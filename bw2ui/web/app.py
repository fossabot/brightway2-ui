# -*- coding: utf-8 -*-
from __future__ import division
from brightway2 import config, databases, methods, Database, Method, \
    JsonWrapper, set_data_dir, bw2setup
from bw2analyzer import DatabaseExplorer, SerializedLCAReport
from bw2calc.speed_test import SpeedTest
from bw2data.io import Ecospold1Importer, EcospoldImpactAssessmentImporter
from flask import Flask, url_for, render_template, request, redirect, abort
from jobs import JobDispatch, InvalidJob
from urllib import unquote as _unquote
from utils import get_job_id, get_job, set_job_status, json_response
import json
import multiprocessing
import os
import urllib2


def get_windows_drive_letters():
    import win32api
    return [x for x in win32api.GetLogicalDriveStrings().split('\000') if x]


def jqfilepicker_unquote(source):
    """
Stupid Javascript (insert joke here...) and jQueryFilePicker
http://stackoverflow.com/questions/300445/how-to-unquote-a-urlencoded-unicode-string-in-python
https://github.com/simogeo/Filemanager/issues/40
    """
    result = _unquote(source)
    if '%u' in result:
        result = result.replace('%u', '\\u').decode('unicode_escape')
    return result

app = Flask(__name__)

###########################
### Basic functionality ###
###########################


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
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

def get_windows_drives():
    if not config._windows:
        return {'windows': False}
    else:
        return {
            'windows': True,
            'drive_letters': get_windows_drive_letters(),
            'current_drive': os.path.splitdrive(os.getcwd())[0]
        }

@app.route('/start/path', methods=["POST"])
def set_path():
    path = urllib2.unquote(request.form["path"])
    dirname = urllib2.unquote(request.form["dirname"])
    set_data_dir(os.path.join(path, dirname))
    return "1"


@app.route('/start/biosphere')
def install_biosphere():
    bw2setup()
    return "1"


@app.route('/start')
def start():
    return render_template(
        "start.html",
        root_path=json.dumps(os.path.abspath("/")),
        **get_windows_drives()
    )

#################
### Importing ###
#################


@app.route("/import/database", methods=["GET", "POST"])
def import_database():
    if request.method == "GET":
        return render_template("import-database.html", **get_windows_drives())
    else:
        path = urllib2.unquote(request.form["path"])
        name = urllib2.unquote(request.form["name"])
        Ecospold1Importer().importer(path, name)
        return "1"


@app.route("/import/method", methods=["GET", "POST"])
def import_method():
    if request.method == "GET":
        return render_template("import-method.html", **get_windows_drives())
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
        "version": value["version"],
        "url": url_for('database_explorer', name=key)
        } for key, value in databases.iteritems()]
    dbs.sort(key=lambda x: x['name'])
    ms = [{
        "name": " - ".join(key),
        "unit": value["unit"],
        "num_cfs": value["num_cfs"],
        "url": url_for("method_explorer", abbreviation=value['abbreviation'])
    } for key, value in methods.iteritems()]
    ms.sort(key = lambda x: x['name'])
    context = {
        'databases': json.dumps(dbs),
        'methods': json.dumps(ms),
        'config': config
        }
    return render_template("index.html", **context)


@app.route('/settings', methods=["GET", "POST"])
def change_settings():
    if request.method == "GET":
        context = {
            "config": config,
            "cpu_count": multiprocessing.cpu_count(),
        }
        return render_template("settings.html", **context)
    else:
        config.p["use_cache"] = bool(request.form.get("use-cache", False))
        config.p["temp_dir_ok"] = bool(request.form.get("use-temp-dir", False))
        config.p["cpu_cores"] = int(request.form["cpu-cores"])
        config.p["iterations"] = int(request.form["iterations"])
        config.p["upload_reports"] = bool(request.form.get(
            "upload-reports", False))
        config.p["report_server_url"] = request.form["report-server"]
        config.save_preferences()
        return redirect(url_for('index'))


@app.route('/speedtest')
def speed_test():
    st = SpeedTest()
    return str(250 * int(40 * st.ratio()))

##############################
### Databases and datasets ###
##############################


