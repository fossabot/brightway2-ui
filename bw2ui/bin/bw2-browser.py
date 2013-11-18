#!/usr/bin/env python
# encoding: utf-8
"""Brightway2 database and activity browser.
Developed by Bernhard Steubing and Chris Mutel, 2013

This is a command-line utility to browse, search, and filter databases.

Usage:
  bw2-browser.py
  bw2-browser.py <database>
  bw2-browser.py <database> <activity-id>

Options:
  -h --help     Show this screen.
  --version     Show version.

"""
from __future__ import print_function
from docopt import docopt
from brightway2 import *
from bw2data.colors import Fore, safe_colorama
import cmd
import codecs
import itertools
import math
import os
import threading
import time
import traceback
import webbrowser

GRUMPY = itertools.cycle((
    "This makes no damn sense: ",
    "My mule has more sense than this: ",
    "If 50 million people say a foolish thing, it is still a foolish thing: ",
    "I have had enough of this kind of thing: ",
    "What are you talking about? ",
    "Are you kidding me? What is this: ",
    ))

QUIET = itertools.cycle((
    "You say it best when you say nothing at all...",
    "Let us be silent, that we may hear the whispers of the gods.",
    "Actions speak louder than words. But you didn't use either!",
    "We have ways of making you talk, Mr. Bond!",
    "Brevity is the soul of wit. But you can take it too far!",
    "Do not underestimate the determination of a quiet man.",
    ))

COLORS = {
    'b': Fore.BLUE,  # Used for options user can select
    'c': Fore.CYAN,  # Used for configuration variables or supplement info
    'g': Fore.GREEN,  # Used for main information in line
    'm': Fore.MAGENTA,  # Used for optional parameter
    'r': Fore.RED,  # Used for errors
    'y': Fore.YELLOW,  # Used for prompt,
    'R': Fore.RESET,
}

HELP_TEXT = """
This is a simple way to browse databases and activities in Brightway%(b)s2%(R)s.
The following commands are available:

Basic commands:
    %(b)s?%(R)s: Print this help screen.
    %(b)squit%(R)s, %(b)sq%(R)s: Exit the activity browser.
    %(m)snumber%(R)s: Go to option %(m)snumber%(R)s when a list of options is present.
    %(b)sl%(R)s: List current options.
    %(b)sn%(R)s: Go to next page in paged options.
    %(b)sp%(R)s: Go to previous page in paged options.
    %(b)sp%(R)s %(m)snumber%(R)s: Go to page %(m)snumber%(R)s in paged options.
    %(b)sh%(R)s: List history of databases and activities viewed.
    %(b)swh%(R)s: Write history to a text file.
    %(b)sautosave%(R)s: Toggle autosave behaviour: saves current data.activity.

Working with databases:
    %(b)sldb%(R)s: List available databases.
    %(b)sdb%(R)s %(m)sname%(R)s: Go to database %(m)sname%(R)s. No quotes needed.
    %(b)ss%(R)s %(m)sstring%(R)s: Search activity names in current database with %(m)sstring%(R)s.

Working with activities:
    %(b)sa%(R)s %(m)sid%(R)s: Go to activity %(m)sid%(R)s in current database. Complex ids in quotes.
    %(b)si%(R)s: Info on current activity.
    %(b)sweb%(R)s: Open current activity in web browser. Must have %(c)sbw2-web.py%(R)s running.
    %(b)sr%(R)s: Choose a random activity from current database.
    %(b)su%(R)s: List upstream activities (inputs for the current activity).
    %(b)sd%(R)s: List downstream activities (activities which consume current activity).
    %(b)sb%(R)s: List biosphere flows for the current activity.
    """ % COLORS


def _(d):
    d.update(**COLORS)
    return d


def cprint(line):
    with safe_colorama():
        print(line + Fore.RESET)


def get_autosave_text(autosave):
    return Fore.GREEN + "on" + Fore.RESET if autosave \
        else Fore.RED + "off" + Fore.RESET


