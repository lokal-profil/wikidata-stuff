wikidata-stuff
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

###KulturNav/
* kulturnavBot.py: A framework for building bots to adding and/or
sourcing statements made available through [KulturNav](http://kulturnav.org/).
Also includes some more general pywikibot methods for Wikidata.
  * kulturnavBotArkDes: A bot for adding and/or sourcing statements about
architects based on data curated by Swedish Centre for Architecture and
Design ([ArkDes](http://www.arkdes.se/)) made available through KulturNav.
  * kulturnavBotSMM: A bot for adding and/or sourcing statements about
maritime objects based on data curated by the National Maritime Museums
([SMM](http://www.maritima.se/)) made available through KulturNav.
  * kulturnavBotNatMus: A bot for adding and/or sourcing statements about
artists based on data curated by the Nationalmuseum Sweden
([NatMus](http://www.nationalmuseum.se/)) made available through KulturNav.
* synkedKulturnav.py: A small script for generating statistics on
KulturNav-Wikidata connections.

## Usage example:
For usage examples see [lokal-profil/wikidata_batches](https://github.com/lokal-profil/wikidata_batches).

## Running as a different user:

To run as a different user to your standard pywikibot simply place a
modified `user-config.py`-file in the top directory.

To use a different user for a particular batchupload place the `user-config.py`
in the subdirectory and run the script with `-dir:<sub-driectory>`.
Remember to set `password_file = "<sub-driectory>/secretPasswords"` in the
`user-config`.
