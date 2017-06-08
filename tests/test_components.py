#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Tests for WikidataStuff Qualifier, Statement and Reference subclasses."""
from __future__ import unicode_literals
import unittest

from pywikibot import (
    Error as pwbError,
    Site as Site,
    Claim as Claim
)

from wikidataStuff.WikidataStuff import WikidataStuff as WD


class TestQualifier(unittest.TestCase):

    """Test Qualifier."""

    def test_qualifier_init(self):
        q_int = WD.Qualifier(123, 'foo')
        q_no_p = WD.Qualifier('123', 'foo')
        q_with_p = WD.Qualifier('P123', 'foo')
        self.assertEqual(q_int, q_no_p)
        self.assertEqual(q_with_p, q_no_p)

    def test_qualifier_hash(self):
        q_1 = WD.Qualifier('P123', 'foo')
        q_2 = WD.Qualifier('P124', 'foo')
        q_3 = WD.Qualifier('P123', 'bar')
        q_same = WD.Qualifier('P123', 'foo')
        self.assertEqual(q_1, q_same)
        self.assertNotEqual(q_1, q_2)
        self.assertNotEqual(q_1, q_3)
        self.assertNotEqual(q_2, q_3)

    def test_qualifier_equality(self):
        q = WD.Qualifier('P123', 'foo')
        q_same = WD.Qualifier('P123', 'foo')
        q_different = WD.Qualifier('P123', 'bar')
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
        q = WD.Qualifier('P123', 'foo')
        self.assertEqual(
            repr(q),
            'WD.Qualifier(P123, foo)')


class TestStatement(unittest.TestCase):

    """Test Statement."""

    def test_statement_init(self):
        s = WD.Statement('foo')
        self.assertFalse(s.force)
        self.assertFalse(s.special)
        self.assertEquals(s.quals, [])
        self.assertEquals(s.itis, 'foo')

    def test_statement_init_none(self):
        self.assertTrue(WD.Statement(None).isNone())
        self.assertFalse(WD.Statement('foo').isNone())

    def test_statement_init_special(self):
        self.assertTrue(
            WD.Statement('somevalue', special=True).special)
        self.assertTrue(
            WD.Statement('novalue', special=True).special)
        with self.assertRaises(pwbError) as cm:
            WD.Statement('foo', special=True)
        self.assertEqual(
            str(cm.exception),
            'You tried to create a special statement with a non-allowed '
            'snakvalue: foo')

    def test_statement_equality(self):
        s = WD.Statement('foo')
        s_same = WD.Statement('foo')
        s_different = WD.Statement('bar')
        self.assertEquals(s, s)
        self.assertEquals(s, s_same)
        self.assertNotEquals(s, s_different)

        # Comparison with other classes always gives false, weird but expected
        self.assertFalse(s == 'foo')
        self.assertFalse(s != 'foo')

    def test_statement_inequality(self):
        s = WD.Statement('novalue')
        s_special = WD.Statement('novalue', special=True)
        s_force = WD.Statement('novalue')
        s_force.force = True

        self.assertNotEquals(s, s_special)
        self.assertNotEquals(s, s_force)
        self.assertNotEquals(s_force, s_special)

    def test_statement_qualifier(self):
        s = WD.Statement('foo')
        q_1 = WD.Qualifier('P123', 'bar')
        q_2 = WD.Qualifier('P123', 'bar')
        s.addQualifier(q_1)
        self.assertEquals(s.quals, [q_1])
        self.assertEquals(s._quals, set([q_1]))
        self.assertEquals(s, s)

        s.addQualifier(q_2)
        self.assertEquals(s._quals, set([q_1, q_2]))
        self.assertEquals(s, s)

    def test_statement_none_qualifier(self):
        s = WD.Statement('foo')
        s.addQualifier(None)
        self.assertEquals(s.quals, [])

        s.addQualifier(None, force=True)
        s.force = False

    def test_statement_qualifier_chaining(self):
        s = WD.Statement('foo')
        q_1 = WD.Qualifier('P123', 'bar')
        q_2 = WD.Qualifier('P123', 'bar')
        s.addQualifier(q_1).addQualifier(q_2)
        self.assertEquals(s._quals, set([q_1, q_2]))

    def test_statement_equality_qualifier_order(self):
        s_1 = WD.Statement('foo')
        s_2 = WD.Statement('foo')
        s_3 = WD.Statement('foo')
        q_1 = WD.Qualifier('P123', 'foo')
        q_2 = WD.Qualifier('P123', 'bar')
        s_1.addQualifier(q_1).addQualifier(q_2)
        s_2.addQualifier(q_2).addQualifier(q_1)
        s_3.addQualifier(q_1)
        self.assertEquals(s_1, s_2)
        self.assertNotEquals(s_1, s_3)

    def test_statement_qualifier_duplicates(self):
        s = WD.Statement('foo')
        q = WD.Qualifier('P123', 'bar')
        s.addQualifier(q)
        s.addQualifier(q)
        self.assertEquals(s.quals, [q])

    def test_statement_repr(self):
        s = WD.Statement('foo')
        q = WD.Qualifier('P123', 'bar')
        self.assertEqual(
            repr(s),
            'WD.Statement(itis:foo, quals:[], special:False, force:False)')
        s.addQualifier(q)
        self.assertEqual(
            repr(s),
            'WD.Statement(itis:foo, quals:[WD.Qualifier(P123, bar)], '
            'special:False, force:False)')