class ActivityBrowser(cmd.Cmd):
    """A command line based Activity Browser for brightway2."""
    def _init(self, database=None, activity=None):
        """Provide initial data.

        Can't override __init__, because this is an old style class, i.e. there is no support for ``super``."""
        # Have to print into here; otherwise only print during ``cmdloop``
        if config.p.get('ab_activity', None):
            # Must be tuple, not a list
            config.p['ab_activity'] = tuple(config.p['ab_activity'])
        cprint(HELP_TEXT + "\n" + self.format_defaults())
        self.page_size = 20
        self.set_current_options(None)
        self.autosave = config.p.get('ab_autosave', False)
        self.history = self.reformat_history(config.p.get('ab_history', []))
        self.load_database(database)
        self.load_activity(activity)
        # self.found_activities = []
        # self.filter_activities = []
        # self.filter_mode = False
        self.update_prompt()

    ######################
    # Options management #
    ######################

    def choose_option(self, opt):
        """Go to option ``option``"""
        try:
            index = int(opt)
            if index >= len(self.current_options.get('formatted', [])):
                cprint("%(r)sThere aren't this many options%(R)s" % COLORS)
            elif self.current_options['type'] == 'databases':
                self.choose_database(self.current_options['options'][index])
            elif self.current_options['type'] == 'activities':
                self.choose_activity(self.current_options['options'][index])
            elif self.current_options['type'] == 'history':
                option = self.current_options['options'][index]
                if option[0] == "database":
                    self.choose_database(option[1])
                elif option[0] == "activity":
                    self.choose_activity(option[1])
            else:
                # No current options.
                cprint(Fore.RED + "No current options to choose from" + Fore.RESET)
        except:
            cprint(traceback.format_exc())
            cprint("%(r)sCan't convert %(o)s to number.%(R)s\nCurrent options are:" % _({'o': opt}))
            self.print_current_options()

    def print_current_options(self, label=None):
        print("")
        if label:
            cprint(label + "\n")
        if not self.current_options.get('formatted', []):
            cprint("%(r)sEmpty list%(R)s" % COLORS)
        elif self.max_page:
            # Paging needed
            begin = self.page * self.page_size
            end = (self.page + 1) * self.page_size
            for index, obj in enumerate(self.current_options['formatted'][begin: end]):
                cprint("[%(b)s%(index)i%(R)s]: %(option)s%(R)s" % \
                    _({'option': obj, 'index': index + begin})
                )
            cprint("\nPage %(g)s%(page)i%(R)s of %(g)s%(maxp)s%(R)s. Use %(b)sn%(R)s (next page) and %(b)sp%(R)s (previous page) to navigate." % _({
                'page': self.page,
                'maxp': self.max_page
            }))
        else:
            for index, obj in enumerate(self.current_options['formatted']):
                cprint("[%(b)s%(index)i%(R)s]: %(option)s" % \
                    _({'option': obj, 'index': index})
                )
        print("")

    def set_current_options(self, options):
        self.page = 0
        if options == None:
            options = {'type': None}
            self.max_page = 0
        else:
            self.max_page = int(math.ceil(
                len(options['formatted']) / self.page_size
            ))
        self.current_options = options

    ####################
    # Shell management #
    ####################

    def update_prompt(self):
        """ update prompt and upstream/downstream activity lists """
        if self.activity:
            allowed_length = 76 - 8 - len(self.database)
            name = Database(self.activity[0]).load()[self.activity]['name']
            if allowed_length < len(name):
                name = name[:allowed_length]
            self.prompt = "@(%(db)s) %(n)s >> " % {
                'db': self.database,
                'n': name
            }
        elif self.database:
            self.prompt = "@(%(name)s) >> " % {
                'name': self.database
            }
        else:
            self.prompt = ">> "

    ##############
    # Formatting #
    ##############

    def format_activity(self, key, max_length=10000):
        ds = Database(key[0]).load()[key]
        kurtz = {
            'location': ds.get('location', ''),
            'name': ds['name'],
        }
        if max_length < len(kurtz['name']):
            max_length -= (len(kurtz['location']) + 6)
            kurtz['name'] = kurtz['name'][:max_length] + "..."
        return "%(g)s%(name)s%(R)s (%(m)s%(location)s%(R)s)" % _(kurtz)

    def format_defaults(self):
        text = """The current data directory is %(c)s%(dd)s%(R)s.
Autosave is turned %(autosave)s.""" % _({'dd': config.dir,
            'autosave': get_autosave_text(config.p.get('ab_autosave', False))})
        if config.p.get('ab_database', None):
            text += "\nDefault database: %(c)s%(db)s%(R)s." % _(
                {'db': config.p['ab_database']})
        if config.p.get('ab_activity', None):
            text += "\nDefault activity: %s" % self.format_activity(config.p['ab_activity'])
        return text

    def format_history(self, command):
        kind, obj = command
        if kind == 'database':
            return "%(c)sDb%(R)s: %(g)s%(name)s%(R)s" % _({'name': obj})
        else:
            return "%(c)sAct%(R)s: %(act)s" % _({'act': self.format_activity(obj)})

    def reformat_history(self, json_data):
        """Convert lists to tuples (from JSON serialization)"""
        return [(x[0], tuple(x[1])) if x[0] == 'activity' else tuple(x)
            for x in json_data]

    #######################
    # Database management #
    #######################

    def choose_database(self, database):
        if self.activity and self.activity[0] == database:
            pass
        elif config.p.get('ab_activity', [0, 0])[0] == database:
            self.choose_activity(config.p['ab_activity'])
        else:
            self.unknown_activity()

        self.database = database
        self.history.append(('database', database))
        if self.autosave:
            config.p['ab_database'] = self.database
            config.p['ab_history'] = self.history[-10:]
            config.save_preferences()
        self.set_current_options(None)
        self.update_prompt()

    def load_database(self, database):
        """Load database, trying first """
        if database:
            if database not in databases:
                cprint("%(r)sDatabase %(name)s not found%(R)s" % \
                    _({'name': database}))
                self.load_database(None)
            else:
                self.database = database
        elif config.p.get('ab_database', False):
            self.database = config.p['ab_database']
        else:
            self.database = None
            self.list_databases()

    def list_databases(self):
        dbs = sorted(databases.list)
        self.set_current_options({
            'type': 'databases',
            'options': dbs,
            'formatted': [
                "%(g)s%(name)s%(r)s (%(number)i activities/flows)" % _(
                {
                    'name': name, 'number': databases[name].get('number', 'unknown')
                })
            for name in dbs]
        })
        self.print_current_options("Databases")

    #######################
    # Activity management #
    #######################

    def load_activity(self, activity):
        """Load given or default activity on start"""
        if isinstance(activity, basestring):
            # Input parameter
            self.choose_activity((self.database, activity))
        elif config.p.get('ab_activity', None):
            self.choose_activity(config.p['ab_activity'], restored=True)
        else:
            self.unknown_activity()

    def choose_activity(self, key, restored=False):
        self.database = key[0]
        self.activity = key
        self.history.append(('activity', key))
        if self.autosave and not restored:
            config.p['ab_activity'] = key
            config.p['ab_history'] = self.history[-10:]
            config.save_preferences()
        self.set_current_options(None)
        self.update_prompt()

    def format_exchanges_as_options(self, es, kind, unit_override=None):
        objs = []
        for exc in es:
            if exc['type'] != kind:
                continue
            ds = Database(exc['input'][0]).load()[exc['input']]
            objs.append({
                'name': ds['name'],
                'location': ds.get('location', 'GLO'),
                'unit': unit_override or ds.get('unit', 'unit'),
                'amount': exc['amount'],
                'key': exc['input'],
            })
        objs.sort(key=lambda x: x['name'])

        self.set_current_options({
            'type': 'activities',
            'options': [obj['key'] for obj in objs],
            'formatted': ["%(amount).3g %(m)s%(unit)s %(g)s%(name)s%(R)s (%(m)s%(location)s%(R)s)" \
                % _(obj) for obj in objs]
        })

    def get_downstream_exchanges(self, activity):
        """Get the exchanges that consume this activity's product"""
        db_name = activity[0]
        dbs = [db_name]
        excs = []
        for db in databases:
            if db_name in databases[db]['depends']:
                dbs.append(db)
        for db in dbs:
            for k, v in Database(db).load().iteritems():
                if k == activity:
                    continue
                for exc in v.get('exchanges', []):
                    if activity == exc['input']:
                        excs.append({
                            'type': 7,  # Dummy value
                            'input': k,
                            'amount': exc['amount'],
                            'key': k,
                            'name': v['name'],
                        })
        excs.sort(key=lambda x: x['name'])
        return excs

    def unknown_activity(self):
        self.activity = None

    ########################
    # Default user actions #
    ########################

    def default(self, line):
        """No ``do_foo`` command - try to select from options."""
        if self.current_options['type']:
            try:
                self.choose_option(int(line))
            except:
                cprint(Fore.RED + GRUMPY.next() + Fore.RESET + line)
        else:
            cprint(Fore.RED + GRUMPY.next() + Fore.RESET + line)

    def emptyline(self):
        """No command entered!"""
        cprint(QUIET.next() + "\n(" + Fore.BLUE + "?" + Fore.RESET + " for help)")

    #######################
    # Custom user actions #
    #######################

    def do_a(self, arg):
        """Go to activity id ``arg``"""
        key = (self.database, arg)
        if not self.database:
            cprint("%(r)sNo database selected%(R)s" % COLORS)
        elif key not in Database(self.database).load():
            cprint("%(r)sInvalid activity id%(R)s" % COLORS)
        else:
            self.choose_activity(key)

    def do_autosave(self, arg):
        """Toggle autosave behaviour.

        If autosave is on, the current database or activity is written to config.p each time it changes."""
        self.autosave = not self.autosave
        config.p['ab_autosave'] = self.autosave
        config.save_preferences()
        cprint("Autosave is now %s" % get_autosave_text(self.autosave))

    def do_b(self, arg):
        """List biosphere flows"""
        if not self.activity:
            cprint("%(r)sNeed to choose an activity first%(R)s" % COLORS)
        else:
            es = Database(self.activity[0]).load()[self.activity]['exchanges']
            self.format_exchanges_as_options(es, 'biosphere')
            self.print_current_options("Biosphere flows")

    def do_cp(self, arg):
        """Clear preferences. Only for development."""
        self.autosave = False
        del config.p['ab_autosave']
        del config.p['ab_database']
        del config.p['ab_activity']
        del config.p['ab_history']
        config.save_preferences()
        self.database = self.activity = None
        self.update_prompt()

    def do_d(self, arg):
        """Load downstream activities"""
        if not self.activity:
            cprint("%(r)sNeed to choose an activity first%(R)s" % COLORS)
        else:
            ds = Database(self.activity[0]).load()[self.activity]
            unit = ds['unit']
            excs = self.get_downstream_exchanges(self.activity)
            self.format_exchanges_as_options(excs, 7, unit)
            self.print_current_options("Downstream consumers")

    def do_db(self, arg):
        """Switch to a different database"""
        cprint(arg)
        if arg not in databases:
            cprint("%(r)s'%(db)s' not a valid database%(R)s" % _({'db': arg}))
        else:
            self.choose_database(arg)

    def do_h(self, arg):
        """Pretty print history of databases & activities"""
        self.set_current_options({
            'type': 'history',
            'options': self.history[::-1],
            'formatted': [self.format_history(o) for o in self.history[::-1]]
        })
        self.print_current_options("Browser history")

    def do_help(self, args):
        cprint(HELP_TEXT)

    def do_i(self, arg):
        """Info on current activity.

        TODO: Colors could be improved."""
        if not self.activity:
            cprint("%(r)sNo current activity%(R)s" % COLORS)
        else:
            ds = Database(self.activity[0]).load()[self.activity]
            prod = [x for x in ds['exchanges'] if x['input'] == self.activity]
            if len(prod) == 1:
                amount = prod[0]['amount']
            else:
                amount = 1.
            cprint("""\n%(g)s%(name)s%(R)s

    Database: %(c)s%(database)s%(R)s
    ID: %(c)s%(id)s%(R)s
    Production amount: %(amount).2g %(m)s%(unit)s%(R)s

    Location: %(m)s%(location)s%(R)s
    Technosphere inputs: %(m)s%(tech)s%(R)s
    Biosphere flows: %(m)s%(bio)s%(R)s
    Reference flow used by: %(m)s%(consumers)s%(R)s\n""" % _({
                'name': ds['name'],
                'database': self.activity[0],
                'id': self.activity[1],
                'amount': amount,
                'unit': ds.get('unit', ''),
                'location': ds.get('location', 'GLO'),
                'tech': len([x for x in ds['exchanges']
                    if x['type'] == 'technosphere']),
                'bio': len([x for x in ds['exchanges']
                    if x['type'] == 'biosphere']),
                'consumers': len(self.get_downstream_exchanges(self.activity)),
            }))

    def do_l(self, arg):
        """List current options"""
        if self.current_options['type']:
            self.print_current_options()
        else:
            cprint(Fore.RED + "No current options" + Fore.RESET)

    def do_ldb(self, arg):
        """List available databases"""
        self.list_databases()

    def do_n(self, arg):
        """Go to next page in paged options"""
        if not self.current_options['type']:
            cprint("%(r)sNot in page mode%(R)s" % COLORS)
        elif self.page == self.max_page:
            cprint("%(r)sNo next page%(R)s" % COLORS)
        else:
            self.page += 1
            self.print_current_options()

    def do_p(self, arg):
        """Go to previous page in paged options"""
        if not self.current_options['type']:
            cprint("%(r)sNot in page mode%(R)s" % COLORS)
        elif arg:
            try:
                page = int(arg)
                if page < 0 or page > self.max_page:
                    cprint("%(r)sInvalid page number%(R)s" % COLORS)
                else:
                    self.page = page
                    self.print_current_options()
            except:
                cprint("%(r)sCan't convert page number %(page)s%(R)s" % _({'page': arg}))
        elif self.page == 0:
            cprint("%(r)sAlready page 0%(R)s" % COLORS)
        else:
            self.page -= 1
            self.print_current_options()

    def do_q(self, args):
        """Exit the activity browser."""
        return True

    def do_quit(self, args):
        """Exit the activity browser."""
        return True

    def do_r(self, arg):
        """Choose an activity at random"""
        if not self.database:
            cprint(Fore.RED + "Please choose a database first" + Fore.RESET)
        else:
            key = Database(self.database).random()
            self.choose_activity(key)

    def do_s(self, arg):
        """Search activity names.

        TODO: Ignore case."""
        if not self.database:
            cprint("%(r)sNo current database%(R)s")
        elif not arg:
            cprint("%(r)sMust provide search string%(R)s")
        else:
            results = Database(self.database).query(Filter('name', 'in', arg))
            self.set_current_options({
                'type': 'activities',
                'options': results.keys(),
                'formatted': [self.format_activity(key) for key in results]
                })
            self.print_current_options(
                "Search results for %(c)s%(query)s%(R)s" % _({'query': arg})
            )

    def do_u(self, arg):
        """List upstream processes"""
        if not self.activity:
            cprint("%(r)sNeed to choose an activity first%(R)s" % COLORS)
        else:
            es = Database(self.activity[0]).load()[self.activity]['exchanges']
            self.format_exchanges_as_options(es, 'technosphere')
            self.print_current_options("Upstream inputs")

    def do_web(self, arg):
        """Open a web browser to current activity"""
        if not self.activity:
            cprint("%(r)sNo current activity%(R)s")
        else:
            url = "http://127.0.0.1:5000/view/%(db)s/%(key)s" % {
                'db': self.database,
                'key': self.activity[1]
            }
            threading.Timer(
                0.1,
                lambda: webbrowser.open_new_tab(url)
            ).start()

    def do_wh(self, arg):
        output_dir = config.request_dir("export")
        fp = os.path.join(output_dir, "browser history.%s.txt" % time.ctime())
        with codecs.open(fp, "w", encoding='utf-8') as f:
            for line in self.history:
                f.write(unicode(line) + "\n")
        cprint("History exported to %(c)s%(fp)s%(R)s" % _({'fp': fp}))

