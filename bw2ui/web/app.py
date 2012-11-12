# -*- coding: utf-8 -*
from brightway2 import config, databases, methods, Database, Method
from flask import Flask, url_for, render_template

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
