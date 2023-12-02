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
from __future__ import print_function, unicode_literals

import cmd
import codecs
import itertools
import math
import os
import pprint
import re
import textwrap
import threading
import time
import traceback
import uuid
import warnings
import webbrowser
from bw2calc import MultiLCA
from bw2data import (
    Database,
    Method,
    calculation_setups,
    config,
    databases,
    get_activity,
    methods,
    projects,
)
from bw2data.parameters import (
    ActivityParameter,
    DatabaseParameter,
    Group,
    ProjectParameter,
)
from docopt import docopt
from tabulate import tabulate

warnings.filterwarnings("ignore", ".*Read only project.*")

GRUMPY = itertools.cycle(
    (
        "This makes no damn sense: ",
        "My mule has more sense than this: ",
        "If 50 million people say a foolish thing, it is still a foolish thing: ",
        "I have had enough of this kind of thing: ",
        "What are you talking about? ",
        "Are you kidding me? What is this: ",
    )
)

QUIET = itertools.cycle(
    (
        "You say it best when you say nothing at all...",
        "Let us be silent, that we may hear the whispers of the gods.",
        "Actions speak louder than words. But you didn't use either!",
        "We have ways of making you talk, Mr. Bond!",
        "Brevity is the soul of wit. But you can take it too far!",
        "Do not underestimate the determination of a quiet man.",
    )
)


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

Working with projects:
    lpj: List available projects.

Working with databases:
    ldb: List available databases.
    db name: Go to database name. No quotes needed.
    s string: Search activity names in current database with string.
    s -loc {LOCATION} string: Search activity names in current database with \
string and location LOCATION.
    s -cat {CAT::SUBCAT::SUBSUBCAT} string: Search activity names in current database \
with string and category cat, subcat, subcat [useful for biosphere].

Working with activities:
    a id: Go to activity id in current database. Complex ids in quotes.
    aa: List all activities in current database. aa name sorts the activities \
by name.
    i: Info on current activity.
    ii: Extended Info on current activity.
    web: Open current activity in web browser. Must have bw2-web running.
    r: Choose a random activity from current database.
    u: List upstream activities (inputs for the current activity).
    up: List upstream activities with pedigree info if avail (inputs for the current \
activity).
    uu: List upstream activities with formula info if avail.
    d: List downstream activities (activities which consume current activity).
    b: List biosphere flows for the current activity.
    cfs: Show characterization factors for current activity and current method.
    G: if a method and activity are selected, do an lcia of the activity.
    ta: if an lcia of the activity has been done, list top activities.
    te: if an lcia of the activity has been done, list top emissions.

Working with methods:
    lm: List methods.
    mi: Show method metadata. (must select method/category/subcategory first)

Working with parameters:
    lpam: List all parameters (Project, Database and Activity) showing only \
basic columns (data).
    lpam [-f]: List all parameters showing all columns (data) of each parameter.
    lpam [-f] -g {YY}: List parameters for a specific group. Use db or specific \
data. add as first option -f to show all columns.
    lpamg: show parameter groups
    ap [-f]: If an activity is selected, show activity parameters
    dp [-f]: if a database is selected show database parameters
    pp [-f]: If a project is selected show project parameters
    fp : Find parameters (Project, Database or Activity) by name
    sp : search a parameter (accepts wildcards)
