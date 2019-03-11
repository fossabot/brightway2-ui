# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *
from future.standard_library import install_aliases
install_aliases()

from .jobs import JobDispatch, InvalidJob
from .utils import get_job_id, get_job, set_job_status, json_response, \
    get_dynamic_media_folder
from bw2analyzer import DatabaseExplorer, SerializedLCAReport, DatabaseHealthCheck
from bw2calc.speed_test import SpeedTest
from bw2calc.lca import LCA
from bw2data import (
    Database,
    databases,
    JsonWrapper,
    Method,
    methods,
    preferences,
    projects,
    get_activity,
)
from bw2data.search import Searcher
from bw2io import bw2setup
from flask import url_for, render_template, request, redirect, abort
from genson import SchemaBuilder
from stats_arrays import uncertainty_choices
from urllib.parse import unquote
import multiprocessing
import os
import pprint

from . import bw2webapp


def get_windows_drive_letters():
    import win32api
    return [x for x in win32api.GetLogicalDriveStrings().split('\000') if x]


def jqfilepicker_unquote(source):
    """
Stupid Javascript (insert joke here...) and jQueryFilePicker
http://stackoverflow.com/questions/300445/how-to-unquote-a-urlencoded-unicode-string-in-python
https://github.com/simogeo/Filemanager/issues/40
    """
    result = unquote(source)
    if '%u' in result:
        result = result.replace('%u', '\\u').decode('unicode_escape')
    return result

###########################
### Basic functionality ###
###########################


@bw2webapp.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@bw2webapp.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

############
### Jobs ###
############


@bw2webapp.route("/status/<job>")
def job_status(job):
    try:
        return json_response(get_job(job))
    except:
        abort(404)


@bw2webapp.route("/dispatch/<job>")
def job_dispatch(job):
    try:
        job_data = get_job(job)
    except:
        abort(404)
    try:
        return JobDispatch()(job, **job_data)
    except InvalidJob:
        abort(500)

###################
### File Picker ###
###################


@bw2webapp.route("/filepicker")
def fp_test():
    return render_template("fp.html")


@bw2webapp.route("/fp-api", methods=["POST"])
def fp_api():
    full = bool(request.args.get("full", False))
    path = jqfilepicker_unquote(request.form["dir"])
    try:
        root, dirs, files = os.walk(path).next()
    except StopIteration:
        try:
            # Only files from now on...
            root, dirs = path, []
            files = os.listdir(root)
        except:
            # Don't have permissions for this directory or other OS error
            files = []
    data = []
    files = [x for x in files if x[0] != "."]
    if not full and len(files) > 20:
        files = files[:20] + ["(and %s more files...)" % (len(files) - 20)]
    for dir_name in dirs:
        if dir_name[0] == ".":
            continue
        data.append({
            "dir": True,
            "path": os.path.join(root, dir_name),
            "name": dir_name
        })
    for file_name in files:
        data.append({
            "dir": False,
            "ext": file_name.split(".")[-1].lower(),
            "path": os.path.join(root, file_name),
            "name": file_name
        })
    return render_template("fp-select.html", dirtree=data)

#######################
### Getting started ###
#######################

# def get_windows_drives():
#     if not config._windows:
#         return {'windows': False}
#     else:
#         return {
#             'windows': True,
#             'drive_letters': get_windows_drive_letters(),
#             'current_drive': os.path.splitdrive(os.getcwd())[0]
#         }

# @bw2webapp.route('/start/path', methods=["POST"])
# def set_path():
#     path = urllib2.unquote(request.form["path"])
#     dirname = urllib2.unquote(request.form["dirname"])
#     set_data_dir(os.path.join(path, dirname))
#     return "1"


# @bw2webapp.route('/start/biosphere')
# def install_biosphere():
#     bw2setup()
#     return "1"


# @bw2webapp.route('/start')
# def start():
#     TODO: Add projects
#     return render_template(
#         "start.html",
#         root_path=JsonWrapper.dumps(os.path.abspath("/")),
#         **get_windows_drives()
#     )

#################
### Importing ###
#################


