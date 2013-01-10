#!/usr/bin/env python
# encoding: utf-8
"""Brightway2 web user interface.

Usage:
  bw2-web.py [--port=<port>] [--processes=<processes>] [--nobrowser] [--debug|--insecure]
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
from bw2ui.utils import clean_jobs_directory
from docopt import docopt
from werkzeug.serving import run_simple
import random
import threading
import webbrowser


if __name__ == "__main__":
    clean_jobs_directory()

    args = docopt(__doc__, version='Brightway2 Web UI 0.1')
    port = int(args.get("--port", False) or 5000)  # + random.randint(0, 999))
    host = "0.0.0.0" if args.get("--insecure", False) else "localhost"

    if not args["--nobrowser"]:
        url = "http://127.0.0.1:{}".format(port)
        threading.Timer(1., lambda: webbrowser.open_new_tab(url)).start()

    kwargs = {
        "processes": args.get("<processes>", 0) or 3,
        "use_debugger": args["--debug"]
    }

    # run_simple(host, port, bw2webapp, use_evalex=True, **kwargs)
    bw2webapp.run(debug=False)
