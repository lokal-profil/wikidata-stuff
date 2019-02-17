#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author: Lokal_Profil
# License: MIT
#
"""Temporary helper functions to aid in mass deprecation."""
from __future__ import unicode_literals

import inspect

from pywikibot.tools import ModuleDeprecationWrapper


def deprecate_single_class(wrapper_name, module, class_name):
    """Deprecate a single class of a module."""
    wrapper = ModuleDeprecationWrapper(wrapper_name)
    wrapper._add_deprecated_attr(
        class_name,
        replacement_name='{}.{}'.format(module.__name__, class_name),
        since='0.4'
    )


def deprecate_all_functions(wrapper_name, module):
    """Deprecate all functions in a module."""
    wrapper = ModuleDeprecationWrapper(wrapper_name)
    deprecated_functions = [
        member[0]
        for member in inspect.getmembers(module, inspect.isfunction)]
    for func_name in deprecated_functions:
        wrapper._add_deprecated_attr(
            func_name,
            replacement_name='{}.{}'.format(module.__name__, func_name),
            since='0.4'
        )
