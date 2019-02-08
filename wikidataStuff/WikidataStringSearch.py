#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Backwards compatibility shim."""
from __future__ import unicode_literals

import wikidatastuff.wikidata_string_search
import wikidataStuff.deprecator

wikidataStuff.deprecator.deprecate_single_class(
    __name__, wikidatastuff.wikidata_string_search, 'WikidataStringSearch')
