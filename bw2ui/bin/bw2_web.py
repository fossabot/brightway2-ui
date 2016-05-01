#!/usr/bin/env python
# encoding: utf-8
"""Brightway2 web user interface.

Usage:
  bw2-web [--port=<port>] [--nobrowser] [--debug|--insecure]
  bw2-web -h | --help
  bw2-web --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --nobrowser   Don't automatically open a browser tab.
  --debug       Use Werkzeug debug mode (only for development).
  --insecure    Allow outside connections (insecure!). Not with --debug.

"""
from __future__ import print_function, unicode_literals
from eight import *

from bw2data import projects
from bw2ui.web import bw2webapp
from docopt import docopt
# from werkzeug.serving import run_simple
import logging
import os
import threading
import webbrowser


def main():
    args = docopt(__doc__, version='Brightway2 Web UI 1.0')
    port = int(args.get("--port", False) or 5000)  # + random.randint(0, 999))
    host = "0.0.0.0" if args.get("--insecure", False) else "localhost"
    debug = args["--debug"]

    if not args["--nobrowser"]:
        url = "http://127.0.0.1:{}".format(port)
        threading.Timer(1., lambda: webbrowser.open_new_tab(url)).start()

    # kwargs = {
    #     "processes": args.get("<processes>", 0) or 3,
    # }

    if not debug:
        handler = logging.handlers.RotatingFileHandler(
            os.path.join(projects.logs_dir, "web-ui-error.log"),
            maxBytes=50000, encoding='utf-8', backupCount=5)
        handler.setLevel(logging.WARNING)
        handler.setFormatter(logging.Formatter('''
Message type:       %(levelname)s
Location:           %(pathname)s:%(lineno)d
Module:             %(module)s
Function:           %(funcName)s
Time:               %(asctime)s
Message:
%(message)s

'''))

        bw2webapp.logger.addHandler(handler)

    bw2webapp.run(host=host, port=port, debug=debug)
    # run_simple disabled because multiple workers cause cache conflicts...
    # run_simple(host, port, bw2webapp, use_evalex=True, **kwargs)


if __name__ == "__main__":
    main()