@app.route("/database/<name>")
def database_explorer(name):
    try:
        meta = databases[name]
    except KeyError:
        return abort(404)
    data = Database(name).load()
    depends = [{
        'name': obj,
        'url': url_for('database_explorer', name=obj)
    } for obj in sorted(meta['depends'])]
    json_data = [{
        'name': value['name'],
        'categories': ",".join(value.get('categories', [])),
        'location': value.get('location', ''),
        'unit': value.get('unit', ''),
        'url': url_for('activity_dataset', database=name, code=key[1]),
        'num_exchanges': len(value.get('exchanges', [])),
        'key': key
        } for key, value in data.iteritems()]
    json_data.sort(key = lambda x: x['name'])
    return render_template(
        "database.html",
        meta=meta,
        name=name,
        depends=depends,
        data=JsonWrapper.dumps(json_data),
        backup_url = url_for('backup_database', database=name),
        delete_url = url_for('delete_database', database=name),
    )


@app.route("/delete/<database>", methods=["POST"])
def delete_database(database):
    if database not in databases:
        return abort(404)
    del databases[database]
    return ''


@app.route("/backup/<database>", methods=["POST"])
def backup_database(database):
    if database not in databases:
        return abort(404)
    return Database(database).backup()


@app.route("/view/<database>/<code>")
def activity_dataset(database, code):
    if database not in databases:
        return abort(404)
    data = Database(database).load()
    try:
        data = data[(database, code)]
    except KeyError:
        return abort(404)

    rp = [x for x in data['exchanges'] if x['type'] == "production"]
    if len(rp) == 1:
        rp = rp[0]['amount']
    else:
        rp = 0

    def format_ds(key, amount):
        # try:
        ds = Database(key[0]).load()[key]
        # except:
        #     return {}
        return {
            'name': ds['name'],
            'categories': ",".join(ds.get('categories', [])),
            'location': ds.get('location', ''),
            'unit': ds.get('unit', ''),
            'url': url_for('activity_dataset', database=key[0], code=key[1]),
            'amount': amount
            }

    biosphere = [format_ds(x['input'], x['amount']) for x in data['exchanges'] if x['type'] == "biosphere"]
    technosphere = [format_ds(x['input'], x['amount']) for x in data['exchanges'] if x['type'] == "technosphere"]

    return render_template(
        "activity.html",
        data=data,
        ref_prod=rp,
        edit_url=url_for("json_editor", database=database, code=code),
        biosphere=json.dumps(biosphere),
        technosphere=json.dumps(technosphere)
    )

@app.route("/view/<database>/<code>/json")
def json_editor(database, code):
    if database not in databases:
        return abort(404)
    data = Database(database).load()
    try:
        data = data[(database, code)]
    except KeyError:
        return abort(404)
    return render_template("jsoneditor.html", jsondata=json.dumps(data))

###########
### LCA ###
###########


def get_tuple_index(t, i):
    try:
        return t[i]
    except IndexError:
        return "---"


@app.route('/lca', methods=["GET", "POST"])
def lca():
    if request.method == "GET":
        return render_template("select.html",
            db_names=[x for x in databases.list if x != config.biosphere],
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
        iterations = config.p.get("iterations", 10000)
        cpu_count = config.p.get("cpu_cores", None)
        report = SerializedLCAReport(fu, method, iterations, cpu_count)
        report.calculate()
        try:
            report.upload()
        except:
            # No online report no cry
            pass
        report.write()
        return report.uuid


@app.route('/report/<uuid>')
def report(uuid):
    data = open(os.path.join(
        config.dir, "reports", "report.%s.json" % uuid)).read()
    return render_template("report.html", data=data)


###############
### Methods ###
###############


@app.route("/method/<abbreviation>")
def method_explorer(abbreviation):
    method = [key for key, value in methods.iteritems()
        if value['abbreviation'] == abbreviation]
    if not len(method) == 1:
        abort(404)
    method = method[0]
    meta = methods[method]
    json_data = []
    for key, value, geo in Method(method).load():
        flow = Database(key[0]).load()[key]
        json_data.append({
            'name': flow['name'],
            'unit': flow.get('unit', ''),
            'categories': ",".join(flow.get('categories', [])),
            'cf': value['amount'] if isinstance(value, dict) else value,
            'location': geo,
            'url': url_for('activity_dataset', database=key[0], code=key[1])
        })
    json_data.sort(key=lambda x: x['name'])
    return render_template(
        "method.html",
        name=method,
        unit=meta['unit'],
        description=meta['description'],
        data=JsonWrapper.dumps(json_data)
    )

###################
### Development ###
###################


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

# use werkzeug.utils.secure_filename to check uploaded file names
# http://werkzeug.pocoo.org/docs/utils/

# to send static files not from 'static': send_from_directory
# http://flask.pocoo.org/docs/api/#flask.send_from_directory
# http://stackoverflow.com/questions/9513072/more-than-one-static-path-in-local-flask-instance
