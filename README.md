wikidata-stuff  [![Build Status](https://travis-ci.org/lokal-profil/wikidata-stuff.svg?branch=master)](https://travis-ci.org/lokal-profil/wikidata-stuff)
==============

Random scripts used for doing mass imports to Wikidata. The emphasis is on sourcing
Claims whether new or pre-existing. As such any imported statement will follow the
following decision tree (any added statement includes the source):

* The property has not yet been used. Statement is added
* The property is already used and:
   * The value is different. A new statement is added.
   * The value is the same but sources differ. The new source is added to the
     existing claim.
   * The value is the same and (relevant parts of) the source are the same. No
     information is added.

For details on how qualifiers are handled, see `wikidatastuff.wikidata_stuff.WikidataStuff.match_claim()`.

For details on how sources are compared, see `wikidatastuff.reference`.

## Components

* `wikidata_stuff.py`:
  * A set of generally useful functions for interacting with Wikidata using pywikibot.
* `reference.py`: A class representing the source claims.
* `qualifier.py`: A class representing qualifier claims.
* `statement.py`: A class representing a statement (i.e. value, qualifiers and references).
* `wikidata_string_search.py`: A database hookup (to be run from Toolforge) for
doing text string searches (SQL LIKE style) in labels, aliases and
descriptions of items.
* `wdqs_lookup.py`: A module for doing [WDQS](http://query.wikidata.org/) look-ups
and for converting (some) [WDQ](http://wdq.wmflabs.org/) queries to WDQS
queries.
* `preview_item.py`: Allows for the visualisation of a prepared new/updated Wikidata
item candidate. An item candidate consists of a dict of label/aliases (per language
code), a dict of descriptions (per language code), a dict of `Statement`s (per
P-prefixed property-id), an optional `Reference` (used whenever one is not included
in a `Statement`) and the `itemPage` to which the information should be written
(if not a new item). The visualisation takes the form of a wikitext table
([example](https://www.wikidata.org/w/index.php?title=User:AndreCostaWMSE-bot/WFD/preview&oldid=508045617)).

## Usage example:
For usage examples see [lokal-profil/wikidata_batches](https://github.com/lokal-profil/wikidata_batches).

Note that these may be using older versions of the repo.

## Running as a different user:

To run as a different user to your standard pywikibot simply place a
modified `user-config.py`-file in the top directory.

To use a different user for a particular mass import place the `user-config.py`
in the subdirectory and run the script with `-dir:<sub-directory>`.

## Deprecations
Deprecated functions, classes and arguments may be dropped at any major
version change. To display the deprecation warnings run your script using
the pywikibot `-debug` flag (you must be making use of
`pywikibot.handleArgs()`) or add the `-Wd` option to your python call.

## Requirements
* [pywikibot](https://github.com/wikimedia/pywikibot-core)
