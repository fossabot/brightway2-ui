from brightway2 import config, JsonWrapper
from flask import Response
import os
import uuid

jobs_dir = config.request_dir("jobs")


def set_job_status(job, status):
    JsonWrapper.dump(status, os.path.join(jobs_dir, "%s.json" % job))


def get_job(job):
    return JsonWrapper.load(os.path.join(jobs_dir, "%s.json" % job))


def get_job_id():
    return uuid.uuid4().hex


def json_response(data):
    return Response(JsonWrapper.dumps(data), mimetype='application/json')
