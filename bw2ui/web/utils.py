# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from brightway2 import projects, JsonWrapper
from flask import Response
import os
import uuid

jobs_dir = projects.request_directory("jobs")


def set_job_status(job, status):
    JsonWrapper.dump(status, os.path.join(jobs_dir, "%s.json" % job))


def get_job(job):
    return JsonWrapper.load(os.path.join(jobs_dir, "%s.json" % job))


def get_job_id():
    return uuid.uuid4().hex


def json_response(data):
    return Response(JsonWrapper.dumps(data), mimetype='application/json')

def get_dynamic_media_folder():
    return os.path.join(os.path.dirname(__file__), u"static", u"dynamic")
