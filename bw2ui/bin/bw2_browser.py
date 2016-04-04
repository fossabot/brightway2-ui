#!/usr/bin/env python
# encoding: utf-8
"""Brightway2 database and activity browser.
Developed by Bernhard Steubing and Chris Mutel, 2013

This is a command-line utility to browse, search, and filter databases.

Usage:
  bw2-browser
  bw2-browser <project>
  bw2-browser <project> <database>
  bw2-browser <project> <database> <activity-id>

Options:
  -h --help     Show this screen.
  --version     Show version.

"""
from __future__ import print_function
from future.utils import iteritems
from past.builtins import basestring
from docopt import docopt
from brightway2 import *
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


HELP_TEXT = """
This is a simple way to browse databases and activities in Brightway2.
The following commands are available:

Basic commands:
    ?: Print this help screen.
    quit, q: Exit the activity browser.
    number: Go to option number when a list of options is present.
    l: List current options.
    n: Go to next page in paged options.
    p: Go to previous page in paged options.
    p number: Go to page number in paged options.
    h: List history of databases and activities viewed.
    wh: Write history to a text file.
    autosave: Toggle autosave behaviour on and off.

Working with databases:
    lpj: List available projects.
    ldb: List available databases.
    db name: Go to database name. No quotes needed.
    s string: Search activity names in current database with string.

Working with activities:
    a id: Go to activity id in current database. Complex ids in quotes.
    i: Info on current activity.
    web: Open current activity in web browser. Must have bw2-web running.
    r: Choose a random activity from current database.
    u: List upstream activities (inputs for the current activity).
    d: List downstream activities (activities which consume current activity).
    b: List biosphere flows for the current activity.
    """


def get_autosave_text(autosave):
    return "on" if autosave else "off"


