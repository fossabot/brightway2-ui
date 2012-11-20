# -*- coding: utf-8 -*-
import base64
from brightway2 import config, databases, methods, Database, Method, \
    JsonWrapper
from bw2analyzer import ContributionAnalysis
from bw2calc import LCA
from flask import Flask, url_for, render_template, request, redirect, abort
import json
import os

app = Flask(__name__)


@app.errorhandler(404)
def page_not_found(e):
    # Log error?
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    # Log error?
    return render_template('500.html'), 500


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


@app.route('/error')
def error_t():
    abort(404)


@app.route('/calculate/lca')
@app.route('/calculate/lca/<process>/<method>')
def lca(process=None, method=None):
    context = {}
    if process:
        method = eval(base64.urlsafe_b64decode(str(method)), None, None)
        process = eval(base64.urlsafe_b64decode(str(process)), None, None)
        lca = LCA(process, method)
        lca.lci()
        lca.lcia()
        rt, rb = lca.reverse_dict()
        ca = ContributionAnalysis()
        context["treemap_data"] = json.dumps(ca.d3_treemap(
            lca.characterized_inventory.data, rb, rt))
        context["ia_score"] = "%.2g" % lca.score
        context["ia_unit"] = methods[method]["unit"]
        context["ia_method"] = ": ".join(method)
        context["fu"] = [(ca.get_name(k), "%.2g" % v, ca.db_names[k[0]][k][
            "unit"]) for k, v in process.iteritems()]
        return render_template("lca.html", **context)
    else:
        return "No parameters"

import uuid


def get_job_id():
    return uuid.uuid4().hex


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

jobs_dir = config.request_dir("jobs")


def set_job_status(job, status):
    filepath = os.path.join(jobs_dir, "%s.json" % job)
    JsonWrapper.dump(status, filepath)

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
