#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Backwards compatibility shim."""
from __future__ import unicode_literals

import wikidataStuff.wikidata_string_search
import wikidataStuff.deprecator

wikidataStuff.deprecator.deprecate_single_class(
    __name__, wikidataStuff.wikidata_string_search, 'WikidataStringSearch')