@bw2webapp.route("/import/database", methods=["GET", "POST"])
def import_database():
    if request.method == "GET":
        return render_template("import-database.html", **get_windows_drives())
    else:
        raise NotImplemented
        path = unquote(request.form["path"])
        name = unquote(request.form["name"])
        Ecospold1Importer().importer(path, name)
        return "1"


@bw2webapp.route("/import/method", methods=["GET", "POST"])
def import_method():
    if request.method == "GET":
        return render_template("import-method.html", **get_windows_drives())
    else:
        raise NotImplemented
        path = unquote(request.form["path"])
        EcospoldImpactAssessmentImporter().importer(path)
        return "1"

###################
### Basic views ###
###################


@bw2webapp.route('/')
@bw2webapp.route('/project/<projectname>')
def index(projectname=None):
    if projectname is None:
        projectname = 'default'
    projects.set_current(projectname)
    dbs = [{
        "name": key,
        "number": value.get("number", 0),
        "version": value.get("version", 0),
        "url": url_for('database_explorer', name=key)
        } for key, value in databases.items()]
    dbs.sort(key=lambda x: x['name'])
    ms = [{
        "name": " - ".join(key),
        "unit": value.get("unit", "unknown"),
        "num_cfs": value.get("num_cfs", 0),
        "url": url_for("method_explorer", abbreviation=value['abbreviation'])
    } for key, value in methods.items()]
    ms.sort(key = lambda x: x['name'])
    pjs = [{"name": p.name,
        "url": url_for('index', projectname=p.name)
        } 
            for p in projects ]
    context = {
        'databases': JsonWrapper.dumps(dbs),
        'methods': JsonWrapper.dumps(ms),
        'projects': JsonWrapper.dumps(pjs),
        'currentproject': projects.current
        }
    return render_template("index.html", **context)


@bw2webapp.route('/ping', methods=['GET'])
def ping():
    # Used to check if web UI is running
    return "pong"


@bw2webapp.route('/settings', methods=["GET", "POST"])
def change_settings():
    if request.method == "GET":
        context = {
            "preferences": preferences,
            "cpu_count": multiprocessing.cpu_count(),
        }
        return render_template("settings.html", **context)
    else:
        preferences["cpu_cores"] = int(request.form["cpu-cores"])
        preferences["iterations"] = int(request.form["iterations"])
        return redirect(url_for('index'))


@bw2webapp.route('/speedtest')
def speed_test():
    st = SpeedTest()
    return str(250 * int(40 * st.ratio()))


#################
### Searching ###
#################


@bw2webapp.route('/search')
def whoosh_index():
    return render_template('search.html')

@bw2webapp.route('/search_request', methods=["POST"])
def whoosh_search():
    try:
        from bw2search import Searcher
    except ImportError:
        abort(500)

    try:
        request_data = JsonWrapper.loads(request.data)
    except:
        abort(400)

    data = {'results': Searcher().search(request_data['search_string'])}
    print(data)
    return json_response(data)


##############################
### Databases and datasets ###
##############################


@bw2webapp.route("/database/<name>")
def database_explorer(name):
    try:
        meta = databases[name]
    except KeyError:
        return abort(404)
    data = Database(name).load(as_dict=True)
    depends = [{
        'name': obj,
        'url': url_for('database_explorer', name=obj)
    } for obj in sorted(meta['depends'])]
    json_data = [{
        'name': value.get('name', "Unknown"),
        'categories': ",".join(value.get('categories', [])),
        'location': value.get('location', ''),
        'unit': value.get('unit', ''),
        'url': url_for('activity_dataset-canonical', database=name, code=key[1]),
        'num_exchanges': len(value.get('exchanges', [])),
        'key': key
        } for key, value in data.items()]
    json_data.sort(key = lambda x: x['name'])
    return render_template(
        "database.html",
        meta=meta,
        name=name,
        depends=depends,
        data=JsonWrapper.dumps(json_data),
        health_check_url=url_for('database_health_check', database=name),
        backup_url = url_for('backup_database', database=name),
        delete_url = url_for('delete_database', database=name),
        location_facet_url = url_for('facet', database=name, facet="location"),
        unit_facet_url = url_for('facet', database=name, facet="unit"),
    )