# SOME ADDITIONAL FUNCTIONALITY FROM THE FIRST VERSION, WHICH IS CURRENTLY NOT INCLUDED:
# MAINLY FILTER AND UP- AND DOWNSTREAM ACTIVITIES OVER SEVERAL LEVELS
    # def sort_by_name(self, unsorted_list):
    # EASIER:
    # Something like this: unsorted_list.sort(key=lambda x: x['name'])
    #     """ sorts a list of keys by the corresponding names """
    #     names_list = [self.db[key]["name"] for key in unsorted_list]
    #     sorted_list = [key for (name,key) in sorted(zip(names_list,unsorted_list))]
    #     return sorted_list

    # def get_upstream_activities(self, activity):
    #     """ get upstream activities (process inputs) (technosphere) """
    #     if self.filter_mode == False:
    #         upstream_activities_list = [e["input"] for e in self.db[activity]["exchanges"] if e["type"] == "technosphere"]
    #     else:
    #         upstream_activities_list = [e["input"] for e in self.db[activity]["exchanges"] if e["type"] == "technosphere" and e["input"] in self.filter_activities]
    #     return self.sort_by_name(upstream_activities_list)

    # def get_downstream_activities(self, activity):
    #     """ get downstream activities (used-by processes) (technosphere) """
    #     if self.filter_mode == False:
    #         downstream_activities_list = [key for key in self.db if activity in [e["input"] for e in self.db[key]["exchanges"]]]
    #     else:
    #         downstream_activities_list = [key for key in self.db if activity in [e["input"] for e in self.db[key]["exchanges"]] if e["input"] and activity in self.filter_activities]
    #     return self.sort_by_name(downstream_activities_list)

    # def traverse_upstream(self, new_current_activity, max_depth):
    #     """ recursive graph traversal showing the next level activities for each traversed activity """
    #     print "ACTIVITY (DEPTH " + str(self.level) + "/" + str(max_depth) + "): " + self.db[new_current_activity]["name"] + ", " + self.db[new_current_activity]["location"]
    #     self.display_list(self.get_upstream_activities(new_current_activity), "UPSTREAM ACTIVITIES (DEPTH " + str(self.level) + "/" + str(max_depth) + ")")
    #     for upstream_activity in self.get_upstream_activities(new_current_activity):
    #         self.level += 1
    #         if self.level <= max_depth:
    #             self.traverse_upstream(upstream_activity, max_depth)
    #         self.level -= 1

    # def traverse_downstream(self, new_current_activity, max_depth):
    #     """ recursive graph traversal showing the next level activities for each traversed activity """
    #     print "ACTIVITY (DEPTH " + str(self.level) + "/" + str(max_depth) + "): " + self.db[new_current_activity]["name"] + ", " + self.db[new_current_activity]["location"]
    #     self.display_list(self.get_downstream_activities(new_current_activity), "DOWNTSTREAM ACTIVITIES (DEPTH " + str(self.level) + "/" + str(max_depth) + ")")
    #     for upstream_activity in self.get_downstream_activities(new_current_activity):
    #         self.level += 1
    #         if self.level <= max_depth:
    #             self.traverse_downstream(upstream_activity, max_depth)
    #         self.level -= 1

    # def do_filter(self, args):
    #     """ switch filter mode on / off """
    #     if args == "":
    #         if self.filter_mode == True:
    #             print "\nfilter mode is ON\n"
    #         else:
    #             print "\nfilter mode is OFF\n"
    #     elif args == "on":
    #         self.filter_mode = True
    #         print "\n filter mode ON\n"
    #     elif args == "off":
    #         self.filter_mode = False
    #         print "\n filter mode OFF\n"
    #     else:
    #         print "please specify 'on' / 'off' to switch on/off filter mode"
    #     self.update()

    # def do_load_filter_from_file(self, args):
    #     """ load a file with names and locations for filter activities and convert it to a list of keys """
    #     if args == "":
    #         args = raw_input("\nPlease enter a filename: ")
    #     try:
    #         with open(args) as f:
    #             lines = f.read().splitlines()
    #         list_names_locations = [l.split(";") for l in lines]
    #         try: # now make a list of keys from this list of names and locations
    #             count = 0
    #             self.filter_activities = []
    #             for nl in list_names_locations:
    #                 for key in self.db:
    #                     if nl[0] in self.db[key]["name"] and nl[1] in self.db[key]["location"]:
    #                         self.filter_activities.append(key)
    #                         count += 1
    #             self.sort_by_name(self.filter_activities)
    #         except UnicodeDecodeError:
    #             print "\nUnicodeDecodeError: there is a problem with special characters in line: " + str(count)
    #         print "\nloaded " + args + " as FILTER\n"
    #     except:
    #         print "file could not be loaded\n"


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Brightway2 Activity Browser 1.0')
    activitybrowser = ActivityBrowser()
    activitybrowser._init(
        database=arguments['<database>'],
        activity=arguments['<activity-id>']
    )
    activitybrowser.cmdloop()