class TestReference(unittest.TestCase):

    """Test Reference."""

    def setUp(self):
        wikidata = Site('test', 'wikidata')
        self.ref_1 = Claim(wikidata, 'P55')
        self.ref_1.setTarget('foo')
        self.ref_2 = Claim(wikidata, 'P55')
        self.ref_2.setTarget('bar')

    def test_reference_init_empty_error(self):
        with self.assertRaises(pwbError) as cm:
            WD.Reference()
        self.assertEqual(
            str(cm.exception),
            'You tried to create a reference without any sources')

    def test_reference_init_non_claim_error(self):
        with self.assertRaises(pwbError) as cm:
            WD.Reference(source_test='foo')
        self.assertEqual(
            str(cm.exception),
            'You tried to create a reference with a non-Claim source')

        with self.assertRaises(pwbError) as cm:
            WD.Reference(source_notest='foo')
        self.assertEqual(
            str(cm.exception),
            'You tried to create a reference with a non-Claim source')

    def test_reference_init_single_claim_gives_list(self):
        r_test = WD.Reference(source_test=self.ref_1)
        self.assertEqual(r_test.source_test, [self.ref_1])
        self.assertEqual(r_test.source_notest, [])

        r_notest = WD.Reference(source_notest=self.ref_1)
        self.assertEqual(r_notest.source_test, [])
        self.assertEqual(r_notest.source_notest, [self.ref_1])

        r_both = WD.Reference(self.ref_1, self.ref_2)
        self.assertEqual(r_both.source_test, [self.ref_1])
        self.assertEqual(r_both.source_notest, [self.ref_2])

    def test_reference_init_with_list(self):
        r_test = WD.Reference(source_test=[self.ref_1, self.ref_2])
        self.assertEqual(r_test.source_test, [self.ref_1, self.ref_2])
        self.assertEqual(r_test.source_notest, [])

        r_notest = WD.Reference(source_notest=[self.ref_1, self.ref_2])
        self.assertEqual(r_notest.source_test, [])
        self.assertEqual(r_notest.source_notest, [self.ref_1, self.ref_2])

        r_both = WD.Reference([self.ref_1, self.ref_2],
                              [self.ref_2, self.ref_1])
        self.assertEqual(r_both.source_test, [self.ref_1, self.ref_2])
        self.assertEqual(r_both.source_notest, [self.ref_2, self.ref_1])

    def test_reference_get_all_sources(self):
        r_test = WD.Reference(source_test=self.ref_1)
        self.assertEqual(r_test.get_all_sources(), [self.ref_1])

        r_notest = WD.Reference(source_notest=self.ref_1)
        self.assertEqual(r_notest.get_all_sources(), [self.ref_1])

        r_both = WD.Reference(self.ref_1, self.ref_2)
        self.assertEqual(r_both.get_all_sources(), [self.ref_1, self.ref_2])

    def test_reference_repr(self):
        """Also ensures there is a repr for Claim."""
        r = WD.Reference(self.ref_1, self.ref_2)
        self.assertEqual(
            repr(r),
            'WD.Reference('
            'test: [WD.Claim(P55: foo)], '
            'no_test: [WD.Claim(P55: bar)])')