Misc:
    tsv: [filename] export latest table to tsv file (e.g.: results or cfs)
    """


def get_autosave_text(autosave):
    return "on" if autosave else "off"


class ActivityBrowser(cmd.Cmd):
    """A command line based Activity Browser for brightway2."""

    def _init(self, project=None, database=None, activity=None, method=None):
        """Provide initial data.

        Can't override __init__, because this is an old style class
        i.e. there is no support for ``super``."""
        # Have to print into here; otherwise only print during ``cmdloop``
        if config.p.get("ab_activity", None):
            # Must be tuple, not a list
            config.p["ab_activity"] = tuple(config.p["ab_activity"])
        print(HELP_TEXT + "\n" + self.format_defaults())
        self.page_size = 20
        self.search_limit = config.p.get("search_limit", 100)
        self.set_current_options(None)
        self.autosave = config.p.get("ab_autosave", False)
        self.history = self.reformat_history(config.p.get("ab_history", []))
        self.load_project(project)
        self.load_database(database)
        self.load_activity(activity)
        self.load_method(method)
        self.update_prompt()

    ######################
    # Options management #
    ######################

    def choose_option(self, opt):
        """Go to option ``opt``"""
        try:
            index = int(opt)
            if index >= len(self.current_options.get("formatted", [])):
                print("There aren't this many options")
            elif self.current_options["type"] == "methods":
                self.choose_method(self.current_options["options"][index])

            elif self.current_options["type"] == "categories":
                self.choose_category(self.current_options["options"][index])

            elif self.current_options["type"] == "subcategories":
                self.choose_subcategory(self.current_options["options"][index])

            elif self.current_options["type"] == "projects":
                self.choose_project(self.current_options["options"][index])

            elif self.current_options["type"] == "databases":
                self.choose_database(self.current_options["options"][index])
            elif self.current_options["type"] == "activities":
                self.choose_activity(self.current_options["options"][index])
            elif self.current_options["type"] == "groups":
                self.choose_group(self.current_options["options"][index])
            elif self.current_options["type"] == "history":
                option = self.current_options["options"][index]
                if option[0] == "database":
                    self.choose_database(option[1])
                elif option[0] == "activity":
                    self.choose_activity(option[1])
            else:
                # No current options.
                print("No current options to choose from")
        except Exception:
            print(traceback.format_exc())
            print("Can't convert %(o)s to number.\nCurrent options are:" % {"o": opt})
            self.print_current_options()

    def print_current_options(self, label=None):
        print("")
        if label:
            print(label + "\n")
        if not self.current_options.get("formatted", []):
            print("Empty list")
        elif self.max_page:
            # Paging needed
            begin = self.page * self.page_size
            end = (self.page + 1) * self.page_size
            for index, obj in enumerate(self.current_options["formatted"][begin:end]):
                print(
                    "[%(index)i]: %(option)s" % {"option": obj, "index": index + begin}
                )
            print(
                "\nPage %(page)i of %(maxp)s. Use n (next page) and p \
(previous page) to navigate."
                % {"page": self.page, "maxp": self.max_page}
            )
        else:
            for index, obj in enumerate(self.current_options["formatted"]):
                print("[%(index)i]: %(option)s" % {"option": obj, "index": index})
        print("")

    def set_current_options(self, options):
        self.page = 0
        if options is None:
            options = {"type": None}
            self.max_page = 0
        else:
            self.max_page = int(math.ceil(len(options["formatted"]) / self.page_size))
        self.current_options = options

    ####################
    # Shell management #
    ####################

    def update_prompt(self):
        """update prompt and upstream/downstream activity lists"""
        self.invite = ">> "
        self.prompt = ""
        if self.activity:
            allowed_length = 76 - 8 - len(self.database)
            activity_ = get_activity(self.activity)
            name = activity_.get("name", "Unknown")
            categories = activity_.get("categories", [])
            if allowed_length < len(name):
                name = name[:allowed_length]
            self.prompt = "%(pj)s@(%(db)s) %(n)s %(categories)s" % {
                "pj": self.project,
                "db": self.database,
                "n": name,
                "categories": categories,
            }
        elif self.database:
            self.prompt = "%(pj)s@(%(name)s) " % {
                "pj": self.project,
                "name": self.database,
            }
        elif self.project:
            self.prompt = "%(pj)s " % {"pj": self.project}
        if self.method:
            if self.category:
                if self.subcategory:
                    self.prompt += "[%(method)s/%(category)s/%(subcategory)s] " % {
                        "method": self.method,
                        "category": self.category,
                        "subcategory": self.subcategory,
                    }
                else:
                    self.prompt += "[%(method)s/%(category)s] " % {
                        "method": self.method,
                        "category": self.category,
                    }
            else:
                self.prompt += "[%(method)s/] " % {"method": self.method}
        self.prompt += self.invite

    ##############
    # Formatting #
    ##############

    def format_activity(self, key, max_length=10000):
        ds = get_activity(key)
        kurtz = {"location": ds.get("location", ""), "name": ds.get("name", "Unknown")}
        if max_length < len(kurtz["name"]):
            max_length -= len(kurtz["location"]) + 6
            kurtz["name"] = kurtz["name"][:max_length] + "..."
        # TODO: Can adjust string lengths with product name, but just ignore for now
        product = ds.get("reference product", "")
        categories = ds.get("categories", "")
        if product:
            product += ", " % {}
        kurtz["product"] = product
        kurtz["categories"] = categories
        return "%(name)s (%(product)s%(location)s%(categories)s)" % kurtz

    def format_defaults(self):
        text = """The current data directory is %(dd)s.
