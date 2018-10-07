#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Tests for WikidataStuff Qualifier."""
from __future__ import unicode_literals
import unittest

from pywikibot import (
    Error as pwbError,
    Site as Site,
    Claim as Claim
)

from wikidataStuff.reference import Reference


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
            Reference()
        self.assertEqual(
            str(cm.exception),
            'You tried to create a reference without any sources')

    def test_reference_init_non_claim_error(self):
        with self.assertRaises(pwbError) as cm:
            Reference(source_test='foo')
        self.assertEqual(
            str(cm.exception),
            'You tried to create a reference with a non-Claim source')

        with self.assertRaises(pwbError) as cm:
            Reference(source_notest='foo')
        self.assertEqual(
            str(cm.exception),
            'You tried to create a reference with a non-Claim source')

    def test_reference_init_single_claim_gives_list(self):
        r_test = Reference(source_test=self.ref_1)
        self.assertEqual(r_test.source_test, [self.ref_1])
        self.assertEqual(r_test.source_notest, [])

        r_notest = Reference(source_notest=self.ref_1)
        self.assertEqual(r_notest.source_test, [])
        self.assertEqual(r_notest.source_notest, [self.ref_1])

        r_both = Reference(self.ref_1, self.ref_2)
        self.assertEqual(r_both.source_test, [self.ref_1])
        self.assertEqual(r_both.source_notest, [self.ref_2])

    def test_reference_init_with_list(self):
        r_test = Reference(source_test=[self.ref_1, self.ref_2])
        self.assertEqual(r_test.source_test, [self.ref_1, self.ref_2])
        self.assertEqual(r_test.source_notest, [])

        r_notest = Reference(source_notest=[self.ref_1, self.ref_2])
        self.assertEqual(r_notest.source_test, [])
        self.assertEqual(r_notest.source_notest, [self.ref_1, self.ref_2])

        r_both = Reference([self.ref_1, self.ref_2], [self.ref_2, self.ref_1])
        self.assertEqual(r_both.source_test, [self.ref_1, self.ref_2])
        self.assertEqual(r_both.source_notest, [self.ref_2, self.ref_1])

    def test_reference_get_all_sources(self):
        r_test = Reference(source_test=self.ref_1)
        self.assertEqual(r_test.get_all_sources(), [self.ref_1])

        r_notest = Reference(source_notest=self.ref_1)
        self.assertEqual(r_notest.get_all_sources(), [self.ref_1])

        r_both = Reference(self.ref_1, self.ref_2)
        self.assertEqual(r_both.get_all_sources(), [self.ref_1, self.ref_2])

    def test_reference_repr(self):
        """Also ensures there is a repr for Claim."""
        r = Reference(self.ref_1, self.ref_2)
        self.assertEqual(
            repr(r),
            'WD.Reference('
            'test: [WD.Claim(P55: foo)], '
            'no_test: [WD.Claim(P55: bar)])')
