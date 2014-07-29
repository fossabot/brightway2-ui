#!/usr/bin/env python
# encoding: utf-8
"""Brightway2 command line controller.

Usage:
  bw2-controller list (databases|methods)
  bw2-controller details <name>
  bw2-controller copy <name> <newname>
  bw2-controller backup <name>
  bw2-controller validate <name>
  bw2-controller versions <name>
  bw2-controller revert <name> <revision>
  bw2-controller remove <name>
  bw2-controller export <name> [--include-dependencies]
  bw2-controller setup [--data-dir=<datadir>]
  bw2-controller upload_logs [COMMENT]
  bw2-controller color (on|off)

Options:
  -h --help     Show this screen.
  --version     Show version.

"""
from docopt import docopt
from bw2ui import Controller, terminal_format

def main():
    arguments = docopt(__doc__, version='Brightway2 CLI 1.0')
    terminal_format(Controller().dispatch(**arguments))


if __name__ == '__main__':
    main()
