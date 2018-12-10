#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Backwards compatibility shim."""
from __future__ import unicode_literals

import wikidatastuff.wdq_to_wdqs
import wikidataStuff.deprecator

wikidataStuff.deprecator.deprecate_all_functions(
    __name__, wikidatastuff.wdq_to_wdqs)
