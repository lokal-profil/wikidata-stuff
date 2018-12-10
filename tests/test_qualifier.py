#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Tests for WikidataStuff Qualifier."""
from __future__ import unicode_literals
import unittest

from wikidatastuff.qualifier import Qualifier


class TestQualifier(unittest.TestCase):

    """Test Qualifier."""

    def test_qualifier_init(self):
        q_int = Qualifier(123, 'foo')
        q_no_p = Qualifier('123', 'foo')
        q_with_p = Qualifier('P123', 'foo')
        self.assertEqual(q_int, q_no_p)
        self.assertEqual(q_with_p, q_no_p)

    def test_qualifier_hash(self):
        q_1 = Qualifier('P123', 'foo')
        q_2 = Qualifier('P124', 'foo')
        q_3 = Qualifier('P123', 'bar')
        q_same = Qualifier('P123', 'foo')
        self.assertEqual(q_1, q_same)
        self.assertNotEqual(q_1, q_2)
        self.assertNotEqual(q_1, q_3)
        self.assertNotEqual(q_2, q_3)

    def test_qualifier_equality(self):
        q = Qualifier('P123', 'foo')
        q_same = Qualifier('P123', 'foo')
        q_different = Qualifier('P123', 'bar')
        self.assertTrue(q == q_same)
        self.assertFalse(q != q_same)
        self.assertTrue(q == q)
        self.assertFalse(q != q)
        self.assertFalse(q == q_different)
        self.assertTrue(q != q_different)

        # Comparison with other classes always gives false, weird but expected
        self.assertFalse(q == 'foo')
        self.assertFalse(q != 'foo')

    def test_qualifier_repr(self):
        q = Qualifier('P123', 'foo')
        self.assertEqual(
            repr(q),
            'WD.Qualifier(P123, foo)')
