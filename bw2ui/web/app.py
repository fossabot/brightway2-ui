# -*- coding: utf-8 -*-
from brightway2 import config, databases, methods, Database, Method, \
    JsonWrapper, reset_meta
from bw2analyzer import ContributionAnalysis, DatabaseExplorer
from bw2calc import LCA, ParallelMonteCarlo
from bw2data.io import EcospoldImporter, EcospoldImpactAssessmentImporter
from flask import Flask, url_for, render_template, request, redirect, abort
from fuzzywuzzy import process
from jobs import JobDispatch, InvalidJob
from utils import get_job_id, get_job, set_job_status, json_response
import itertools
import math
import multiprocessing
import numpy as np
import os
import platform
import requests
import urllib2


app = Flask(__name__)

###########################
### Basic functionality ###
###########################


@app.errorhandler(404)
def page_not_found(e):
    # Log error?
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    # Log error?
    return render_template('500.html'), 500

############
### Jobs ###
############


@app.route("/status/<job>")
def job_status(job):
    try:
        return json_response(get_job(job))
    except:
        abort(404)


@app.route("/dispatch/<job>")
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


@app.route("/filepicker")
def fp_test():
    return render_template("fp.html")


@app.route("/fp-api", methods=["POST"])
def fp_api():
    full = bool(request.args.get("full", False))
    path = urllib2.unquote(request.form["dir"])
    try:
        root, dirs, files = os.walk(path).next()
    except StopIteration:
        # Only files from now on...
        root, dirs = path, []
        files = os.listdir(root)
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


@app.route('/start/path', methods=["POST"])
def set_path():
    path = urllib2.unquote(request.form["path"])
    dirname = urllib2.unquote(request.form["dirname"])
    dirpath = os.path.join(path, dirname)
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)

    user_dir = os.path.expanduser("~")
    if platform.system == "Windows":
        filename = "brightway2path.txt"
    else:
        filename = ".brightway2path"
    with open(os.path.join(user_dir, filename), "w") as f:
        f.write(dirpath)

    config.reset()
    config.is_temp_dir = False
    config.create_basic_directories()
    reset_meta()
    return "1"


@app.route('/start/biosphere')
def install_biosphere():
    # Download and format data
    keys, values = JsonWrapper.loads(
        requests.get("http://mutel.org/biosphere.json").content)
    data = dict(zip([tuple(x) for x in keys], values))
    biosphere = Database("biosphere")
    biosphere.register(
        format=["Handmade", -1],
        depends=[],
        num_processes=len(data),
        )
    biosphere.write(data)
    biosphere.process()
    return "1"


@app.route('/start')
def start():
    return render_template("start.html")
    """
    You are currently saving your work in a temporary directory that can be deleted at any time. You can let Brightway2 create a workspace in your home directory, or you can specify a different directory by typing in the full path below:
    """

#################
### Importing ###
#################


@app.route("/import/database", methods=["GET", "POST"])
def import_database():
    if request.method == "GET":
        return render_template("import-database.html")
    else:
        path = urllib2.unquote(request.form["path"])
        name = urllib2.unquote(request.form["name"])
        EcospoldImporter().importer(path, name)
        return "1"


@app.route("/import/method", methods=["GET", "POST"])
def import_method():
    if request.method == "GET":
        return render_template("import-method.html")
    else:
        path = urllib2.unquote(request.form["path"])
        EcospoldImpactAssessmentImporter().importer(path)
        return "1"

###################
### Basic views ###
###################


@app.route('/')
def index():
    if config.is_temp_dir and not config.p.get("temp_dir_ok", False):
        return redirect(url_for('start'))
    dbs = [{
        "name": key,
        "number": value["number"],
        "version": value["version"]
        } for key, value in databases.iteritems()]
    ms = [{
        "name": " - ".join(key),
        "unit": value["unit"],
        "num_cfs": value["num_cfs"]
    } for key, value in methods.iteritems()]
    context = {
        'databases': dbs,
        'methods': ms,
        'config': config
        }
    return render_template("index.html", **context)


@app.route('/settings', methods=["GET", "POST"])
def change_settings():
    if request.method == "GET":
        context = {
            "config": config,
            "cpu_count": multiprocessing.cpu_count(),
            "current_cpu_count": config.p.get("cpu_count",
                multiprocessing.cpu_count()),
        }
        return render_template("settings.html", **context)
    else:
        return ""

###########
### LCA ###
###########


@app.route('/database/<name>/names')
def activity_names(name):
    if name not in databases:
        return abort(404)
    db = Database(name)
    data = db.load()
    return json_response([{
        "label": u"%s (%s, %s)" % (
            value["name"],
            value.get("unit", "?"),
            value.get("location", "?")),
        "value": {
            "u": value["unit"],
            "l": value["location"],
            "n": value["name"],
            "k": key
        }} for key, value in data.iteritems()])


def get_tuple_index(t, i):
    try:
        return t[i]
    except IndexError:
        return "---"