@bw2webapp.route("/delete/<database>", methods=["POST"])
def delete_database(database):
    if database not in databases:
        return abort(404)
    del databases[database]
    return ''


@bw2webapp.route("/backup/<database>", methods=["POST"])
def backup_database(database):
    if database not in databases:
        return abort(404)
    return Database(database).backup()


@bw2webapp.route("/view/<database>/<code>", endpoint="activity_dataset-canonical")
@bw2webapp.route("/view/<database>/<code>/sc_graph")
def activity_dataset(database, code, sc_graph_json=False):
    if database not in databases:
        return abort(404)
    try:
        the_activity = get_activity((database, code))
        the_activity_data = the_activity.as_dict()
    except KeyError:
        return abort(404)

    try:
        preferred_lcia = tuple(config.p[u'preferred lcia method'])
        assert preferred_lcia in methods
        lca = LCA({(database, code): 1}, method=preferred_lcia)
        lca.lci(factorize=1)
        lca.lcia()
        single_score = lca.score
    except:
        preferred_lcia = lca = single_score = False

    rp = [x for x in the_activity_data.get('exchanges', []) if x['type'] == "production"]
    if len(rp) == 1:
        rp = rp[0]['amount']
    else:
        rp = 0

    def format_sc(key):
        a = get_activity(key)
        return {
            'id': "-".join(key),
            'children': [],
            'name': a.get('name', "Unknown"),
            'data': {'url': url_for('activity_dataset-canonical', 
                database=a.get('database'), 
                code=a.get('code'))},
        }

    if request.url_rule.rule[-9:] == "/sc_graph":
        data = {
        'id': database + "-" + code,
        'name': the_activity_data.get('name', "Unknown"),
        'data': {'origin': True},
        'children': [
            format_sc(exc['input'])
            for exc in the_activity_data.get('exchanges', []) 
            if 'input' in exc
            and exc['type'] == "technosphere"
        ]}
        print("Supply chain data")
        print(data)
        return json_response(data)

    def format_ds(key, amount, biosphere=False):
        a = get_activity(key)
        a_data = a.as_dict()
        data =  {
            'name': a_data.get('name', "Unknown"),
            'categories': ",".join(a_data.get('categories', [])),
            'location': a_data.get('location', ''),
            'unit': a_data.get('unit', ''),
            'url': url_for('activity_dataset-canonical', 
                database=a_data.get('database'), 
                code=a_data.get('code')),
            'amount': amount
            }
        if lca and not biosphere:
            lca.redo_lcia({(a.get('database'), a.get('code')): amount})
            data['score'] = lca.score
        return data

    biosphere = [format_ds(x['input'], x['amount'], True) for x in the_activity.biosphere()]
    technosphere = [format_ds(x['input'], x['amount']) for x in the_activity.exchanges()]

    sc_data = {
        'id': database + "-" + code,
        'name': the_activity_data.get('name', "Unknown"),
        'data': {'origin': True},
        'children': [
            format_sc(exc['input'])
            for exc in the_activity.technosphere()
            if 'input' in exc
        ]
    }

    return render_template(
        "activity.html",
        data=the_activity_data,
        ref_prod=rp,
        edit_url=url_for("json_editor", database=database, code=code),
        sc_data=JsonWrapper.dumps(sc_data),
        biosphere=JsonWrapper.dumps(biosphere),
        technosphere=JsonWrapper.dumps(technosphere),
        single_score=single_score,
        lca=bool(lca),
        preferred_lcia="-".join(preferred_lcia) if lca else None
    )


@bw2webapp.route("/view/<database>/<code>/json")
def json_editor(database, code):
    if database not in databases:
        return abort(404)
    try:
        data = get_activity((database, code)).as_dict()
        builder = SchemaBuilder()
        builder.add_object(data)
        theschema = builder.to_schema()
    except KeyError:
        return abort(404)
    return render_template("jsoneditor.html", jsondata=JsonWrapper.dumps(data), jsonchema=theschema)


###################
### Facet views ###
###################


