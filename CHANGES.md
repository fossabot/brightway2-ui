# ui Changelog

## [unreleased]

### Added

+ up command to display pedigree data on exchanges if available
+ show CFS for full methods or per selected biosphere3 activity
+ add command to output cf lists as tsv, or results of LCIA calculation
+ support numerical activity ids (as used in bw25)


## [0.29.0] - 2022-08-22

### Added

+ Full compatibility with brightway25

## [0.28.0] - 2022-06-13

### Added

+ Feature #11 - search by location (useful for biosphere flows)

## [0.27.0] - 2021-06-17

### Added

+ Fix #10

## [0.26.0] - 2021-04-02

### Added

+ Fix #9

## [0.25.0] - 2020-09-16

### Added

+ The package is architecture independant, but requires conda > 4.3 to be installed
+ Commands to list and search parameters

## [0.24.0] - 2020-01-30

### Added

+ Show formulas for parameterized exchanges

## [0.23.0] - 2019-07-15

### Added

+ Top emissions and Top activities commands

### Changed

## [0.22.0] - 2019-06-26

### Changed

+ Fixed listing of downstream consumers
+ Fixed listing of classifications instead of categories

## [0.21.0] - 2019-06-25

### Added

+ `s -loc {CODE} string` allows to search by location

bw2data (at least up to 3.5) Whoosh search schema treats the location field as text.
Searching for location {CA-CQ} would yield no results, but searching for
location {CA} would bring all CA-xx locations. The s -loc feature will do a full search
and filter afterwards if the provide location contains any of the following
```
specials = [' ', '/', '-', '&']
```

### Changed

+ default search_limit is now 100 results

## [0.20.0] - 2019-04-24

### Added

+ `aa` command lists all activities in an active database

## [0.19.0] - 2019-03-11

### Added

+ `G` command will do an LCIA if an activity and method(s) are selected



0.18.2 (2015-03-08)
===================

Fix `issue #6 <https://bitbucket.org/cmutel/brightway2-ui/issue/6/bw2-controller-typeerror-safe_colorama>`__

0.18.1 (2014-09-03)
===================

Bugfix for database health check template.

0.18 (2014-09-03)
=================

- FEATURE: Add database facet views, e.g. by location or unit.
- Updated jquery and background javascript libraries.

0.17 (2014-08-30)
=================

- FEATURE: Add database health check. Requires ``bw2analyzer`` >= 0.6.
- FEATURE: Add Whoosh-based searching using ``bw2search``.

0.16 (2014-08-26)
=================

- FEATURE: New supply chain visualization in activity browser.

0.15 (2014-07-30)
=================

Updated dependencies.

0.14 (2014-06-14)
=================

- CHANGE: Using `entry_points` instead of `scripts` in setup.py allows scripts that are exectuable in Windows. New names are `bw-web` (instead of `bw2-web.py`), `bw2-controller`, and `bw2-browser`.

0.13 (2014-06-13)
=================

- CHANGE: Change bw2ui.web.app to web_app to avoid naming conflicts
- CHANGE: Remove some assumptions about Database and Method metadata
