from distutils.core import setup

setup(
  name='bw2ui',
  version="0.2",
  packages=["bw2ui", "bw2ui.web"],
  package_data={'bw2ui': ["web/static/*/*.*", "web/templates/*.*", "web/templates/*/*.*"]},
  author="Chris Mutel",
  author_email="cmutel@gmail.com",
  license=open('LICENSE.txt').read(),
  requires=["brightway2", "docopt", "flask"],
  scripts=["bw2ui/bin/bw2-web.py", "bw2ui/bin/bw2-controller.py"],
  url="https://bitbucket.org/cmutel/brightway2-ui",
  long_description=open('README.txt').read(),
)
