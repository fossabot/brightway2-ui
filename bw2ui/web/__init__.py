from flask import Flask

# Hardcoding to remove import errors
# See http://flask.pocoo.org/docs/api/#application-object
bw2webapp = Flask("bw2ui.web")

from . import web_app