@bw2webapp.route("/database/<database>/facet/<facet>")
def facet(database, facet):
    def reformat(key, ds):
        return {
            'name': ds.get('name', "Unknown"),
            'categories': ",".join(ds.get('categories', [])),
            'location': ds.get('location', ''),
            'unit': ds.get('unit', ''),
            'url': url_for('activity_dataset-canonical', database=key[0], code=key[1]),
        }

    if database not in databases:
        return abort(404)
    data = Database(database).load()
    facets = {}
    for key, ds in data.items():
        try:
            facets.setdefault(ds[facet], []).append(reformat(key, ds))
        except KeyError:
            abort(404)
    facet_data = [
        (key + " (%s)" % len(facets[key]), "facet%s" % index, JsonWrapper.dumps(facets[key]))
        for index, key in enumerate(sorted(facets.keys()))
    ]
    tree_data = [{'id': o[1], 'text': o[0]} for o in facet_data]
    tree_data[0]['state'] = {'selected': True}
    kwargs = {
        "tree_data": JsonWrapper.dumps(tree_data),
        "data": facet_data,
        "db": database,
        "facet": facet
    }
    return render_template("facets.html", **kwargs)

####################
### Health check ###
####################


@bw2webapp.route("/database/<database>/health-check")
def database_health_check(database):
    if database not in databases:
        return abort(404)
    data = Database(database).load()
    np = len(data)

    def reformat(key, score=None):
        ds = data[key]
        return {
            'name': ds.get('name', "Unknown"),
            'categories': ",".join(ds.get('categories', [])),
            'location': ds.get('location', ''),
            'unit': ds.get('unit', ''),
            'url': url_for('activity_dataset-canonical', database=key[0], code=key[1]),
            'score': score
        }

    dhc = DatabaseHealthCheck(database).check(get_dynamic_media_folder())
    dhc['pr'] = JsonWrapper.dumps([reformat(key, score * np) for score, key in dhc['pr'][:20]])
    dhc['uncertainty'] = sorted([
        (uncertainty_choices[key].description, value['total'], value['bad'])
        for key, value in dhc['uncertainty'].items()
        if value['total']
    ], key=lambda x: x[1], reverse=True)
    for obj in ('mo', 'me', 'sp'):
        if dhc[obj]:
            dhc[obj] = JsonWrapper.dumps([reformat(key, number) for key, number in dhc[obj]])
    for obj in ('nsp', 'ob'):
        if dhc[obj]:
            dhc[obj] = JsonWrapper.dumps([reformat(key) for key in dhc[obj]])

    return render_template("health-check.html", database=database, **dhc)


###########
### LCA ###
###########


@bw2webapp.route('/database/<name>/names')
def activity_names(name):
    if name not in databases:
        return abort(404)
    return json_response([{
        "label": u"%s (%s, %s)" % (
            value.get("name", "Unknown"),
            value.get("unit", "Unknown"),
            value.get("location", "Unknown")),
        "value": {
            "u": value.get("unit", "Unknown"),
            "l": value.get("location", "Unknown"),
            "n": value.get("name", "Unknown"),
            "k": key
        }} for key, value in Database(name).load(as_dict=True).items()])


def get_tuple_index(t, i):
    try:
        return t[i]
    except IndexError:
        return "---"


@bw2webapp.route('/lca', methods=["GET", "POST"])
def lca():
    if request.method == "GET":
        ms = [{
            "name": " - ".join(key),
            "key": key,
            "unit": value.get("unit", "unknown"),
            "num_cfs": value.get("num_cfs", 0),
            "url": url_for("method_explorer", abbreviation=value['abbreviation'])
        } for key, value in methods.items()]
        ms.sort(key = lambda x: x['name'])
        return render_template("select.html",
            db_names=[x for x in databases.list if x != config.biosphere],
            lcia_methods=JsonWrapper.dumps(ms)
        )
    else:
        try:
            request_data = JsonWrapper.loads(request.data)
        except:
            abort(400)
        demand = {tuple(o['key']): o['amount'] for o in request_data['activities']}
        method = tuple(request_data['method'])
        iterations = config.p.get("iterations", 1000)
        cpu_count = config.p.get("cpu_cores", None)
        report = SerializedLCAReport(demand, method, iterations, cpu_count)
        print("Starting SerializedLCAReport calculation")
        report.calculate()
        print("Finished report calculation")
        if config.p.get('upload_reports', 0):
            try:
                report.upload()
            except:
                # No online report no cry
                pass
        report.write()
        print(report.uuid)
        return report.uuid


