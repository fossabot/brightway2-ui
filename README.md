# Brightway2-UI

[![PyPI](https://img.shields.io/pypi/v/bw25ui.svg)][pypi status]
[![Status](https://img.shields.io/pypi/status/bw25ui.svg)][pypi status]
[![Python Version](https://img.shields.io/pypi/pyversions/bw25ui)][pypi status]
[![License](https://img.shields.io/pypi/l/bw25ui)][license]

[![Read the documentation at https://brightway2-ui.readthedocs.io/](https://img.shields.io/readthedocs/brightway2-ui/latest.svg?label=Read%20the%20Docs)][read the docs]
[![Codecov](https://codecov.io/gh/brightway-lca/brightway2-ui/branch/main/graph/badge.svg)][codecov]

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)][pre-commit]
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)][black]

[pypi status]: https://pypi.org/project/bw25ui/
[read the docs]: https://brightway2-ui.readthedocs.io/
[codecov]: https://app.codecov.io/gh/brightway-lca/brightway2-ui
[pre-commit]: https://github.com/pre-commit/pre-commit
[black]: https://github.com/psf/black

This is now the official repo for  Brightway2-UI:

> a web and command line user interface, part of the **Brightway2 LCA framework** <https://brightway.dev>.

The _original_ source code was hosted on Bitbucket: <https://bitbucket.org/tomas_navarrete/brightway2-ui>.

## Compatibility with Brightway2X

This repository is used to produce 2 packages: one compatible with brightway25 (`bw25ui`), and one compatible with brightway2 (`bw2ui`).

## Installation

Both, `conda` / `mamba` and wheels from [pypi.org](https://pypi.org) are available.
The package names are different for Brightway25 and Brightway2, but the main executable script is still the same.

> [!NOTE]
> The requirements here are abstract, but they are different for `brightway25` and `brightway2`.
> For brightway25, bw2calc must be `>= 2.0.dev10` and bw2analyzer `>= 0.11`
> for brightway2 bw2calc must be `< 2` and bw2analyzer `>=0.10`

### Brightway25

To install a `conda` / `mamba` package compatible with brightway25:

```commandline
mamba install -c tomas_navarrete bw25ui
```

There is also a pip wheel that you can install with:

```commandline
pip install bw25ui
```

### Brightway2

To install a package compatible with brightway2:

```commandline
mamba install -c tomas_navarrete bw2ui
```

There is also a pip wheel that you can install with:

```commandline
pip install bw2ui
```

## Roadmap

+ As long as retro-compatibility is possible between Brightway25 and Brightway2, the code base will remain identical.
+ Packages will be published with the same version tags, but different names.
+ New features will be primarily implemented to work with Brightway25, and if they are compatible with Brightway2 they will be part of the same code base.
+ When the implementation of new features in a single code base for Brightway2 and Brightway25 becomes imposible, a new branch called `legacy` will be created to track the code compatible with Brightway2. The same will be done in the long term once Brightway3 is released.

### Short term

The current code base is identical for both packages (`bw25ui` and `bw2ui`).
The current main branch will be kept as the branch for development, with identical code bases for both packages _until_ brightway25 public API breaks the compatibility.

### Mid term

Once Brightway3 starts to exist, the main branch will be dedicated to it, with a `bw3ui` package.


## Contributing

Contributions are very welcome.
To learn more, see the [Contributor Guide][Contributor Guide].

## License

Distributed under the terms of the [BSD-3 license][License],
_bw2ui_ is free and open source software.

## Issues

If you encounter any problems,
please [file an issue][Issue Tracker] along with a detailed description.


<!-- github-only -->

[command-line reference]: https://brightway2-ui.readthedocs.io/en/latest/usage.html
[License]: https://github.com/brightway-lca/brightway2-ui/blob/main/LICENSE
[Contributor Guide]: https://github.com/brightway-lca/brightway2-ui/blob/main/CONTRIBUTING.md
[Issue Tracker]: https://github.com/brightway-lca/brightway2-ui/issues


## Building the Documentation

You can build the documentation locally by installing the documentation Conda environment:

```bash
conda env create -f docs/environment.yml
```

activating the environment

```bash
conda activate sphinx_brightway2-ui
```

and [running the build command](https://www.sphinx-doc.org/en/master/man/sphinx-build.html#sphinx-build):

```bash
sphinx-build docs _build/html --builder=html --jobs=auto --write-all; open _build/html/index.html
```

and [running the build command](https://www.sphinx-doc.org/en/master/man/sphinx-build.html#sphinx-build):

```bash
sphinx-build docs _build/html --builder=html --jobs=auto --write-all; open _build/html/index.html
```
