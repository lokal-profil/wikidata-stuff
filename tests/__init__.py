# -*- coding: utf-8  -*-
"""Unit tests shim needed for py27 compatibilityfor converters."""
import unittest
import sys

PYTHON_VERSION = sys.version_info[:3]
if (PYTHON_VERSION[0] == 2):
    unittest.TestCase.assertCountEqual = unittest.TestCase.assertItemsEqual