@bw2webapp.route('/report/<uuid>')
def report(uuid):
    data = open(os.path.join(
        config.dir, "reports", "report.%s.json" % uuid)).read()
    return render_template("report.html", data=data)


###############
### Methods ###
###############


# @bw2webapp.route("/explore_methods")
# def method_explorer():


@bw2webapp.route("/method/<abbreviation>")
def method_explorer(abbreviation):
    method = [key for key, value in methods.items()
        if value[u'abbreviation'] == abbreviation]
    if not len(method) == 1:
        abort(404)
    method = method[0]
    meta = methods[method]
    json_data = []
    for values in Method(method).load():
        if len(values) >= 3:
            key, value, geo = values[:3]
        else:
            key, value = values[:2]
            geo = config.global_location
        flow = Database(key[0]).load()[key]
        json_data.append({
            u'name': flow.get(u'name', u"Unknown"),
            u'unit': flow.get(u'unit', ''),
            u'categories': ",".join(flow.get(u'categories', [])),
            u'cf': value[u'amount'] if isinstance(value, dict) else value,
            u'location': geo,
            u'url': url_for('activity_dataset-canonical', database=key[0], code=key[1])
        })
    json_data.sort(key=lambda x: x[u'name'])
    return render_template(
        "method.html",
        name=method,
        unit=meta.get(u'unit', u''),
        description=meta.get(u'description', u''),
        data=JsonWrapper.dumps(json_data)
    )

###################
### Development ###
###################


def short_name(name):
    return " ".join(name.split(" ")[:3])[:25]


@bw2webapp.route("/database/tree/<name>/<code>")
@bw2webapp.route("/database/tree/<name>/<code>/<direction>")
def database_tree(name, code, direction="backwards"):
    def format_d(d):
        return [{"name": short_name(data[k]["name"]),
            "children": format_d(v) if isinstance(v, dict) \
                else [{"name": short_name(data[x]["name"])} for x in v]
            } for k, v in d.items()]

    if name not in databases:
        abort(404)
    explorer = DatabaseExplorer(name)
    data = Database(name).load()
    if (name, code) not in data:
        try:
            code = int(code)
            assert (name, code) in data
        except:
            return abort(404)
    if direction == "forwards":
        nodes = explorer.uses_this_process((name, code), 1)
    else:
        nodes = explorer.provides_this_process((name, code), 1)
    for db in databases[name]["depends"]:
        data.update(Database(db).load())
    formatted = {
        "name": short_name(data[(name, code)]["name"]),
        "children": format_d(nodes)
    }
    pprint.pprint(formatted)
    return render_template("database_tree.html",
        f=formatted,
        activity=data[(name, code)]["name"],
        direction=direction.title())


@bw2webapp.route('/progress')
def progress_test():
    job_id = get_job_id()
    status_id = get_job_id()
    set_job_status(job_id, {"name": "progress-test", "status": status_id})
    set_job_status(status_id, {"status": "Starting..."})
    return render_template("progress.html", **{"job": job_id,
        'status': status_id})


@bw2webapp.route('/hist')
def hist_test():
    job_id = get_job_id()
    status_id = get_job_id()
    set_job_status(job_id, {"name": "hist-test", "status": status_id})
    set_job_status(status_id, {"status": "Starting..."})
    return render_template("hist.html", **{"job": job_id, 'status': status_id})

# use werkzeug.utils.secure_filename to check uploaded file names
# http://werkzeug.pocoo.org/docs/utils/

# to send static files not from 'static': send_from_directory
# http://flask.pocoo.org/docs/api/#flask.send_from_directory
# http://stackoverflow.com/questions/9513072/more-than-one-static-path-in-local-flask-instance
