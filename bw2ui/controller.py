# encoding: utf-8
from brightway2 import databases, methods, Database, Method
from brightway2.io import EcospoldImporter, EcospoldImpactAssessmentImporter


class Controller(object):
    def database_or_method(self, name):
        if name in databases:
            return (name, "database")
        elif tuple(name.split(":")) in methods:
            return (tuple(name.split(":")), "method")
        else:
            raise ValueError

    def dispatch(self, **kwargs):
        if kwargs['list']:
            return self.list(kwargs)
        elif kwargs['details']:
            return self.details(kwargs)
        elif kwargs['remove']:
            return self.remove(kwargs)
        elif kwargs['import'] and kwargs['database']:
            return self.import_database(kwargs)
        elif kwargs['import'] and kwargs['method']:
            return self.import_method(kwargs)
        return "This action not yet supported!"

    def list(self, kwargs):
        if kwargs['databases']:
            return databases.list
        else:
            return methods.list

    def details(self, kwargs):
        name, kind = self.database_or_method(kwargs['<name>'])
        if kind == "database":
            return databases[name]
        else:
            return methods[name]

    def remove(self, kwargs):
        name, kind = self.database_or_method(kwargs['<name>'])
        if kind == "database":
            Database(name).deregister()
        else:
            Method(name).deregister()

    def import_database(self, path):
        EcospoldImporter.import_directory(path)

    def import_method(self, path):
        EcospoldImpactAssessmentImporter(path)
