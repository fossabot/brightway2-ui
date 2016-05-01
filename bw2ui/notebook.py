# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

import jinja2
import os
import random
import string


def random_id(size=20):
    return "".join(random.sample(string.letters + string.digits, size))


def get_javascript(filename):
    directory = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "web",
        "static",
        "js"
    )
    return open(os.path.join(directory, filename)).read()


def format_template(template, context):
    template = jinja2.Template(template)
    return template.render(context)


FD_TEMPLATE = r"""
<button id="{{ button_selector }}">Individual weights</button>
<div id="{{ svg_selector }}"></div>

<script type="text/javascript">
    require.config({paths: {d3: "http://d3js.org/d3.v3.min"}});
    require(["d3"], function (d3) {
        color_scale = d3.scale.category20()
        {{ fd_graph_js }}
        force_directed_graph({{ data }}, color_scale, {{ width }}, {{ height }}, {{ min_size }} , {{ max_size }}, "#{{ svg_selector }}", "#{{ button_selector }}")
        });
"""


def force_directed(data, width=800, height=600, min_size=6, max_size=40):
    context = {
        'data': data,
        'width': width,
        'height': height,
        'min_size': min_size,
        'max_size': max_size,
        'fd_graph_js': get_javascript("force-directed.js"),
        'svg_selector': random_id(),
        'button_selector': random_id()
    }
    return format_template(FD_TEMPLATE, context)
