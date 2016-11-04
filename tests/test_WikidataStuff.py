# -*- coding: utf-8  -*-
"""Unit tests for WikidataStuff."""


import pywikibot
import unittest
import json
import mock
import os
from wikidataStuff import WikidataStuff as WD


class BaseTest(unittest.TestCase):

    def setUp(self):
        """Setup test."""
        repo = pywikibot.Site('test', 'wikidata')
        self.wd_page = pywikibot.ItemPage(repo, None)
        data_dir = os.path.join(os.path.split(__file__)[0], 'data')
        with open(os.path.join(data_dir, 'Q27399.json')) as f:
            self.wd_page._content = json.load(f).get('entities').get('Q27399')
        self.wd_page._content['id'] = u'-1'  # override id used in demo file
        self.wd_page.get()
        self.wd_stuff = WD.WikidataStuff(repo)


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
