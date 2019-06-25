# Changelog

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
