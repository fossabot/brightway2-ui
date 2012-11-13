# -*- coding: utf-8 -*
from brightway2 import config, databases, methods, Database, Method
from bw2analyzer import ContributionAnalysis
from bw2calc import LCA
from flask import Flask, url_for, render_template
import base64
import json

app = Flask(__name__)


def template_context():
    return {
        'blueprint_screen': url_for('static', filename="blueprint/screen.css"),
        'blueprint_print': url_for('static', filename="blueprint/print.css"),
        'blueprint_ie': url_for('static', filename="blueprint/ie.css"),
    }


@app.route('/')
def index():
    context = template_context()
    print context
    return "Success"
    return render_template("index.html", **context)


@app.route('/calculate/lca')
@app.route('/calculate/lca/<process>/<method>')
def lca(process=None, method=None):
    context = template_context()
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
