#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Tests for WikidataStuff Statement."""
from __future__ import unicode_literals
import unittest

from pywikibot import (
    Error as pwbError,
    Site as Site,
    Claim as Claim
)

from wikidatastuff.statement import Statement
from wikidatastuff.qualifier import Qualifier  # replace with mocks
from wikidatastuff.reference import Reference  # replace with mocks


class TestStatement(unittest.TestCase):

    """Test Statement."""

    def setUp(self):
        wikidata = Site('test', 'wikidata')
        self.q_1 = Qualifier('P123', 'foo')
        self.q_2 = Qualifier('P123', 'bar')
        claim = Claim(wikidata, 'P55')
        claim.setTarget('foo')
        self.ref = Reference(source_test=[claim, ])

    def test_statement_init(self):
        s = Statement('foo')
        self.assertFalse(s.force)
        self.assertFalse(s.special)
        self.assertEqual(s.quals, [])
        self.assertEqual(s.itis, 'foo')
        self.assertEqual(s.ref, None)

    def test_statement_init_none(self):
        self.assertTrue(Statement(None).is_none())
        self.assertFalse(Statement('foo').is_none())

    def test_statement_init_special(self):
        self.assertTrue(
            Statement('somevalue', special=True).special)
        self.assertTrue(
            Statement('novalue', special=True).special)
        with self.assertRaises(pwbError) as cm:
            Statement('foo', special=True)
        self.assertEqual(
            str(cm.exception),
            'You tried to create a special statement with a non-allowed '
            'snakvalue: foo')

    def test_statement_equality(self):
        s = Statement('foo')
        s_same = Statement('foo')
        s_different = Statement('bar')
        self.assertEqual(s, s)
        self.assertEqual(s, s_same)
        self.assertNotEquals(s, s_different)

        # Comparison with other classes always gives false, weird but expected
        self.assertFalse(s == 'foo')
        self.assertFalse(s != 'foo')

    def test_statement_inequality(self):
        s = Statement('novalue')
        s_special = Statement('novalue', special=True)
        s_force = Statement('novalue')
        s_force.force = True

        self.assertNotEquals(s, s_special)
        self.assertNotEquals(s, s_force)
        self.assertNotEquals(s_force, s_special)

    def test_statement_qualifier(self):
        s = Statement('foo')
        s.add_qualifier(self.q_1)
        self.assertEqual(s.quals, [self.q_1])
        self.assertEqual(s._quals, set([self.q_1]))
        self.assertEqual(s, s)

        s.add_qualifier(self.q_2)
        self.assertEqual(s._quals, set([self.q_1, self.q_2]))
        self.assertEqual(s, s)

    def test_statement_none_qualifier(self):
        s = Statement('foo')
        s.add_qualifier(None)
        self.assertEqual(s.quals, [])

        s.add_qualifier(None, force=True)
        s.force = False

    def test_statement_qualifier_chaining(self):
        s = Statement('foo')
        s.add_qualifier(self.q_1).add_qualifier(self.q_2)
        self.assertEqual(s._quals, set([self.q_1, self.q_2]))

    def test_statement_equality_qualifier_order(self):
        s_1 = Statement('foo')
        s_2 = Statement('foo')
        s_3 = Statement('foo')
        s_1.add_qualifier(self.q_1).add_qualifier(self.q_2)
        s_2.add_qualifier(self.q_2).add_qualifier(self.q_1)
        s_3.add_qualifier(self.q_1)
        self.assertEqual(s_1, s_2)
        self.assertNotEquals(s_1, s_3)

    def test_statement_qualifier_duplicates(self):
        s = Statement('foo')
        s.add_qualifier(self.q_1)
        s.add_qualifier(self.q_1)
        self.assertEqual(s.quals, [self.q_1])

    def test_statement_add_reference(self):
        s = Statement('foo')
        s.add_reference(self.ref)
        self.assertEqual(s.ref, self.ref)

    def test_statement_add_chained_reference(self):
        s = Statement('foo').add_reference(self.ref)
        self.assertEqual(s.ref, self.ref)

    def test_statement_add_bad_reference_error(self):
        s = Statement('foo')
        with self.assertRaises(pwbError) as cm:
            s.add_reference('foo')
        self.assertEqual(
            str(cm.exception),
            'add_reference was called with something other '
            'than a Reference object: foo')

    def test_statement_add_second_reference_error(self):
        s = Statement('foo').add_reference(self.ref)
        with self.assertRaises(pwbError) as cm:
            s.add_reference(self.ref)
        self.assertEqual(
            str(cm.exception),
            'add_reference was called when the statement already had '
            'a reference assigned to it.')

    def test_statement_repr(self):
        s = Statement('foo')
        self.assertEqual(
            repr(s),
            'WD.Statement('
            'itis:foo, quals:[], ref:None, special:False, force:False)')
        s.add_qualifier(self.q_1)
        self.assertEqual(
            repr(s),
            'WD.Statement('
            'itis:foo, quals:[WD.Qualifier(P123, foo)], ref:None, '
            'special:False, force:False)')
        s.add_reference(self.ref)
        self.assertEqual(
            repr(s),
            'WD.Statement('
            'itis:foo, quals:[WD.Qualifier(P123, foo)], '
            'ref:WD.Reference(test: [WD.Claim(P55: foo)], no_test: []), '
            'special:False, force:False)')
