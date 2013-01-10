from setuptools import setup

setup(
  name='bw2ui',
  version="0.4.4",
  packages=["bw2ui", "bw2ui.web"],
  package_data={'bw2ui.web': [
    "static/blueprint/*.css",
    "static/blueprint/plugins/buttons/*.css",
    "static/blueprint/plugins/fancy-type/*.css",
    "static/jqueryFileTree/*.css",
    "static/jqueryFileTree/*.js",
    "static/jqueryFileTree/images/*.png",
    "static/jqueryFileTree/images/*.gif",
    "static/img/*.png",
    "static/img/*.ico",
    "static/img/*.jpg",
    "static/js/*.js",
    "static/css/*.css",
    "templates/*.html",
    ]},
  author="Chris Mutel",
  author_email="cmutel@gmail.com",
  license=open('LICENSE.txt').read(),
  install_requires=["brightway2", "docopt", "flask", "requests", "bw-stats-toolkit", \
    "fuzzywuzzy"],
  scripts=["bw2ui/bin/bw2-web.py", "bw2ui/bin/bw2-controller.py"],
  url="https://bitbucket.org/cmutel/brightway2-ui",
  long_description=open('README.txt').read(),
)