@app.route('/lca', methods=["GET", "POST"])
def lca():
    if request.method == "GET":
        return render_template("select.html",
            db_names=[x for x in databases.list if x != "biosphere"],
            lcia_methods=[{
                "l1": get_tuple_index(key, 0),
                "l2": get_tuple_index(key, 1),
                "l3": get_tuple_index(key, 2),
                "u": value["unit"],
                "n": value["num_cfs"],
            } for key, value in methods.data.iteritems() if value.get(
                "num_cfs", 1)])
    else:
        fu = dict([
            (tuple(x[0]), x[1]) for x in JsonWrapper.loads(
                request.form["activity"])
            ])
        method = tuple(JsonWrapper.loads(request.form["method"]))
        context = {}
        lca = LCA(fu, method)
        lca.lci()
        lca.lcia()
        rt, rb = lca.reverse_dict()
        ca = ContributionAnalysis()
        # Monte Carlo
        iterations = 10000
        mc = np.array(ParallelMonteCarlo(fu, method, iterations=iterations
            ).calculate())
        mc.sort()
        # Filter out the outliers
        one_percent = int(0.01 * iterations)
        mc = mc[one_percent:-one_percent]
        mc_data = [(float(x), float(y)) for x, y in zip(*np.histogram(
            mc, bins=max(100, min(20, int(math.sqrt(iterations))))))]
        context.update({
            "mc_median": float(np.median(mc)),
            "mc_mean": float(np.average(mc)),
            "mc_lower": float(mc[int(0.025 * iterations)]),
            "mc_upper": float(mc[int(0.975 * iterations)]),
            "mc_data": JsonWrapper.dumps(mc_data),
            "herfindahl": ca.herfindahl_index(
                lca.characterized_inventory.data, lca.score),
            "concentration_ratio": ca.concentration_ratio(
                lca.characterized_inventory.data, lca.score),
            "hinton_data": JsonWrapper.dumps(ca.hinton_matrix(lca)),
            "treemap_data": JsonWrapper.dumps(ca.d3_treemap(
                lca.characterized_inventory.data, rb, rt)),
            "ia_score": float(lca.score),
            "ia_unit": methods[method]["unit"],
            "ia_method": ": ".join(method),
            "fu": [(ca.get_name(k), "%.2g" % v, ca.db_names[k[0]][k][
                "unit"]) for k, v in fu.iteritems()],
            })
        return render_template("lca.html", **context)


#############
### Tests ###
#############


@app.route('/progress')
def progress_test():
    job_id = get_job_id()
    status_id = get_job_id()
    set_job_status(job_id, {"name": "progress-test", "status": status_id})
    set_job_status(status_id, {"status": "Starting..."})
    return render_template("progress.html", **{"job": job_id,
        'status': status_id})


@app.route('/hist')
def hist_test():
    job_id = get_job_id()
    status_id = get_job_id()
    set_job_status(job_id, {"name": "hist-test", "status": status_id})
    set_job_status(status_id, {"status": "Starting..."})
    return render_template("hist.html", **{"job": job_id, 'status': status_id})

#########################
### Database explorer ###
#########################


def filter_sort_process_database(data, filter=None, order=None):
    if order:
        data = list(itertools.chain(
            *[[(k, v) for k, v in data.iteritems() if v["name"] == x
            ] for x in order]))
    else:
        data = data.iteritems()
    pass


@app.route("/database/<name>")
def database_explorer(name):
    if name not in databases:
        return abort(404)
    db = Database(name)
    data = db.load()
    if request.args.get("q", None):
        names = [x["name"] for x in data.values()]
        names = process.extract(request.args.get("q"), names, limit=20)
        data = filter_sort_process_database(data, filter=names, order=names)
    else:
        data = filter_sort_process_database(data)
    return render_template("database.html",
        name=name, data=JsonWrapper.dumps(data))


def short_name(name):
    return " ".join(name.split(" ")[:3])[:25]


@app.route("/database/tree/<name>/<code>")
@app.route("/database/tree/<name>/<code>/<direction>")
def database_tree(name, code, direction="backwards"):
    def format_d(d):
        return [{"name": short_name(data[k]["name"]),
            "children": format_d(v) if isinstance(v, dict) \
                else [{"name": short_name(data[x]["name"])} for x in v]
            } for k, v in d.iteritems()]

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
    import pprint
    pprint.pprint(formatted)
    return render_template("database_tree.html",
        f=formatted,
        activity=data[(name, code)]["name"],
        direction=direction.title())

#######################
### Method explorer ###
#######################


@app.route("/method-json/<name1>/<name2>/<name3>")
def method_json(name1, name2, name3):
    name = (name1, name2, name3)
    print name, name in methods
    if name not in methods:
        abort(404)
    biosphere = Database("biosphere").load()
    print "Biosphere loaded", len(biosphere)
    cfs = [{"n": biosphere[x[0]]["name"],
        "c": str(biosphere[x[0]]["categories"]),
        "a": x[1]
        } for x in Method(name).load().iteritems()]
    cfs.sort()
    return json_response(cfs)


@app.route("/method/<name1>")
@app.route("/method/<name1>/<name2>")
@app.route("/method/<name1>/<name2>/<name3>")
def method_explorer(name1, name2=None, name3=None):
    return


# use werkzeug.utils.secure_filename to check uploaded file names
# http://werkzeug.pocoo.org/docs/utils/

# to send static files not from 'static': send_from_directory
# http://flask.pocoo.org/docs/api/#flask.send_from_directory
# http://stackoverflow.com/questions/9513072/more-than-one-static-path-in-local-flask-instance
