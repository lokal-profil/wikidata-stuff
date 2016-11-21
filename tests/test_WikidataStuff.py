#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Unit tests for WikidataStuff."""


import pywikibot
import unittest
import json
import mock
import os
from wikidataStuff import WikidataStuff as WD


class TestListify(unittest.TestCase):

    """Test listify()."""

    def test_listify_none(self):
        self.assertEquals(WD.listify(None), None)

    def test_listify_empty_list(self):
        self.assertEquals(WD.listify([]), [])

    def test_listify_list(self):
        input_value = ['a', 'c']
        expected = ['a', 'c']
        self.assertEquals(WD.listify(input_value), expected)

    def test_listify_string(self):
        input_value = 'a string'
        expected = ['a string']
        self.assertEquals(WD.listify(input_value), expected)


class BaseTest(unittest.TestCase):

    def setUp(self):
        """Setup test."""
        self.repo = pywikibot.Site('test', 'wikidata')
        self.wd_page = pywikibot.ItemPage(self.repo, None)
        data_dir = os.path.join(os.path.split(__file__)[0], 'data')
        with open(os.path.join(data_dir, 'Q27399.json')) as f:
            self.wd_page._content = json.load(f).get('entities').get('Q27399')
        self.wd_page._content['id'] = u'-1'  # override id used in demo file
        self.wd_page.get()
        self.wd_stuff = WD.WikidataStuff(self.repo)


class TestAddLabelOrAlias(BaseTest):

    """Test addLabelOrAlias()."""

    def setUp(self):
        super(TestAddLabelOrAlias, self).setUp()
        # override loaded labels and aliases
        self.wd_page.labels = {u'en': u'en_label', u'sv': u'sv_label'}
        self.wd_page.aliases = {u'en': [u'en_alias_1', ]}

        alias_patcher = mock.patch(
            'wikidataStuff.WikidataStuff.pywikibot.ItemPage.editAliases')
        label_patcher = mock.patch(
            'wikidataStuff.WikidataStuff.pywikibot.ItemPage.editLabels')
        self.mock_edit_alias = alias_patcher.start()
        self.mock_edit_label = label_patcher.start()
        self.addCleanup(alias_patcher.stop)
        self.addCleanup(label_patcher.stop)

    def test_add_label_no_language(self):
        """Test adding label when language not present."""
        lang = 'fi'
        text = 'fi_label'
        self.wd_stuff.addLabelOrAlias(lang, text, self.wd_page)
        self.mock_edit_label.assert_called_once_with(
            {lang: text},
            summary=u'Added [fi] label to [[-1]]'
        )
        self.mock_edit_alias.assert_not_called()

    def test_add_label_has_same_label(self):
        lang = 'sv'
        text = 'sv_label'
        self.wd_stuff.addLabelOrAlias(lang, text, self.wd_page)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_not_called()

    def test_add_label_has_other_label(self):
        lang = 'sv'
        text = 'sv_label_2'
        self.wd_stuff.addLabelOrAlias(lang, text, self.wd_page)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_called_once_with(
            {lang: [text, ]},
            summary=u'Added [sv] alias to [[-1]]'
        )

    def test_add_label_has_same_alias(self):
        lang = 'en'
        text = 'en_alias_1'
        self.wd_stuff.addLabelOrAlias(lang, text, self.wd_page)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_not_called()

    def test_add_label_has_other_alias(self):
        lang = 'en'
        text = 'en_alias_2'
        self.wd_stuff.addLabelOrAlias(lang, text, self.wd_page)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_called_once_with(
            {lang: [u'en_alias_1', u'en_alias_2']},
            summary=u'Added [en] alias to [[-1]]'
        )

    def test_add_label_not_case_sensitive(self):
        lang = 'sv'
        text = 'SV_label'
        self.wd_stuff.addLabelOrAlias(lang, text, self.wd_page)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_not_called()

    def test_add_label_case_sensitive(self):
        lang = 'sv'
        text = 'SV_label'
        self.wd_stuff.addLabelOrAlias(
            lang, text, self.wd_page, caseSensitive=True)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_called_once_with(
            {lang: [text, ]},
            summary=u'Added [sv] alias to [[-1]]'
        )

    def test_add_label_with_summary(self):
        lang = 'sv'
        text = 'sv_label_2'
        self.wd_stuff.addLabelOrAlias(lang, text, self.wd_page, summary='TEXT')
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_called_once_with(
            {lang: [text, ]},
            summary=u'Added [sv] alias to [[-1]], TEXT'
        )


class TestHasClaim(BaseTest):

    """Test hasClaim()."""

    def setUp(self):
        super(TestHasClaim, self).setUp()

        alias_patcher = mock.patch(
            'wikidataStuff.WikidataStuff.pywikibot.ItemPage.editAliases')
        label_patcher = mock.patch(
            'wikidataStuff.WikidataStuff.pywikibot.ItemPage.editLabels')
        self.mock_edit_alias = alias_patcher.start()
        self.mock_edit_label = label_patcher.start()
        self.addCleanup(alias_patcher.stop)
        self.addCleanup(label_patcher.stop)

    def test_has_claim_prop_not_present(self):
        prop = 'P0'
        itis = 'A string'
        self.assertIsNone(self.wd_stuff.hasClaim(prop, itis, self.wd_page))

    def test_has_claim_prop_but_not_value(self):
        prop = 'P174'
        itis = 'An unknown string'
        self.assertIsNone(self.wd_stuff.hasClaim(prop, itis, self.wd_page))

    def test_has_claim_simple_match(self):
        prop = 'P174'
        itis = 'A string'
        expected = 'Q27399$3f62d521-4efe-e8de-8f2d-0d8a10e024cf'
        self.assertEquals(
            self.wd_stuff.hasClaim(prop, itis, self.wd_page).toJSON()['id'],
            expected)

    def test_has_claim_match_independent_of_reference(self):
        prop = 'P174'
        itis = 'A string with a reference'
        expected = 'Q27399$ef9f73ce-4cd5-13e5-a0bf-4ad835d8f9c3'
        self.assertEquals(
            self.wd_stuff.hasClaim(prop, itis, self.wd_page).toJSON()['id'],
            expected)

    def test_has_claim_match_item_type(self):
        prop = 'P84'
        itis = pywikibot.ItemPage(self.repo, 'Q1341')
        expected = 'Q27399$58a0a8bc-46e4-3dc6-16fe-e7c364103c9b'
        self.assertEquals(
            self.wd_stuff.hasClaim(prop, itis, self.wd_page).toJSON()['id'],
            expected)

    def test_has_claim_match_WbTime_type(self):
        prop = 'P74'
        itis = pywikibot.WbTime(year=2016, month=11, day=22, site=self.repo)

        with mock.patch('wikidataStuff.WikidataStuff.WikidataStuff.compareWbTimeClaim', autospec=True) as mock_compare_WbTime:
            self.wd_stuff.hasClaim(prop, itis, self.wd_page)
            mock_compare_WbTime.assert_called_once_with(
                self.wd_stuff, itis, itis)

    # this test should fail later
    # then check that it gets the qualified one only (or all of them)
    def test_has_claim_match_independent_of_qualifier(self):
        prop = 'P174'
        itis = 'A string entry with a qualifier'
        expected = 'Q27399$50b7cccb-4e9d-6f5d-d9c9-6b85d771c2d4'
        self.assertEquals(
            self.wd_stuff.hasClaim(prop, itis, self.wd_page).toJSON()['id'],
            expected)
