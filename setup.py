from setuptools import setup

setup(
    name='bw2ui',
    version="0.18.2",
    packages=["bw2ui", "bw2ui.web", "bw2ui.bin"],
    package_data={'bw2ui.web': [
        "static/blueprint/*.css",
        "static/blueprint/plugins/buttons/*.css",
        "static/blueprint/plugins/fancy-type/*.css",
        "static/jqueryFileTree/*.css",
        "static/jqueryFileTree/*.js",
        "static/jqueryFileTree/images/*.png",
        "static/jqueryFileTree/images/*.gif",
        "static/d3-tip/*.js",
        "static/d3-tip/*.css",
        "static/jit/*.js",
        "static/backgrid/*.js",
        "static/backgrid/*.css",
        "static/jstree/*.js",
        "static/jstree/*.css",
        "static/jstree/*.gif",
        "static/jstree/*.png",
        "static/jsoneditor/*.css",
        "static/jsoneditor/*.js",
        "static/jsoneditor/*.png",
        "static/img/*.png",
        "static/img/*.ico",
        "static/img/*.jpg",
        "static/js/*.js",
        "static/css/*.css",
        "static/dynamic/dummy",
        "templates/*.html",
    ]},
    author="Chris Mutel",
    author_email="cmutel@gmail.com",
    license=open('LICENSE.txt').read(),
    install_requires=[
        "brightway2>=2.0.1",
        "docopt",
        "eight",
        "flask",
        "jinja2",
        "stats_arrays",
        "tabulate",
    ],
    entry_points = {
        'console_scripts': [
            'bw2-web        = bw2ui.bin.bw2_web:main',
            'bw2-browser    = bw2ui.bin.bw2_browser:main'
        ]
    },
    url="https://bitbucket.org/cmutel/brightway2-ui",
    long_description=open('README.rst').read(),
    description='Web and command line user interface, part of the Brightway2 LCA framework',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2 :: Only',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Scientific/Engineering :: Visualization',
    ],
)