class ActivityBrowser(cmd.Cmd):
    """A command line based Activity Browser for brightway2."""
    def _init(self, project=None, database=None, activity=None):
        """Provide initial data.

        Can't override __init__, because this is an old style class, i.e. there is no support for ``super``."""
        # Have to print into here; otherwise only print during ``cmdloop``
        if config.p.get('ab_activity', None):
            # Must be tuple, not a list
            config.p['ab_activity'] = tuple(config.p['ab_activity'])
        print(HELP_TEXT + "\n" + self.format_defaults())
        self.page_size = 20
        self.set_current_options(None)
        self.autosave = config.p.get('ab_autosave', False)
        self.history = self.reformat_history(config.p.get('ab_history', []))
        self.load_project(project)
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
        """Go to option ``opt``"""
        try:
            index = int(opt)
            if index >= len(self.current_options.get('formatted', [])):
                print("There aren't this many options")
            elif self.current_options['type'] == 'projects':
                self.choose_project(self.current_options['options'][index])
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
                print("No current options to choose from")
        except:
            print(traceback.format_exc())
            print("Can't convert %(o)s to number.\nCurrent options are:" % {'o': opt})
            self.print_current_options()

    def print_current_options(self, label=None):
        print("")
        if label:
            print(label + "\n")
        if not self.current_options.get('formatted', []):
            print("Empty list")
        elif self.max_page:
            # Paging needed
            begin = self.page * self.page_size
            end = (self.page + 1) * self.page_size
            for index, obj in enumerate(self.current_options['formatted'][begin: end]):
                print("[%(index)i]: %(option)s" % \
                    {'option': obj, 'index': index + begin}
                )
            print("\nPage %(page)i of %(maxp)s. Use n (next page) and p (previous page) to navigate." % {
                'page': self.page,
                'maxp': self.max_page
            })
        else:
            for index, obj in enumerate(self.current_options['formatted']):
                print("[%(index)i]: %(option)s" % \
                    {'option': obj, 'index': index}
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
            name = Database(self.activity[0]).get(self.activity[1]).get('name', "Unknown")
            if allowed_length < len(name):
                name = name[:allowed_length]
            self.prompt = "%(pj)s@(%(db)s) %(n)s >> " % {
                'pj': self.project,
                'db': self.database,
                'n': name
            }
        elif self.database:
            self.prompt = "%(pj)s@(%(name)s) >> " % {
                'pj': self.project,
                'name': self.database
            }
        elif self.project:
            self.prompt = "%(pj)s >> " % {
                'pj': self.project
            }
        else:
            self.prompt = ">> "

    ##############
    # Formatting #
    ##############

    def format_activity(self, key, max_length=10000):
        ds = Database(key[0]).get(key[1])
        kurtz = {
            'location': ds.get('location', ''),
            'name': ds.get('name', "Unknown"),
        }
        if max_length < len(kurtz['name']):
            max_length -= (len(kurtz['location']) + 6)
            kurtz['name'] = kurtz['name'][:max_length] + "..."
        # TODO: Can adjust string lengths with product name, but just ignore for now
        product = ds.get(u'reference product', '')
        categories = ds.get(u'categories', '')
        if product:
            product += u', ' % {}
        kurtz['product'] = product
        kurtz['categories'] = categories 
        return "%(name)s (%(product)s%(location)s) %(categories)s" % kurtz

    def format_defaults(self):
        text = """The current data directory is %(dd)s.
Autosave is turned %(autosave)s.""" % {'dd': config.dir,
            'autosave': get_autosave_text(config.p.get('ab_autosave', False))}
        if config.p.get('ab_database', None):
            text += "\nDefault database: %(db)s." % \
                {'db': config.p['ab_database']}
        if config.p.get('ab_activity', None):
            text += "\nDefault activity: %s" % self.format_activity(config.p['ab_activity'])
        return text

    def format_history(self, command):
        kind, obj = command
        if kind == 'database':
            return "Db: %(name)s" % {'name': obj}
        else:
            return "Act: %(act)s" % {'act': self.format_activity(obj)}

    def reformat_history(self, json_data):
        """Convert lists to tuples (from JSON serialization)"""
        return [(x[0], tuple(x[1])) if x[0] == 'activity' else tuple(x)
            for x in json_data]

    #######################
    # Project  management #
    #######################

    def choose_project(self, project):
        if self.project and self.project == project:
            pass
        #elif self.project and self.project == project:
        else:
            self.unknown_project()
        projects.current = project
        self.project = project
        self.history.append(('project', project))
        if self.autosave:
            config.p['ab_project'] = self.project
            config.p['ab_history'] = self.history[-10:]
            config.save_preferences()
        self.set_current_options(None)
        self.activity=None
        self.database=None
        self.list_databases()
        self.update_prompt()

    def load_project(self, project):
        if project:
            if project not in projects:
                print("Project %(name)s not found" % \
                        {'name': project})
                load_project(None)
            else:
                self.project = project
                projects.current = project
        elif config.p.get('ab_project', False):
            self.project = config.p['ab_project']
        else:
            self.project= None
            self.list_projects()

    def list_projects(self):
        pjs = [p.name for p in projects]
        self.set_current_options({
            'type':'projects',
            'options':pjs,
            'formatted': [
                "%(name)s" % {
                    'name': name
                #, 'number': databases[name].get('number', 'unknown')
                }
            for name in pjs]
        })
        self.print_current_options("Projects")

    def unknown_project(self):
        self.project = None

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
                print("Database %(name)s not found" % \
                    {'name': database})
                self.load_database(None)
            else:
                self.database = database
        elif config.p.get('ab_database', False):
            self.database = config.p['ab_database']
        else:
            self.database = None
            #self.list_databases()

    def list_databases(self):
        dbs = sorted(databases.list)
        self.set_current_options({
            'type': 'databases',
            'options': dbs,
            'formatted': [
                "%(name)s (%(number)s activities/flows)" %
                {
                    'name': name, 'number': databases[name].get('number', 'unknown')
                }
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
            ds = Database(exc['input'][0]).get(exc['input'][1])
            objs.append({
                'name': ds.get('name', "Unknown"),
                'location': ds.get('location', config.global_location),
                'unit': unit_override or ds.get('unit', 'unit'),
                'amount': exc['amount'],
                'key': exc['input'],
            })
        objs.sort(key=lambda x: x['name'])

        self.set_current_options({
            'type': 'activities',
            'options': [obj['key'] for obj in objs],
            'formatted': ["%(amount).3g %(unit)s %(name)s (%(location)s)" \
                % obj for obj in objs]
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
            for k, v in iteritems(Database(db).load()):
                if k == activity:
                    continue
                for exc in v.get('exchanges', []):
                    if activity == exc['input']:
                        excs.append({
                            'type': 7,  # Dummy value
                            'input': k,
                            'amount': exc['amount'],
                            'key': k,
                            'name': v.get('name', "Unknown"),
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
                print(GRUMPY.next() + line)
        else:
            print(GRUMPY.next() + line)

    def emptyline(self):
        """No command entered!"""
        print(QUIET.next() + "\n(? for help)")

    #######################
    # Custom user actions #
    #######################

    def do_a(self, arg):
        """Go to activity id ``arg``"""
        key = (self.database, arg)
        if not self.database:
            print("No database selected")
        elif key not in Database(self.database).load():
            print("Invalid activity id")
        else:
            self.choose_activity(key)

    def do_autosave(self, arg):
        """Toggle autosave behaviour.

        If autosave is on, the current database or activity is written to config.p each time it changes."""
        self.autosave = not self.autosave
        config.p['ab_autosave'] = self.autosave
        config.save_preferences()
        print("Autosave is now %s" % get_autosave_text(self.autosave))

    def do_b(self, arg):
        """List biosphere flows"""
        if not self.activity:
            print("Need to choose an activity first")
        else:
            es = Database(self.activity[0]).get(self.activity[1]).exchanges()
            self.format_exchanges_as_options(es, 'biosphere')
            self.print_current_options("Biosphere flows")

    def do_cp(self, arg):
        """Clear preferences. Only for development."""
        self.autosave = False
        del config.p['ab_autosave']
        del config.p['ab_project']
        del config.p['ab_database']
        del config.p['ab_activity']
        del config.p['ab_history']
        config.save_preferences()
        self.database = self.activity = None
        self.update_prompt()

    def do_d(self, arg):
        """Load downstream activities"""
        if not self.activity:
            print("Need to choose an activity first")
        else:
            ds = Database(self.activity[0]).get(self.activity[1])
            unit = ds.get('unit', '')
            excs = self.get_downstream_exchanges(self.activity)
            self.format_exchanges_as_options(excs, 7, unit)
            self.print_current_options("Downstream consumers")

    def do_db(self, arg):
        """Switch to a different database"""
        print(arg)
        if arg not in databases:
            print("'%(db)s' not a valid database" % {'db': arg})
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
        print(HELP_TEXT)

    def do_i(self, arg):
        """Info on current activity.

        TODO: Colors could be improved."""
        if not self.activity:
            print("No current activity")
        else:
            ds = Database(self.activity[0]).get(self.activity[1])
            prod = [x for x in ds.exchanges() if x['input'] == self.activity]
            if u'production amount' in ds and ds[u'production amount']:
                amount = ds[u'production amount']
            elif len(prod) == 1:
                amount = prod[0]['amount']
            else:
                amount = 1.
            print("""\n%(name)s

    Database: %(database)s
    ID: %(id)s
    Product: %(product)s
    Production amount: %(amount).2g %(unit)s

    Location: %(location)s
    Categories: %(categories)s
    Technosphere inputs: %(tech)s
    Biosphere flows: %(bio)s
    Reference flow used by: %(consumers)s\n""" % {
                'name': ds.get('name', "Unknown"),
                'product': ds.get(u'reference product') or ds.get('name', "Unknown"),
                'database': self.activity[0],
                'id': self.activity[1],
                'amount': amount,
                'unit': ds.get('unit', ''),
                'categories': ', '.join(ds.get('categories', [])),
                'location': ds.get('location', config.global_location),
                'tech': len([x for x in ds.exchanges()
                    if x['type'] == 'technosphere']),
                'bio': len([x for x in ds.exchanges()
                    if x['type'] == 'biosphere']),
                'consumers': len(self.get_downstream_exchanges(self.activity)),
            })

    def do_l(self, arg):
        """List current options"""
        if self.current_options['type']:
            self.print_current_options()
        else:
            print("No current options")

    def do_lpj(self, arg):
        """List available projects"""
        self.list_projects()

    def do_ldb(self, arg):
        """List available databases"""
        self.list_databases()

    def do_n(self, arg):
        """Go to next page in paged options"""
        if not self.current_options['type']:
            print("Not in page mode")
        elif self.page == self.max_page:
            print("No next page")
        else:
            self.page += 1
            self.print_current_options()

    def do_p(self, arg):
        """Go to previous page in paged options"""
        if not self.current_options['type']:
            print("Not in page mode")
        elif arg:
            try:
                page = int(arg)
                if page < 0 or page > self.max_page:
                    print("Invalid page number")
                else:
                    self.page = page
                    self.print_current_options()
            except:
                print("Can't convert page number %(page)s" % {'page': arg})
        elif self.page == 0:
            print("Already page 0")
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
            print("Please choose a database first")
        else:
            key = Database(self.database).random()
            self.choose_activity(key)

    def do_s(self, arg):
        """Search activity names."""
        if not self.database:
            print("No current database" % {})
        elif not arg:
            print("Must provide search string" % {})
        else:
            #results = Database(self.database).query(Filter('name', 'ihas', arg))
            results = Database(self.database).search(arg)
            results_keys = [r.key for r in results] 
            self.set_current_options({
                'type': 'activities',
                'options': results_keys,
                'formatted': [self.format_activity(key) for key in results]
                })
            self.print_current_options(
                "Search results for %(query)s" % {'query': arg}
            )

    def do_u(self, arg):
        """List upstream processes"""
        if not self.activity:
            print("Need to choose an activity first")
        else:
            #es = Database(self.activity[0]).load()[self.activity].get("exchanges", [])
            es = Database(self.activity[0]).get(self.activity[1]).exchanges()
            self.format_exchanges_as_options(es, 'technosphere')
            self.print_current_options("Upstream inputs")

    def do_web(self, arg):
        """Open a web browser to current activity"""
        if not self.activity:
            print("No current activity" % {})
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
        output_dir = projects.request_directory("export")
        fp = os.path.join(output_dir, "browser history.%s.txt" % time.ctime())
        with codecs.open(fp, "w", encoding='utf-8') as f:
            for line in self.history:
                f.write(unicode(line) + "\n")
        print("History exported to %(fp)s" % {'fp': fp})


def main():
    arguments = docopt(__doc__, version='Brightway2 Activity Browser 1.0')
    activitybrowser = ActivityBrowser()
    activitybrowser._init(
        project=arguments['<project>'],
        database=arguments['<database>'],
        activity=arguments['<activity-id>']
    )
    activitybrowser.cmdloop()


if __name__ == '__main__':
    main()
