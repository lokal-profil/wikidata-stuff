#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Backwards compatibility shim."""
from __future__ import unicode_literals

import wikidatastuff.wikidata_stuff
import wikidataStuff.deprecator

wikidataStuff.deprecator.deprecate_single_class(
    __name__, wikidatastuff.wikidata_stuff, 'WikidataStuff')

wikidataStuff.deprecator.deprecate_all_functions(
    __name__, wikidatastuff.wikidata_stuff)
