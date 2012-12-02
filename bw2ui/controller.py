# -*- coding: utf-8 -*-
from brightway2 import databases, methods, Database, Method, config, reset_meta
from bw2data.io import EcospoldImporter, EcospoldImpactAssessmentImporter
from errors import UnknownAction


class Controller(object):
    def database_or_method(self, name):
        if name in databases:
            return (name, "database")
        elif name in methods:
            return (name, "method")
        elif tuple(name.split(":")) in methods:
            return (tuple(name.split(":")), "method")
        else:
            raise ValueError

    def dispatch(self, **kwargs):
        if kwargs.get('list', None):
            return self.list(kwargs)
        elif kwargs.get('details', None):
            return self.details(kwargs)
        elif kwargs.get('remove', None):
            return self.remove(kwargs)
        elif kwargs.get('import', None) and kwargs.get('database', None):
            return self.import_database(kwargs)
        elif kwargs.get('import', None) and kwargs.get('method', None):
            return self.import_method(kwargs)
        raise UnknownAction("No suitable action found")

    def list(self, kwargs):
        if kwargs.get('databases', None):
            return databases.list
        else:
            return methods.list

    def details(self, kwargs):
        name, kind = self.database_or_method(kwargs.get('<name>', None))
        if kind == "database":
            return databases[name]
        else:
            return methods[name]

    def remove(self, kwargs):
        name, kind = self.database_or_method(kwargs.get('<name>', None))
        if kind == "database":
            Database(name).deregister()
        else:
            Method(name).deregister()

    def import_database(self, path):
        EcospoldImporter.import_directory(path)

    def import_method(self, path):
        EcospoldImpactAssessmentImporter(path)

    def setup_directory(self, path):
        config.dir = path
        config.create_basic_directories()
        reset_meta()
