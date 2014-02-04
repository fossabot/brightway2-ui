# -*- coding: utf-8 -*-
from __future__ import print_function
from brightway2 import databases, methods, Database, config, reset_meta
from bw2data.io import download_biosphere, BW2Package, download_methods
from bw2data.logs import upload_logs_to_server
from bw2data.colors import Fore, safe_colorama
from errors import UnknownAction, UnknownDatabase
import datetime
import os
import sys


def exit(text):
    with safe_colorama():
        print(text)
    sys.exit(1)


def strfdelta(tdelta):
    """From http://stackoverflow.com/questions/8906926/formatting-python-timedelta-objects"""
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    fmt = "{days} days {hours}h:{minutes}m:{seconds}s old"
    return fmt.format(**d)


class Controller(object):
    def dispatch(self, **kwargs):
        options = ("list", "details", "copy", "backup", "validate", "versions",
            "revert", "remove", "export", "setup", "upload_logs", "color")
        for option in options:
            if kwargs[option]:
                return getattr(self, option)(kwargs)
        if kwargs["import"]:
            return self.importer(kwargs)
        raise UnknownAction("No suitable action found")

    def get_name(self, kwargs):
        name = kwargs['<name>']
        if name not in databases:
            raise UnknownDatabase("Can't find the database %s" % name)
        return name

    def color(self, kwargs):
        if kwargs['on']:
            if 'no_color' in config.p:
                del config.p['no_color']
                config.save_preferences()
            return u"Color turned on"
        elif kwargs['off']:
            config.p['no_color'] = True
            config.save_preferences()
            return u"Color turned off"
        else:
            return

    def list(self, kwargs):
        if kwargs['databases']:
            return databases.list
        elif kwargs['methods']:
            return methods.list
        else:
            return

    def details(self, kwargs):
        return databases[self.get_name(kwargs)]

    def copy(self, kwargs):
        name = self.get_name(kwargs)
        new_name = kwargs['<newname>']
        Database(name).copy(new_name)
        return u"%s copy to %s successful" % (name, new_name)

    def backup(self, kwargs):
        name = self.get_name(kwargs)
        Database(name).backup()
        return u"%s backup successful" % name

    def validate(self, kwargs):
        name = self.get_name(kwargs)
        db = Database(name)
        db.validate(db.load())
        return u"%s data validated successfully" % name

    def versions(self, kwargs):
        now = datetime.datetime.now()
        return [(x[0], x[1].strftime("Created %A, %d. %B %Y %I:%M%p"),
            strfdelta(now - x[1])) for x in Database(self.get_name(kwargs)
            ).versions()]

    def revert(self, kwargs):
        name = self.get_name(kwargs)
        revision = int(kwargs["<revision>"])
        Database(name).revert(revision)
        return u"%s reverted to revision %s" % (name, revision)

    def remove(self, kwargs):
        name = self.get_name(kwargs)
        Database(name).deregister()
        return u"%s removed" % name

    def importer(self, kwargs):
        return
        # Ecospold1Importer().importer(path, name)

    def export(self, kwargs):
        name = self.get_name(kwargs)
        # dependencies = kwargs["--include-dependencies"]
        path = BW2Package.export_obj(Database(name))
        return u"%s exported to bw2package: %s" % (name, path)

    def setup(self, kwargs):
        if kwargs['--data-dir']:
            data_dir = unicode(kwargs['--data-dir'])
            if os.path.exists(data_dir):
                exit(Fore.RED + "Error" + Fore.RESET + ": This directory already exists")
            elif not os.access(os.path.abspath(os.path.join(data_dir, "..")), os.W_OK):
                exit(Fore.RED + "Error" + Fore.RESET + ": Given directory is not writable")
                return
            question_text = safe_colorama("\nPlease confirm that you want to create the following data directory:\n\t" + Fore.BLUE + data_dir + Fore.RESET + "\n" + Fore.GREEN + "y" + Fore.RESET + "/" + Fore.RED + "n" + Fore.RESET + " (or any other input):")
            response = raw_input(question_text)
            if response != "y":
                exit(Fore.RED + "\nSetup cancelled" + Fore.RESET)
                return
            os.mkdir(data_dir)
            config.dir = data_dir
            reset_meta()
        config.create_basic_directories()
        download_biosphere()
        download_methods()
        exit(Fore.GREEN + u"Brightway2 setup successful" + Fore.RESET)

    def upload_logs(self, kwargs):
        response = upload_logs_to_server({'comment': kwargs.get('COMMENT', "")})
        if response.text == "OK":
            return "Logs uploaded successfully"
        else:
            return "There was a problem uploading the log files"
