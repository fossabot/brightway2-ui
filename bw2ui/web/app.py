# -*- coding: utf-8 -*-
from brightway2 import config, databases, methods, Database, Method, \
    JsonWrapper
from bw2analyzer import ContributionAnalysis, DatabaseExplorer
from bw2calc import LCA, ParallelMonteCarlo
from flask import Flask, url_for, render_template, request, redirect, abort
from fuzzywuzzy import process
from jobs import JobDispatch, InvalidJob
from utils import get_job_id, get_job, set_job_status, json_response
import itertools
import numpy as np

app = Flask(__name__)


@app.errorhandler(404)
def page_not_found(e):
    # Log error?
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    # Log error?
    return render_template('500.html'), 500


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


@app.route('/')
def index():
    context = {
        'databases': databases,
        'methods': methods,
        'config': config
        }
    if config.is_temp_dir:
        context["redirect"] = url_for(start_bw)
    return render_template("index.html", **context)


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
        }} for key, value in data.iteritems() if value["num_cfs"]])


def get_tuple_index(t, i):
    try:
        return t[i]
    except IndexError:
        return "---"


@app.route('/select')
def process_selector():
    return render_template("select.html",
        db_names=[x for x in databases.list if x != "biosphere"],
        lcia_methods=[{
            "l1": get_tuple_index(key, 0),
            "l2": get_tuple_index(key, 1),
            "l3": get_tuple_index(key, 2),
            "u": value["unit"],
            "n": value["num_cfs"],
            "k": key
        } for key, value in methods.data.iteritems()])


@app.route('/hinton')
def hinton():
    return render_template("hinton.html")


@app.route('/lca', methods=["GET", "POST"])
def lca():
    if request.method == "GET":
        return render_template("lca-select.html")
    else:
        fu = eval(request.form["activity"])
        method = eval(request.form["method"])
        context = {}
        lca = LCA(fu, method)
        lca.lci()
        lca.lcia()
        rt, rb = lca.reverse_dict()
        ca = ContributionAnalysis()
        # Monte Carlo
        mc = np.array(ParallelMonteCarlo(fu, method, iterations=1000, chunk_size=150).calculate())
        mc.sort()
        mc_data = [(float(x), float(y)) for x, y in zip(*np.histogram(mc, bins=70))]
        context.update({
            "mc_median": float(np.median(mc)),
            "mc_mean": float(np.average(mc)),
            "mc_lower": float(mc[125]),
            "mc_upper": float(mc[-125]),
            "mc_data": JsonWrapper.dumps(mc_data),
            "treemap_data": JsonWrapper.dumps(ca.d3_treemap(
                lca.characterized_inventory.data, rb, rt)),
            "ia_score": float(lca.score),
            "ia_unit": methods[method]["unit"],
            "ia_method": ": ".join(method),
            "fu": [(ca.get_name(k), "%.2g" % v, ca.db_names[k[0]][k][
                "unit"]) for k, v in fu.iteritems()],
            })
        return render_template("lca.html", **context)


@app.route('/progress')
def progress_test():
    job_id = get_job_id()
    status_id = get_job_id()
    set_job_status(job_id, {"name": "progress-test", "status": status_id})
    set_job_status(status_id, {"status": "Starting..."})
    return render_template("progress.html", **{"job": job_id, 'status': status_id})


@app.route('/hist')
def hist_test():
    job_id = get_job_id()
    status_id = get_job_id()
    set_job_status(job_id, {"name": "hist-test", "status": status_id})
    set_job_status(status_id, {"status": "Starting..."})
    return render_template("hist.html", **{"job": job_id, 'status': status_id})


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


@app.route('/start', methods=["GET", "POST"])
def start_bw():
    """Start Brightway"""
    job_id = get_job_id()
    if request.method == "GET":
        pass
    elif not request.form["confirm"] == "false":
        return redirect(url_for(index) + "?temp_dir_ok=True")
    # Starting Brightway
    # If POST[action] = "get_biosphere":
    set_job_status(job_id, {"action": "biosphere-import", "finished": False})
    # Download file to disk
    DatabaseImporter().importer(biosphere)
    set_job_status(job_id, {"action": "biosphere-import", "finished": True})

    # Step two
    # Import IA methods
    # Can also be from dropbox

    # Step three
    # Import Ecoinvent or other LCI database

    # Step four
    # There is no step four!
    # Actually, there is: go to the normal homepage

# Normal homepage:
# Think of what should be here
# At a minimum, a table of databases
# and IA methods
# A quick entry to LCA (define function units)

# use werkzeug.utils.secure_filename to check uploaded file names
# http://werkzeug.pocoo.org/docs/utils/

# to send static files not from 'static': send_from_directory
# http://flask.pocoo.org/docs/api/#flask.send_from_directory
# http://stackoverflow.com/questions/9513072/more-than-one-static-path-in-local-flask-instance
