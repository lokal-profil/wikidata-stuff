#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Backwards compatibility shim."""
from __future__ import unicode_literals

import wikidataStuff.wdqs_lookup
import wikidataStuff.deprecator

wikidataStuff.deprecator.deprecate_all_functions(
    __name__, wikidataStuff.wdqs_lookup)