Autosave is turned %(autosave)s.""" % {
            "dd": projects.dir,
            "autosave": get_autosave_text(config.p.get("ab_autosave", False)),
        }
        if config.p.get("ab_database", None):
            text += "\nDefault database: %(db)s." % {"db": config.p["ab_database"]}
        if config.p.get("ab_activity", None):
            text += "\nDefault activity: %s" % self.format_activity(
                config.p["ab_activity"]
            )
        return text

    def format_history(self, command):
        kind, obj = command
        if kind == "database":
            return "Db: %(name)s" % {"name": obj}
        else:
            return "Act: %(act)s" % {"act": self.format_activity(obj)}

    def reformat_history(self, json_data):
        """Convert lists to tuples (from JSON serialization)"""
        return [
            (x[0], tuple(x[1])) if x[0] == "activity" else tuple(x) for x in json_data
        ]

    def print_cfs(self, current_methods, activity=None):
        """Print cfs for a list of methods, and optionally only for an activity"""
        table_lines = []
        for m in current_methods:
            method_ = Method(m)
            cfs = method_.load()
            if activity:
                cfs = [cf for cf in cfs if get_activity(cf[0]).key == activity]
            for cf in cfs:
                # in bw2, the first elment of the cf data is a key -> tuple('db', 'id')
                # in bw25, the first element is single int id of the activity
                # this looks hackish, but it allows to keep 1 code-base for both
                # versions of bw (bw2 & bw25)
                if isinstance(cf[0], int):
                    flow = get_activity(cf[0])
                else:
                    flow_key = tuple((cf[0][0], cf[0][1]))
                    flow = get_activity(flow_key)
                flow_cat_tup = flow["categories"]
                flow_cat = flow_cat_tup[0]
                flow_subcat = None
                if len(flow_cat_tup) == 2:
                    flow_subcat = flow_cat_tup[1]
                line = [
                    m[1],
                    m[2],
                    cf[1],
                    flow["name"],
                    flow_cat,
                    flow_subcat,
                    method_.metadata["unit"],
                ]
                table_lines.append(line)
        if table_lines:
            headers = [
                "method",
                "category",
                "cf",
                "flow",
                "flow_category",
                "flow_subcategory",
                "unit",
            ]
            print("CFS")
            self.tabulate_data = tabulate(table_lines, headers=headers, tablefmt="tsv")
            print(tabulate(table_lines, headers=headers))
        else:
            print("Not characterized by method")

    #######################
    # Project  management #
    #######################

    def choose_project(self, project):
        if self.project == project:
            return
        self.project = project
        projects.set_current(self.project, writable=False)
        self.history.append(("project", project))
        if self.autosave:
            config.p["ab_project"] = self.project
            config.p["ab_history"] = self.history[-10:]
            config.save_preferences()
        self.set_current_options(None)
        self.activity = None
        self.database = None
        self.list_databases()
        self.update_prompt()

    def load_project(self, project):
        if project:
            if project not in projects:
                print("Project %(name)s not found" % {"name": project})
                self.load_project(None)
            else:
                self.project = project
                projects.set_current(self.project, writable=False)
        elif config.p.get("ab_project", False):
            self.project = config.p["ab_project"]
        else:
            self.project = None
            self.list_projects()

    def list_projects(self):
        pjs = [p.name for p in projects]
        self.set_current_options(
            {
                "type": "projects",
                "options": pjs,
                "formatted": ["%(name)s" % {"name": name} for name in pjs],
            }
        )
        self.print_current_options("Projects")

    #######################
    # Database management #
    #######################

    def choose_database(self, database):
        if self.activity and self.activity[0] == database:
            pass
        elif config.p.get("ab_activity", [0, 0])[0] == database:
            self.choose_activity(config.p["ab_activity"])
        else:
            self.unknown_activity()

        self.database = database
        self.history.append(("database", database))
        if self.autosave:
            config.p["ab_database"] = self.database
            config.p["ab_history"] = self.history[-10:]
            config.save_preferences()
        self.set_current_options(None)
        self.update_prompt()

    def load_database(self, database):
        """Load database, trying first"""
        if database:
            if database not in databases:
                print("Database %(name)s not found" % {"name": database})
                self.load_database(None)
            else:
                self.database = database
        elif config.p.get("ab_database", False):
            self.database = config.p["ab_database"]
        else:
            self.database = None

    def list_databases(self):
        dbs = sorted(databases.list)
        self.set_current_options(
            {
                "type": "databases",
                "options": dbs,
                "formatted": [
                    "%(name)s (%(number)s activities/flows)"
                    % {"name": name, "number": databases[name].get("number", "unknown")}
                    for name in dbs
                ],
            }
        )
        self.print_current_options("Databases")

    #######################
    # Activity management #
    #######################

    def load_activity(self, activity):
        """Load given or default activity on start"""
        if isinstance(activity, str):
            # Input parameter
            self.choose_activity((self.database, activity))
        elif config.p.get("ab_activity", None):
            self.choose_activity(config.p["ab_activity"], restored=True)
        else:
            self.unknown_activity()

    def choose_activity(self, key, restored=False):
        self.database = key[0]
        self.activity = key
        self.history.append(("activity", key))
        if self.autosave and not restored:
            config.p["ab_activity"] = key
            config.p["ab_history"] = self.history[-10:]
            config.save_preferences()
        self.set_current_options(None)
        self.update_prompt()

    def format_exchanges_as_options(
        self, es, kind, unit_override=None, show_formulas=False, show_pedigree=False
    ):
        objs = []
        for exc in es:
            if exc["type"] != kind:
                continue
            ds = get_activity(exc["input"])
            objs.append(
                {
                    "name": ds.get("name", "Unknown"),
                    "location": ds.get("location", config.global_location),
                    "unit": unit_override or ds.get("unit", "unit"),
                    "amount": exc["amount"],
                    "formula": exc.get("formula", None),
                    "pedigree": exc.get("pedigree", None),
                    "key": exc["input"],
                }
            )
        objs.sort(key=lambda x: x["name"])
        if show_formulas:
            format_string = "%(amount).3g [=%(formula)s] %(unit)s %(name)s (%(location)s)"  # NOQA: E501
        elif show_pedigree:
            format_string = "%(amount).3g %(unit)s %(name)s (%(location)s)\n\t[pedigree: %(pedigree)s] "  # NOQA: E501
        else:
            format_string = "%(amount).3g %(unit)s %(name)s (%(location)s)"

        self.set_current_options(
            {
                "type": "activities",
                "options": [obj["key"] for obj in objs],
                "formatted": [format_string % obj for obj in objs],
            }
        )

    def get_downstream_exchanges(self, activity):
        """Get the exchanges that consume this activity's product"""
        activity = get_activity(activity)
        excs = []
        exchanges = activity.upstream()
        for exc in exchanges:
            if activity == exc["input"] and not activity == exc["output"]:
                excs.append(
                    {
                        "type": exc.get("type", "Unknown"),
                        "input": exc["output"],
                        "amount": exc["amount"],
                        "key": exc["output"][1],
                        "name": exc.get("name", "Unknown"),
                    }
                )
        excs.sort(key=lambda x: x["name"])
        return excs

    def unknown_activity(self):
        self.activity = None

    ########################
    # Method management    #
    ########################

    def load_method(self, method):
        if method:
            if method not in methods:
                print("Method %(name)s not found" % {"name": method})
                self.load_method(None)
            else:
                self.method = method[0]
                self.category = method[1]
        elif config.p.get("ab_method", False):
            self.method = config.p["ab_method"]
        else:
            self.method = None
            self.category = None
            self.subcategory = None

    def list_methods(self):
        if self.project:
            m_names = set([])
            methods_ = sorted(methods)
            for m in methods_:
                m_names.add(m[0])
            m_names = sorted(m_names)
            self.set_current_options(
                {
                    "type": "methods",
                    "options": list(m_names),
                    "formatted": ["%(name)s" % {"name": name} for name in m_names],
                }
            )
            self.print_current_options("Methods")
        else:
            self.set_current_options(None)
            self.update_prompt()

    def choose_method(self, method):
        self.method = method
        self.category = self.subcategory = None
        self.history.append(("method", method))
        if self.autosave:
            config.p["ab_method"] = self.method
            config.p["ab_history"] = self.history[-10:]
            config.save_preferences()
        c_names = set([])
        methods_ = sorted(methods)
        for m in [m for m in methods_ if m[0] == method]:
            c_names.add(m[1])
        c_names = sorted(c_names)
        self.set_current_options(
            {
                "type": "categories",
                "options": list(c_names),
                "formatted": ["%(name)s" % {"name": name} for name in c_names],
            }
        )
        self.print_current_options("Categories")
        self.update_prompt()

    def choose_category(self, category):
        self.category = category
        self.history.append(("category", category))
        if self.autosave:
            config.p["ab_category"] = self.category
            config.p["ab_history"] = self.history[-10:]
            config.save_preferences()
        c_names = set([])
        methods_ = sorted(methods)
        for m in [m for m in methods_ if m[0] == self.method and m[1] == category]:
            c_names.add(m[2])
        self.set_current_options(
            {
                "type": "subcategories",
                "options": list(c_names),
                "formatted": ["%(name)s" % {"name": name} for name in c_names],
            }
        )
        self.print_current_options("Subcategories")
        self.update_prompt()

    def choose_subcategory(self, subcategory):
        self.subcategory = subcategory
        self.history.append(("subcategory", subcategory))
        # using ecoinvent_interface creates biosphere dbs that are not only called
        # "biosphere3" so we test now only against a substring, not the exact name
        if (
            self.activity and "biosphere" in self.database
        ):  # TODO: recover generic name instead of hard coded one
            mkey = (self.method, self.category, self.subcategory)
            self.print_cfs([mkey], self.activity)
        self.update_prompt()

    #################################
    # GROUP / Parameters Management #
    #################################

    def dehydrate_params(self, params, fields):
        """Remove keys of each param dictionnary, and only keep fields."""
        return [{k: v for k, v in p.dict.items() if k in fields} for p in params]

    def acquire_params(self, full_cols, the_group):
        if full_cols:
            pparams = [p.dict for p in ProjectParameter.select()]
            dparams = [p.dict for p in DatabaseParameter.select()]
            aparams = [p.dict for p in ActivityParameter.select()]
        else:
            pparams = self.dehydrate_params(
                ProjectParameter.select(), ["name", "formula", "amount"]
            )
            dparams = self.dehydrate_params(
                DatabaseParameter.select(), ["database", "name", "formula", "amount"]
            )
            aparams = self.dehydrate_params(
                ActivityParameter.select(),
                ["database", "code", "group", "name", "formula", "amount"],
            )
        if the_group:
            if the_group.lower() == "project":
                dparams = []
                aparams = []
            else:
                pparams = []
                dparams = [p for p in dparams if p["database"] == the_group]
                aparams = [p for p in aparams if p["group"] == the_group]

        return pparams, dparams, aparams

    def choose_group(self, group_id):
        g = Group.get_by_id(group_id)
        pparams, dparams, aparams = self.acquire_params(False, g.name)
        if len(pparams) > 0:
            print("Project Parameters")
            print(tabulate(pparams, headers="keys"))
        if len(dparams) > 0:
            print("Database Parameters")
            print(tabulate(dparams, headers="keys"))
        if len(aparams) > 0:
            print("Activity Parameters")
            print(tabulate(aparams, headers="keys"))
        self.set_current_options(None)

    ########################
    # Default user actions #
    ########################

    def default(self, line):
        """No ``do_foo`` command - try to select from options."""
        if self.current_options["type"]:
            try:
                self.choose_option(int(line))
            except Exception:
                print(next(GRUMPY) + line)
        else:
            print(next(GRUMPY) + line)

    def emptyline(self):
        """No command entered!"""
        print(next(QUIET) + "\n(? for help)")

    #######################
    # Custom user actions #
    #######################

    def do_a(self, arg):
        """Go to activity id ``arg``"""
        key = (self.database, arg)
        if not self.database:
            print("Please choose a database first")
        # Support the use of int ids (used in bw25)
        try:
            a_numerical_id = int(arg)
            activity = get_activity(a_numerical_id)
            self.choose_activity(activity.key)
        except ValueError:
            try:
                _ = get_activity(key)
                self.choose_activity(key)
            except ValueError:
                print(f"Invalid activity id {key[1]}")

    def do_autosave(self, arg):
        """Toggle autosave behaviour.

        If autosave is on, the current database or activity is written to
        config.p each time it changes.
        """
        self.autosave = not self.autosave
        config.p["ab_autosave"] = self.autosave
        config.save_preferences()
        print("Autosave is now %s" % get_autosave_text(self.autosave))

    def do_b(self, arg):
        """List biosphere flows"""
        if not self.activity:
            print("Need to choose an activity first")
        else:
            es = get_activity(self.activity).exchanges()
            self.format_exchanges_as_options(es, "biosphere")
            self.print_current_options("Biosphere flows")

    def do_cfs(self, arg):
        """Print cfs of biosphere flows."""
        # Support multiple biosphere databases in one project
        if (
            self.activity and "biosphere" in self.database
        ) or self.method:  # show the cfs for the given flow
            current_methods = [m for m in methods if m[0] == self.method]
            if self.category:  # show cfs for current cat, current act
                current_methods = [m for m in current_methods if m[1] == self.category]
                if self.subcategory:
                    current_methods = [
                        m for m in current_methods if m[2] == self.subcategory
                    ]
        else:
            print("No method currently selected")  # Alternative: cfs for all methods?
            return False
        self.print_cfs(current_methods, self.activity)
        self.update_prompt()

    def do_tsv(self, arg):
        """write the latest table created as tsv file."""
        output_filename = "output.tsv"
        if arg:
            output_filename = arg
        if self.tabulate_data:
            with open(output_filename, "w") as f:
                f.write(self.tabulate_data)

    def do_cp(self, arg):
        """Clear preferences. Only for development."""
        self.autosave = False
        if config.p["ab_autosave"]:
            del config.p["ab_autosave"]
        del config.p["ab_project"]
        del config.p["ab_method"]
        del config.p["ab_database"]
        del config.p["ab_activity"]
        del config.p["ab_history"]
        config.save_preferences()
        self.project = self.database = self.activity = None
        self.method = self.category = self.subcategory = None
        self.update_prompt()

    def do_d(self, arg):
        """Load downstream activities"""
        if not self.activity:
            print("Need to choose an activity first")
        else:
            ds = get_activity(self.activity)
            unit = ds.get("unit", "")
            excs = self.get_downstream_exchanges(self.activity)
            self.format_exchanges_as_options(excs, "technosphere", unit)
            self.print_current_options("Downstream consumers")

    def do_db(self, arg):
        """Switch to a different database"""
        print(arg)
        if arg not in databases:
            print("'%(db)s' not a valid database" % {"db": arg})
        else:
            self.choose_database(arg)

    def do_h(self, arg):
        """Pretty print history of databases & activities"""
        self.set_current_options(
            {
                "type": "history",
                "options": self.history[::-1],
                "formatted": [self.format_history(o) for o in self.history[::-1]],
            }
        )
        self.print_current_options("Browser history")

    def do_help(self, args):
        print(HELP_TEXT)

    def do_i(self, arg):
        """Info on current activity.

        TODO: Colors could be improved."""
        if not self.activity:
            print("No current activity")
        else:
            ds = get_activity(self.activity)
            prod = [x for x in ds.exchanges() if x["input"] == self.activity]
            if "production amount" in ds and ds["production amount"]:
                amount = ds["production amount"]
            elif len(prod) == 1:
                amount = prod[0]["amount"]
            else:
                amount = 1.0
            print(
                """\n%(name)s

    Database: %(database)s
    ID: %(id)s
    numerical_id: %(n_id)s
    Product: %(product)s
    Production amount: %(amount).2g %(unit)s

    Location: %(location)s
    Classifications:
                        %(classifications)s
    Technosphere inputs: %(tech)s
    Biosphere flows: %(bio)s
    Reference flow used by: %(consumers)s\n"""
                % {
                    "name": ds.get("name", "Unknown"),
                    "product": ds.get("reference product") or ds.get("name", "Unknown"),
                    "database": self.activity[0],
                    "id": self.activity[1],
                    # numerical ids are a feature of bw25
                    "n_id": ds.get("id") or "NA",
                    "amount": amount,
                    "unit": ds.get("unit", ""),
                    "classifications": "\n\t\t\t".join(
                        [
                            "{}: {}".format(c[0], c[1])
                            for c in ds.get("classifications", [])
                        ]
                    ),
                    "location": ds.get("location", config.global_location),
                    "tech": len(
                        [x for x in ds.exchanges() if x["type"] == "technosphere"]
                    ),
                    "bio": len([x for x in ds.exchanges() if x["type"] == "biosphere"]),
                    "consumers": len(self.get_downstream_exchanges(self.activity)),
                }
            )

    def do_ii(self, arg):
        """Extended Info on current activity.

        TODO: Colors could be improved."""
        if not self.activity:
            print("No current activity")
        else:
            ds = get_activity(self.activity)
            prod = [x for x in ds.exchanges() if x["input"] == self.activity]
            if "production amount" in ds and ds["production amount"]:
                amount = ds["production amount"]
            elif len(prod) == 1:
                amount = prod[0]["amount"]
            else:
                amount = 1.0
            print(
                """Extended info \n%(name)s

    Database: %(database)s
    ID: %(id)s
    numerical_id: %(n_id)s
    Product: %(product)s
    Production amount: %(amount).2g %(unit)s

    Location: %(location)s
    Classifications:
                        %(classifications)s
    Technosphere inputs: %(tech)s
    Biosphere flows: %(bio)s
    Reference flow used by: %(consumers)s\n"""
                % {
                    "name": ds.get("name", "Unknown"),
                    "product": ds.get("reference product") or ds.get("name", "Unknown"),
                    "database": self.activity[0],
                    "id": self.activity[1],
                    # numerical ids are a feature of bw25
                    "n_id": ds.get("id") or "NA",
                    "amount": amount,
                    "unit": ds.get("unit", ""),
                    "classifications": "\n\t\t\t".join(
                        [
                            "{}: {}".format(c[0], c[1])
                            for c in ds.get("classifications", [])
                        ]
                    ),
                    "location": ds.get("location", config.global_location),
                    "tech": len(
                        [x for x in ds.exchanges() if x["type"] == "technosphere"]
                    ),
                    "bio": len([x for x in ds.exchanges() if x["type"] == "biosphere"]),
                    "consumers": len(self.get_downstream_exchanges(self.activity)),
                }
            )
            indentation_char = " " * 4
            line_length = 50  # TODO: use dynamic line lenght or take from prefs
            for field in [
                k
                for k in ds.keys()
                if k
                not in [
                    "name",
                    "product",
                    "database",
                    "location",
                    "unit",
                    "classifications",
                    "production amount",
                    "code",
                ]
            ]:
                field_contents = textwrap.wrap(repr(ds[field]), width=line_length)
                print("%(tab)s%(field)s:" % {"tab": indentation_char, "field": field})
                for line in field_contents:
                    print(
                        "%(tab)s%(line)s" % {"tab": indentation_char * 2, "line": line}
                    )

    def do_l(self, arg):
        """List current options"""
        if self.current_options["type"]:
            self.print_current_options()
        else:
            print("No current options")

    def do_lm(self, arg):
        """List methods"""
        self.list_methods()

    def do_lpj(self, arg):
        """List available projects"""
        self.list_projects()

    def do_ldb(self, arg):
        """List available databases"""
        self.list_databases()

    def do_mi(self, arg):
        """Show method information"""
        if self.method and self.category and self.subcategory:
            m = Method((self.method, self.category, self.subcategory))
            pp = pprint.PrettyPrinter(indent=4)
            pp.pprint(m.metadata)
        else:
            print("No current method selected")

    def do_n(self, arg):
        """Go to next page in paged options"""
        if not self.current_options["type"]:
            print("Not in page mode")
        elif self.page == self.max_page:
            print("No next page")
        else:
            self.page += 1
            self.print_current_options()

    def do_p(self, arg):
        """Go to previous page in paged options"""
        if not self.current_options["type"]:
            print("Not in page mode")
        elif arg:
            try:
                page = int(arg)
                if page < 0 or page > self.max_page:
                    print("Invalid page number")
                else:
                    self.page = page
                    self.print_current_options()
            except Exception:
                print("Can't convert page number %(page)s" % {"page": arg})
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
            print("Please choose a database first")
        else:
            re1a = r"."
            search_criterion = None
            if "-loc" in arg:
                re1a = r"(-loc\s)"  # Any Single Whitespace Character 1
                search_criterion = "location"
            elif "-cat" in arg:
                re1a = r"(-cat\s)"  # Any Single Whitespace Character 1
                search_criterion = "category"
            re1b = r"(\{.*\})"  # Curly Braces 1
            re2 = r"\s(.+)"
            rg = re.compile(re1a + re1b + re2, re.IGNORECASE | re.DOTALL)
            m = rg.search(arg)
            needle = arg  # Find the needle in the haystack
            if m is None and "-loc" in arg:
                print("Missing location in curly braces in command: -loc {MX} ...")
                return
            elif m is None and "-cat " in arg:
                print("Missing category in curly braces in command: -cat {water} ...")
                return
            elif m:
                c2 = m.group(2)
                criterion_value = c2.strip("{}")
                needle = m.group(3)
                print(
                    "Filtering for {} {} after search".format(
                        search_criterion, criterion_value
                    )
                )

            specials = [" ", "/", "-", "&"]
            if m and search_criterion == "location":
                if not any(
                    special in criterion_value for special in specials
                ):  # complex criterion_value
                    criteria = {"location": criterion_value}
                    results = Database(self.database).search(
                        needle, filter=criteria, limit=self.search_limit
                    )
                else:
                    results = Database(self.database).search(needle, limit=None)
                    results = [
                        r
                        for r in results
                        if r[search_criterion].lower() == criterion_value.lower()
                    ]
            elif m and search_criterion == "category":
                criteria = {"categories": criterion_value.split("::")}
                results = Database(self.database).search(
                    needle, filter=criteria, limit=self.search_limit
                )
            else:
                results = Database(self.database).search(
                    needle, limit=self.search_limit
                )
            results_keys = [r.key for r in results]
            self.set_current_options(
                {
                    "type": "activities",
                    "options": results_keys,
                    "formatted": [self.format_activity(key) for key in results],
                }
            )
            self.print_current_options(
                "Search results for %(query)s" % {"query": needle}
            )

    def do_u(self, arg):
        """List upstream processes"""
        if not self.activity:
            print("Need to choose an activity first")
        else:
            es = get_activity(self.activity).technosphere()
            self.format_exchanges_as_options(es, "technosphere")
            self.print_current_options("Upstream inputs")

    def do_up(self, arg):
        """List upstream processes"""
        if not self.activity:
            print("Need to choose an activity first")
        else:
            es = get_activity(self.activity).technosphere()
            self.format_exchanges_as_options(es, "technosphere", show_pedigree=True)
            self.print_current_options("Upstream inputs")

    def do_uu(self, arg):
        """List upstream processes extra info (formulas)"""
        if not self.activity:
            print("Need to choose an activity first")
        else:
            es = get_activity(self.activity).technosphere()
            self.format_exchanges_as_options(es, "technosphere", show_formulas=True)
            self.print_current_options("Upstream inputs")

    def do_web(self, arg):
        """Open a web browser to current activity"""
        if not self.activity:
            print("No current activity" % {})
        else:
            url = "http://127.0.0.1:5000/view/%(db)s/%(key)s" % {
                "db": self.database,
                "key": self.activity[1],
            }
            threading.Timer(0.1, lambda: webbrowser.open_new_tab(url)).start()

    def do_wh(self, arg):
        output_dir = projects.request_directory("export")
        fp = os.path.join(output_dir, "browser history.%s.txt" % time.ctime())
        with codecs.open(fp, "w", encoding="utf-8") as f:
            for line in self.history:
                f.write(line + "\n")
        print("History exported to %(fp)s" % {"fp": fp})

    def do_G(self, arg):
        """Do an LCIA of the selected activity + method[s]"""
        if self.activity and self.method:
            method_key_list = []

            if self.method and self.category and self.subcategory:
                method_id = (self.method, self.category, self.subcategory)
                method_key_list.append(method_id)
            elif self.method and self.category and self.subcategory is None:
                for m in methods:
                    if m[0] == self.method and m[1] == self.category:
                        method_key_list.append(m)
            elif self.method and self.category is None:
                for m in methods:
                    if m[0] == self.method:
                        method_key_list.append(m)
            bw2browser_cs = {
                "inv": [{get_activity(self.activity): 1}],
                "ia": method_key_list,
            }
            tmp_cs_id = uuid.uuid1()
            calculation_setups[str(tmp_cs_id)] = bw2browser_cs
            mlca = MultiLCA(str(tmp_cs_id))
            formatted_res = [
                [
                    mlca.methods[i][0],
                    mlca.methods[i][1],
                    mlca.methods[i][2],
                    Method(mlca.methods[i]).metadata["unit"],
                    score.pop(),
                ]
                for i, score in enumerate(mlca.results.T.tolist())
            ]
            self.tabulate_data = tabulate(
                formatted_res,
                headers=["method", "category", "subcategory", "unit", "score"],
                tablefmt="tsv",
            )
            print(
                tabulate(
                    formatted_res,
                    headers=["method", "category", "subcategory", "unit", "score"],
                )
            )
        else:
            print("Select at least a method first")

    def do_ta(self, arg):
        """Display top activities if an lca is active."""
        if self.activity:
            if self.method and self.category and self.subcategory:
                a = get_activity(self.activity)
                lca = a.lca((self.method, self.category, self.subcategory))
                top_a = lca.top_activities()
                print(tabulate(top_a, headers=["score", "supply", "Activity"]))

            else:
                print("Select at least a method first")

        else:
            print("Select an activity ")

    def do_te(self, arg):
        """Display top emissions if an lca is active."""
        if self.activity:
            if self.method and self.category and self.subcategory:
                a = get_activity(self.activity)
                lca = a.lca((self.method, self.category, self.subcategory))
                top_a = lca.top_emissions()

                print(tabulate(top_a, headers=["score", "supply", "Activity"]))

            else:
                print("Select at least a method first")

        else:
            print("Select an activity ")

    def do_aa(self, arg):
        """List all activities in the current database."""
        if not self.database:
            print("Please choose a database first")
        else:
            db = Database(self.database)
            activities = [activity for activity in db]
            # Sort activities by name
            if arg and isinstance(arg, str) and arg.lower() == "name":
                activities.sort(key=lambda a: a.get("name"))
            activity_keys = [
                (self.database, activity["code"]) for activity in activities
            ]
            formatted_activities = [self.format_activity(key) for key in activity_keys]
            self.set_current_options(
                {
                    "type": "activities",
                    "options": activity_keys,
                    "formatted": formatted_activities,
                }
            )

            self.print_current_options("Activities in database")

    def do_lpam(self, arg):
        """List all (Project, Database, Activity) parameters."""
        re1 = r"(-f\s)?"  # -f and a single whitespace Char
        re2a = r"(-g\s)"  # Any Single Whitespace Character 1
        re2b = r"(\{.*\})"  # Curly Braces 1
        rg = re.compile(re1 + re2a + re2b, re.IGNORECASE | re.DOTALL)
        m = rg.search(arg)
        full_cols = False
        the_group = None
        if m is None and "-g" in arg:
            print("Missing group in curly braces in command: -g {DANCE} ...")
            return
        elif m:
            c2 = m.group(3)
            the_group = c2.strip("{}")
            print("Filtering for group {} after search".format(the_group))
            full_cols = m.group(1) is not None
        if not self.project:
            print("Please choose a project first")
        else:
            pparams, dparams, aparams = self.acquire_params(full_cols, the_group)
            if len(pparams) > 0:
                print("Project Parameters")
                print(tabulate(pparams, headers="keys"))
            if len(dparams) > 0:
                print("Database Parameters")
                print(tabulate(dparams, headers="keys"))
            if len(aparams) > 0:
                print("Activity Parameters")
                print(tabulate(aparams, headers="keys"))

    def do_lpamg(self, arg):
        """List parameter groups."""
        groups = [g for g in Group.select()]
        self.set_current_options(
            {
                "type": "groups",
                "options": [g.id for g in groups],
                "formatted": [g.name for g in groups],
            }
        )
        self.print_current_options("Parameter groups: ")

    def do_ap(self, arg):
        """If an activity is selected, show its parameters."""
        if self.activity:
            param_objects = ActivityParameter.select().where(
                (ActivityParameter.code == self.activity[1])
                & (ActivityParameter.database == self.database)
            )
            aparams = []
            if "-f" not in arg:
                aparams = self.dehydrate_params(
                    param_objects,
                    ["database", "code", "group", "name", "formula", "amount"],
                )
            else:
                aparams = [p.dict for p in param_objects]
            if len(aparams) > 0:
                print(tabulate(aparams, headers="keys"))
            else:
                print(
                    "No Activity parameters for {}".format(get_activity(self.activity))
                )
        else:
            print("Please select an activity first")

    def do_dp(self, arg):
        """List all database parameters."""
        if self.database:
            param_objects = DatabaseParameter.select().where(
                DatabaseParameter.database == self.database
            )
            dparams = []
            if "-f" not in arg:
                dparams = self.dehydrate_params(
                    param_objects, ["name", "formula", "amount"]
                )
            else:
                dparams = [p.dict for p in param_objects]

            if len(dparams) > 0:
                print(tabulate(dparams, headers="keys"))
            else:
                print("No database parameters in database {}".format(self.database))
        else:
            print("Please select a database first")

    def do_pp(self, arg):
        """List all project parameters."""
        if self.project:
            param_objects = ProjectParameter.select()
            pparams = []
            if "-f" not in arg:
                pparams = self.dehydrate_params(
                    param_objects, ["database", "name", "formula", "amount"]
                )
            else:
                pparams = [p.dict for p in param_objects]
            if len(pparams) > 0:
                print(tabulate(pparams, headers="keys"))
            else:
                print("No project parameters in {}".format(self.project))
        else:
            print("Please select a project first")

    def do_fp(self, arg):
        """Find a specific parameter by name."""
        if self.project:
            pparams, dparams, aparams = self.acquire_params(False, None)

            for p in pparams:
                p.update({"parameter type": "project"})
            for p in dparams:
                p.update({"parameter type": "database"})
            for p in aparams:
                p.update({"parameter type": "activity"})

            p = [p for p in pparams + dparams + aparams if p["name"] == arg]
            if len(p) > 0:
                print(tabulate(p, headers="keys"))

        else:
            print("Please select a project first")

    def do_sp(self, arg):
        """Search for a parameter by name, accepting wildcards in arg."""
        if self.project:
            pparams_objects = ProjectParameter.select().where(
                ProjectParameter.name % arg
            )
            dparams_objects = DatabaseParameter.select().where(
                DatabaseParameter.name % arg
            )
            aparams_objects = ActivityParameter.select().where(
                ActivityParameter.name % arg
            )

            pparams = self.dehydrate_params(
                pparams_objects, ["database", "name", "formula", "amount"]
            )
            dparams = self.dehydrate_params(
                dparams_objects, ["name", "formula", "amount"]
            )
            aparams = self.dehydrate_params(
                aparams_objects,
                ["database", "code", "group", "name", "formula", "amount"],
            )

            for p in pparams:
                p.update({"parameter type": "project"})
            for p in dparams:
                p.update({"parameter type": "database"})
            for p in aparams:
                p.update({"parameter type": "activity"})

            p = [p for p in pparams + dparams + aparams]
            if len(p) > 0:
                print(tabulate(p, headers="keys"))
        else:
            print("Please select a project first")


def main():
    arguments = docopt(__doc__, version="Brightway2 Activity Browser 2.0")
    activitybrowser = ActivityBrowser()
    activitybrowser._init(
        project=arguments["<project>"],
        database=arguments["<database>"],
        activity=arguments["<activity-id>"],
    )
    activitybrowser.cmdloop()


if __name__ == "__main__":
    main()
