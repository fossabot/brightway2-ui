Brightway2-UI
=============

This is now the official repo for  Brightway2-UI:

> a web and command line user interface, part of the **Brightway2 LCA framework** <https://brightway.dev>. 

The _original_ source code was hosted on Bitbucket: <https://bitbucket.org/tomas_navarrete/brightway2-ui>.

Compatibility with Brightway2X
==============================

This repository is used to produce 2 packages: one compatible with brightway25 (`bw25ui`), and one compatible with brightway2 (`bw2ui`).

Installation
============

Brightway25
-----------

To install a package compatible with brightway25:

```bash
conda install -c tomas_navarrete bw25ui
```

Brightway2
----------

To install a package compatible with brightway2:

```bash
conda install -c tomas_navarrete bw2ui
```

Roadmap
=======

+ As long as retro-compatibility is possible between Brightway25 and Brightway2, the code base will remain identical.
+ Packages will be published with the same version tags, but different names.
+ New features will be primarily implemented to work with Brightway25, and if they are compatible with Brightway2 they will be part of the same code base.
+ When the implementation of new features in a single code base for Brightway2 and Brightway25 becomes imposible, a new branch called `legacy` will be created to track the code compatible with Brightway2. The same will be done in the long term once Brightway3 is released.

Short term
-----------

The current code base is identical for both packages (`bw25ui` and `bw2ui`).
The current main branch will be kept as the branch for development, with identical code bases for both packages _until_ brightway25 public API breaks the compatibility.

Mid term
--------

Once Brightway3 starts to exist, the main branch will be dedicated to it, with a `bw3ui` package.


