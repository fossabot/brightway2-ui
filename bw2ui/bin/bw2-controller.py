#!/usr/bin/env python
# encoding: utf-8
"""Brightway2 command line controller.

Usage:
  bw2-controller.py list (databases|methods)
  bw2-controller.py details <name>
  bw2-controller.py copy <name> <newname>
  bw2-controller.py backup <name>
  bw2-controller.py validate <name>
  bw2-controller.py versions <name>
  bw2-controller.py revert <name> <revision>
  bw2-controller.py remove <name>
  bw2-controller.py import <path> <name>
  bw2-controller.py export <name> [--include-dependencies]
  bw2-controller.py setup [--data-dir=<datadir>]
  bw2-controller.py upload_logs [COMMENT]
  bw2-controller.py color (on|off)

Options:
  -h --help     Show this screen.
  --version     Show version.

"""
from docopt import docopt
from bw2ui import Controller, terminal_format


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Brightway2 CLI 1.0')
    terminal_format(Controller().dispatch(**arguments))
