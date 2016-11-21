wikidata-stuff  [![Build Status](https://travis-ci.org/lokal-profil/wikidata-stuff.svg?branch=master)](https://travis-ci.org/lokal-profil/wikidata-stuff)
==============

Random scripts used for Wikidata. These require [pywikibot](https://github.com/wikimedia/pywikibot-core)

* WikidataStuff.py: A set of generally useful functions for interacting
with Wikidata using pywikibot.
* WikidataStringSearch.py: A database hookup (to be run from labs) for
doing text string searches (SQL LIKE style) in labels, aliases and
descriptions of items.
* wdqsLookup.py: A module for doing [WDQS](http://query.wikidata.org/) look-ups
and for converting (some) [WDQ](http://wdq.wmflabs.org/) queries to WDQS
queries.

## Usage example:
For usage examples see [lokal-profil/wikidata_batches](https://github.com/lokal-profil/wikidata_batches).

## Running as a different user:

To run as a different user to your standard pywikibot simply place a
modified `user-config.py`-file in the top directory.

To use a different user for a particular batchupload place the `user-config.py`
in the subdirectory and run the script with `-dir:<sub-driectory>`.
Remember to set `password_file = "<sub-driectory>/secretPasswords"` in the
`user-config`.
