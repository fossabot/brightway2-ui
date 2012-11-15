#!/usr/bin/env python
# encoding: utf-8
"""Brightway2 web user interface.

Usage:
  bw2-web.py [--port=<port>] [--nobrowser] [--debug|--insecure]
  bw2-web.py -h | --help
  bw2-web.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --nobrowser   Don't automatically open a browser tab.
  --debug       Use Werkzeug debug mode (not recommended).
  --insecure    Allow outside connections (insecure!). Not with --debug.

"""
from bw2ui.web import bw2webapp
from docopt import docopt
import random
import threading
import webbrowser


if __name__ == "__main__":
    args = docopt(__doc__, version='Brightway2 Web UI 0.1')

    if args["--port"]:
        port = int(args["--port"])
    else:
        port = 5000 + random.randint(0, 999)
    url = "http://127.0.0.1:{}".format(port)

    if not args["--nobrowser"]:
        threading.Timer(1., lambda: webbrowser.open_new_tab(url)).start()

    kwargs = {
        "port": port,
        "debug": args["--debug"]
    }
    if args["--insecure"]:
        kwargs["host"] = '0.0.0.0'

    bw2webapp.run(**kwargs)
