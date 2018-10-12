#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Unit tests for WikidataStuff."""
from __future__ import unicode_literals
import json
import mock
import os
import unittest

import pywikibot

from wikidataStuff import wikidata_stuff
from wikidataStuff.reference import Reference  # replace with mocks
from wikidataStuff.statement import Statement  # replace with mocks
from wikidataStuff.qualifier import Qualifier  # replace with mocks


class BaseTest(unittest.TestCase):

    """Base test setting loading offline data and setting up patchers."""

    def setUp(self):
        """Setup test."""
        self.repo = pywikibot.Site('test', 'wikidata')
        self.wd_page = pywikibot.ItemPage(self.repo, None)
        data_dir = os.path.join(os.path.split(__file__)[0], 'data')
        with open(os.path.join(data_dir, 'Q27399.json')) as f:
            self.wd_page._content = json.load(f).get('entities').get('Q27399')
        self.wd_page._content['id'] = '-1'  # override id used in demo file
        self.wd_page.get()
        self.wd_stuff = wikidata_stuff.WikidataStuff(self.repo)

        # silence output
        output_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.pywikibot.output')
        warning_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.pywikibot.warning')
        self.mock_output = output_patcher.start()
        self.mock_warning = warning_patcher.start()
        self.addCleanup(output_patcher.stop)
        self.addCleanup(warning_patcher.stop)


class TestAddDescription(BaseTest):

    """Test add_description()."""

    def setUp(self):
        super(TestAddDescription, self).setUp()

        description_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.WikidataStuff.'
            'add_multiple_descriptions')
        self.mock_add_multiple_descriptions = description_patcher.start()
        self.addCleanup(description_patcher.stop)

    def test_add_description_send_to_add_multiple(self):
        """Test add_multiple is called with right values and defaults."""
        lang = 'fi'
        text = 'fi_desc'
        self.wd_stuff.add_description(lang, text, self.wd_page)
        self.mock_add_multiple_descriptions.assert_called_once_with(
            {'fi': 'fi_desc'}, self.wd_page, overwrite=False, summary=None)

    def test_add_description_send_all_params_to_add_multiple(self):
        """Test add_multiple is called with all parameters."""
        lang = 'fi'
        text = 'fi_desc'
        self.wd_stuff.add_description(
            lang, text, self.wd_page, True, 'test')
        self.mock_add_multiple_descriptions.assert_called_once_with(
            {'fi': 'fi_desc'}, self.wd_page, overwrite=True, summary='test')


class TestAddMultipleDescriptions(BaseTest):

    """Test add_multiple_descriptions()."""

    def setUp(self):
        super(TestAddMultipleDescriptions, self).setUp()
        # override loaded descriptions
        self.wd_page.descriptions = {u'en': u'en_desc', u'sv': u'sv_desc'}

        description_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.pywikibot.ItemPage.editDescriptions')
        self.mock_edit_description = description_patcher.start()
        self.addCleanup(description_patcher.stop)

    def test_add_multiple_descriptions_empty(self):
        """Test calling without data."""
        data = {}
        self.wd_stuff.add_multiple_descriptions(data, self.wd_page)
        self.mock_edit_description.assert_not_called()

    def test_add_multiple_descriptions_no_descriptions(self):
        """Test adding description when no descriptions present."""
        self.wd_page.descriptions = {}
        data = {'fi': 'fi_desc'}
        self.wd_stuff.add_multiple_descriptions(data, self.wd_page)
        self.mock_edit_description.assert_called_once_with(
            {'fi': 'fi_desc'},
            summary=u'Added [fi] description to [[-1]]'
        )

    def test_add_multiple_descriptions_no_language(self):
        """Test adding description when language not present."""
        data = {'fi': 'fi_desc'}
        self.wd_stuff.add_multiple_descriptions(data, self.wd_page)
        self.mock_edit_description.assert_called_once_with(
            {'fi': 'fi_desc'},
            summary=u'Added [fi] description to [[-1]]'
        )

    def test_add_multiple_descriptions_has_language(self):
        """Test adding description when already present."""
        data = {'sv': 'sv_new_desc'}
        self.wd_stuff.add_multiple_descriptions(data, self.wd_page)
        self.mock_edit_description.assert_not_called()

    def test_add_multiple_descriptions_overwrite(self):
        """Test overwriting description when already present."""
        data = {'sv': 'sv_new_desc'}
        self.wd_stuff.add_multiple_descriptions(
            data, self.wd_page, overwrite=True)
        self.mock_edit_description.assert_called_once_with(
            {'sv': 'sv_new_desc'},
            summary=u'Added [sv] description to [[-1]]'
        )

    def test_add_multiple_descriptions_with_summary(self):
        """Test appending to the summary."""
        data = {'fi': 'fi_desc'}
        self.wd_stuff.add_multiple_descriptions(
            data, self.wd_page, summary='TEXT')
        self.mock_edit_description.assert_called_once_with(
            {'fi': 'fi_desc'},
            summary=u'Added [fi] description to [[-1]], TEXT'
        )

    def test_add_multiple_descriptions_many_add_all(self):
        """Test sending multiple where all are new."""
        data = {
            'fi': 'fi_desc',
            'de': 'de_desc'
        }
        self.wd_stuff.add_multiple_descriptions(data, self.wd_page)
        self.mock_edit_description.assert_called_once_with(
            {'fi': 'fi_desc', 'de': 'de_desc'},
            summary=u'Added [de, fi] description to [[-1]]'
        )

    def test_add_multiple_descriptions_many_add_some(self):
        """Test sending multiple where only one is new."""
        data = {
            'fi': 'fi_desc',
            'sv': 'sv_new_desc'
        }
        self.wd_stuff.add_multiple_descriptions(data, self.wd_page)
        self.mock_edit_description.assert_called_once_with(
            {'fi': 'fi_desc'},
            summary=u'Added [fi] description to [[-1]]'
        )


class TestAddLabelOrAlias(BaseTest):

    """Test add_label_or_alias()."""

    def setUp(self):
        super(TestAddLabelOrAlias, self).setUp()

        description_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.WikidataStuff.'
            'add_multiple_label_or_alias')
        self.mock_add_multiple_label_or_alias = description_patcher.start()
        self.addCleanup(description_patcher.stop)

    def test_add_description_send_to_add_multiple(self):
        """Test add_multiple is called with right values and defaults."""
        lang = 'fi'
        text = 'fi_label'
        self.wd_stuff.add_label_or_alias(lang, text, self.wd_page)
        self.mock_add_multiple_label_or_alias.assert_called_once_with(
            {'fi': 'fi_label'}, self.wd_page, case_sensitive=False,
            summary=None)

    def test_add_description_send_all_params_to_add_multiple(self):
        """Test add_multiple is called with all parameters."""
        lang = 'fi'
        text = 'fi_label'
        self.wd_stuff.add_label_or_alias(
            lang, text, self.wd_page, 'test', True)
        self.mock_add_multiple_label_or_alias.assert_called_once_with(
            {'fi': 'fi_label'}, self.wd_page, case_sensitive=True,
            summary='test')


class TestAddMultipleLabelOrAlias(BaseTest):

    """Test add_multiple_label_or_alias()."""

    def setUp(self):
        super(TestAddMultipleLabelOrAlias, self).setUp()
        # override loaded labels and aliases
        self.wd_page.labels = {'en': 'en_label', 'sv': 'sv_label'}
        self.wd_page.aliases = {'en': ['en_alias_1', ]}

        alias_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.pywikibot.ItemPage.editAliases')
        label_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.pywikibot.ItemPage.editLabels')
        self.mock_edit_alias = alias_patcher.start()
        self.mock_edit_label = label_patcher.start()
        self.addCleanup(alias_patcher.stop)
        self.addCleanup(label_patcher.stop)

    def test_add_multiple_label_or_alias_empty(self):
        """Test calling without data."""
        data = {}
        self.wd_stuff.add_multiple_label_or_alias(data, self.wd_page)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_not_called()

    def test_add_multiple_label_or_alias_no_language(self):
        """Test adding label when language not present."""
        self.wd_page.labels = None
        self.wd_page.aliases = None
        data = {'fi': 'fi_label'}
        self.wd_stuff.add_multiple_label_or_alias(data, self.wd_page)
        self.mock_edit_label.assert_called_once_with(
            {'fi': 'fi_label'},
            summary='Added [fi] label to [[-1]]'
        )
        self.mock_edit_alias.assert_not_called()

    def test_add_multiple_label_or_alias_list_of_names(self):
        """Test adding label when language not present."""
        self.wd_page.labels = None
        self.wd_page.aliases = None
        data = {'fi': ['fi_label1', 'fi_label2', 'fi_label3']}
        self.wd_stuff.add_multiple_label_or_alias(data, self.wd_page)
        self.mock_edit_label.assert_called_once_with(
            {'fi': 'fi_label1'},
            summary='Added [fi] label to [[-1]]'
        )
        self.mock_edit_alias.assert_called_once_with(
            {'fi': ['fi_label2', 'fi_label3']},
            summary='Added [fi] alias to [[-1]]'
        )

    def test_add_multiple_label_or_alias_has_same_label(self):
        data = {'sv': 'sv_label'}
        self.wd_stuff.add_multiple_label_or_alias(data, self.wd_page)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_not_called()

    def test_add_multiple_label_or_alias_has_other_label(self):
        self.wd_page.aliases = None
        data = {'sv': 'sv_label_2'}
        self.wd_stuff.add_multiple_label_or_alias(data, self.wd_page)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_called_once_with(
            {'sv': ['sv_label_2', ]},
            summary='Added [sv] alias to [[-1]]'
        )

    def test_add_multiple_label_or_alias_has_same_alias(self):
        data = {'en': 'en_alias_1'}
        self.wd_stuff.add_multiple_label_or_alias(data, self.wd_page)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_not_called()

    def test_add_multiple_label_or_alias_has_other_alias(self):
        data = {'en': 'en_alias_2'}
        self.wd_stuff.add_multiple_label_or_alias(data, self.wd_page)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_called_once_with(
            {'en': ['en_alias_1', 'en_alias_2']},
            summary='Added [en] alias to [[-1]]'
        )

    def test_add_multiple_label_or_alias_not_case_sensitive(self):
        data = {'sv': 'SV_label'}
        self.wd_stuff.add_multiple_label_or_alias(data, self.wd_page)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_not_called()

    def test_add_multiple_label_or_alias_case_sensitive(self):
        self.wd_page.aliases = None
        data = {'sv': 'SV_label'}
        self.wd_stuff.add_multiple_label_or_alias(
            data, self.wd_page, case_sensitive=True)
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_called_once_with(
            {'sv': ['SV_label', ]},
            summary='Added [sv] alias to [[-1]]'
        )

    def test_add_multiple_label_or_alias_with_summary(self):
        self.wd_page.aliases = None
        data = {'sv': 'sv_label_2'}
        self.wd_stuff.add_multiple_label_or_alias(
            data, self.wd_page, summary='TEXT')
        self.mock_edit_label.assert_not_called()
        self.mock_edit_alias.assert_called_once_with(
            {'sv': ['sv_label_2', ]},
            summary='Added [sv] alias to [[-1]], TEXT'
        )

    def test_add_multiple_label_or_alias_many_add_all_labels(self):
        """Test sending multiple where all are new."""
        self.wd_page.labels = None
        self.wd_page.aliases = None
        data = {
            'fi': 'fi_label',
            'de': 'de_label'
        }
        self.wd_stuff.add_multiple_label_or_alias(data, self.wd_page)
        self.mock_edit_label.assert_called_once_with(
            {'fi': 'fi_label', 'de': 'de_label'},
            summary=u'Added [de, fi] label to [[-1]]'
        )

    def test_add_multiple_label_or_alias_many_add_all_aliases(self):
        """Test sending multiple where all are new."""
        data = {
            'en': 'en_alias_2',
            'sv': 'sv_label_2'
        }
        self.wd_stuff.add_multiple_label_or_alias(data, self.wd_page)
        self.mock_edit_alias.assert_called_once_with(
            {'en': ['en_alias_1', 'en_alias_2'], 'sv': ['sv_label_2', ]},
            summary=u'Added [en, sv] alias to [[-1]]'
        )

    def test_add_multiple_label_or_alias_many_add_mix(self):
        """Test sending multiple where some are alias and some labels."""
        self.wd_page.labels = {'sv': 'sv_label'}
        self.wd_page.aliases = None

        data = {
            'fi': 'fi_label',
            'sv': 'sv_label_2'
        }
        self.wd_stuff.add_multiple_label_or_alias(data, self.wd_page)
        self.mock_edit_label.assert_called_once_with(
            {'fi': 'fi_label', 'sv': 'sv_label'},
            summary=u'Added [fi] label to [[-1]]'
        )
        self.mock_edit_alias.assert_called_once_with(
            {'sv': ['sv_label_2', ]},
            summary='Added [sv] alias to [[-1]]'
        )

    def test_add_multiple_label_or_alias_many_add_some(self):
        """Test sending multiple where only one is new."""
        self.wd_page.labels = {'sv': 'sv_label'}
        data = {
            'fi': 'fi_label',
            'sv': 'sv_label'
        }
        self.wd_stuff.add_multiple_label_or_alias(data, self.wd_page)
        self.mock_edit_label.assert_called_once_with(
            {'fi': 'fi_label', 'sv': 'sv_label'},
            summary=u'Added [fi] label to [[-1]]'
        )


class TestHasClaim(BaseTest):

    """Test has_claim()."""

    def test_has_claim_prop_not_present(self):
        prop = 'P0'
        itis = 'A string'
        self.assertEqual(
            self.wd_stuff.has_claim(prop, itis, self.wd_page),
            [])

    def test_has_claim_prop_but_not_value(self):
        prop = 'P174'
        itis = 'An unknown string'
        self.assertEqual(
            self.wd_stuff.has_claim(prop, itis, self.wd_page),
            [])

    def test_has_claim_simple_match(self):
        prop = 'P174'
        itis = 'A string'
        expected = 'Q27399$3f62d521-4efe-e8de-8f2d-0d8a10e024cf'

        hits = self.wd_stuff.has_claim(prop, itis, self.wd_page)
        self.assertEqual(len(hits), 1)
        self.assertEqual(
            hits[0].toJSON()['id'],
            expected)

    def test_has_claim_match_independent_of_reference(self):
        prop = 'P174'
        itis = 'A string with a reference'
        expected = 'Q27399$ef9f73ce-4cd5-13e5-a0bf-4ad835d8f9c3'

        hits = self.wd_stuff.has_claim(prop, itis, self.wd_page)
        self.assertEqual(len(hits), 1)
        self.assertEqual(
            hits[0].toJSON()['id'],
            expected)

    def test_has_claim_match_item_type(self):
        prop = 'P84'
        itis = pywikibot.ItemPage(self.repo, 'Q1341')
        expected = 'Q27399$58a0a8bc-46e4-3dc6-16fe-e7c364103c9b'

        hits = self.wd_stuff.has_claim(prop, itis, self.wd_page)
        self.assertEqual(len(hits), 1)
        self.assertEqual(
            hits[0].toJSON()['id'],
            expected)

    def test_has_claim_match_wbtime_type(self):
        prop = 'P74'
        itis = pywikibot.WbTime(year=2016, month=11, day=22, site=self.repo)
        function = 'wikidataStuff.wikidata_stuff.WikidataStuff.compare_wbtime_claim'

        with mock.patch(function, autospec=True) as mock_compare_WbTime:
            self.wd_stuff.has_claim(prop, itis, self.wd_page)
            mock_compare_WbTime.assert_called_once_with(
                self.wd_stuff, itis, itis)

    def test_has_claim_match_independent_of_qualifier(self):
        prop = 'P174'
        itis = 'A string entry with a qualifier'
        expected = 'Q27399$50b7cccb-4e9d-6f5d-d9c9-6b85d771c2d4'

        hits = self.wd_stuff.has_claim(prop, itis, self.wd_page)
        self.assertEqual(len(hits), 1)
        self.assertEqual(
            hits[0].toJSON()['id'],
            expected)

    def test_has_claim_match_multiple(self):
        prop = 'P664'
        itis = 'Duplicate_string'
        expected_1 = 'Q27399$221e4451-46d7-8c4a-53cb-47a4e0d09660'
        expected_2 = 'Q27399$a9b83de1-49d7-d033-939d-f430a232ffd0'

        hits = self.wd_stuff.has_claim(prop, itis, self.wd_page)
        self.assertEqual(len(hits), 2)
        self.assertEqual(
            hits[0].toJSON()['id'],
            expected_1)
        self.assertEqual(
            hits[1].toJSON()['id'],
            expected_2)


class TestHasQualifier(BaseTest):

    """Test has_qualifier()."""

    def setUp(self):
        super(TestHasQualifier, self).setUp()
        self.claim_no_qual = self.wd_page.claims['P174'][2]
        # one qualifier: P174:A qualifier
        self.claim_one_qual = self.wd_page.claims['P174'][0]
        # two qualifiers: P174:A qualifier, P664:Another qualifier
        self.claim_two_quals_diff_p = self.wd_page.claims['P174'][4]
        # two qualifiers: P174:A qualifier, P174:Another qualifier
        self.claim_two_quals_same_p = self.wd_page.claims['P174'][5]

        # load three claims to use when making references
        self.qual_1 = Qualifier('P174', 'A qualifier')
        self.qual_2 = Qualifier('P664', 'Another qualifier')
        self.qual_3 = Qualifier('P174', 'Another qualifier')
        self.unmatched_val = Qualifier('P174', 'Unmatched')
        self.unmatched_p = Qualifier('P0', 'A qualifier')

    def test_has_qualifier_no_qualifier(self):
        self.assertFalse(
            self.wd_stuff.has_qualifier(
                self.qual_1, self.claim_no_qual))

    def test_has_qualifier_different_qualifier(self):
        self.assertFalse(
            self.wd_stuff.has_qualifier(
                self.qual_2, self.claim_one_qual))

    def test_has_qualifier_different_qualifier_prop(self):
        self.assertFalse(
            self.wd_stuff.has_qualifier(
                self.unmatched_p, self.claim_one_qual))

    def test_has_qualifier_different_qualifier_value(self):
        self.assertFalse(
            self.wd_stuff.has_qualifier(
                self.unmatched_val, self.claim_one_qual))

    def test_has_qualifier_same_qualifier(self):
        self.assertTrue(
            self.wd_stuff.has_qualifier(
                self.qual_1, self.claim_one_qual))

    def test_has_qualifier_multiple_qualifiers_different_prop(self):
        claim = self.claim_two_quals_diff_p
        expect_qual_1 = self.qual_1
        expect_qual_2 = self.qual_2
        unexpected_qual = self.unmatched_val
        self.assertTrue(self.wd_stuff.has_qualifier(expect_qual_1, claim))
        self.assertTrue(self.wd_stuff.has_qualifier(expect_qual_2, claim))
        self.assertFalse(self.wd_stuff.has_qualifier(unexpected_qual, claim))

    def test_has_qualifier_multiple_qualifiers_same_prop(self):
        claim = self.claim_two_quals_same_p
        expect_qual_1 = self.qual_1
        expect_qual_2 = self.qual_3
        unexpected_qual = self.unmatched_val
        self.assertTrue(self.wd_stuff.has_qualifier(expect_qual_1, claim))
        self.assertTrue(self.wd_stuff.has_qualifier(expect_qual_2, claim))
        self.assertFalse(self.wd_stuff.has_qualifier(unexpected_qual, claim))


class TestHasAllQualifiers(BaseTest):

    """Test has_all_qualifiers()."""

    def setUp(self):
        super(TestHasAllQualifiers, self).setUp()
        self.quals = []

        # load claims
        self.claim_no_qual = self.wd_page.claims['P174'][2]
        # two qualifiers: P174:A qualifier, P664:Another qualifier
        self.claim = self.wd_page.claims['P174'][4]

        # load qualifiers
        self.qual_1 = Qualifier('P174', 'A qualifier')
        self.qual_2 = Qualifier('P664', 'Another qualifier')
        self.unmatched = Qualifier('P174', 'Unmatched')

    def test_has_all_qualifiers_none(self):
        with self.assertRaises(TypeError):
            self.wd_stuff.has_all_qualifiers(None, self.claim)

    def test_has_all_qualifiers_empty(self):
        expected = (True, True)
        self.assertEqual(
            self.wd_stuff.has_all_qualifiers(self.quals, self.claim_no_qual),
            expected)

    def test_has_all_qualifiers_has_all(self):
        self.quals.append(self.qual_1)
        self.quals.append(self.qual_2)
        expected = (True, True)
        self.assertEqual(
            self.wd_stuff.has_all_qualifiers(self.quals, self.claim),
            expected)

    def test_has_all_qualifiers_has_all_but_one(self):
        self.quals.append(self.qual_1)
        self.quals.append(self.qual_2)
        self.quals.append(self.unmatched)
        expected = (False, False)
        self.assertEqual(
            self.wd_stuff.has_all_qualifiers(self.quals, self.claim),
            expected)

    def test_has_all_qualifiers_has_all_plus_one(self):
        self.quals.append(self.qual_1)
        expected = (False, True)
        self.assertEqual(
            self.wd_stuff.has_all_qualifiers(self.quals, self.claim),
            expected)


class TestAddReference(BaseTest):

    """Test add_reference()."""

    def setUp(self):
        super(TestAddReference, self).setUp()
        self.claim_no_ref = self.wd_page.claims['P174'][2]
        # one ref with two claims: P174:ref_1, P664:ref_2
        self.claim_one_ref = self.wd_page.claims['P174'][1]
        # two refs each with one claim: P174:ref_1, P174:ref_2
        self.claim_two_refs = self.wd_page.claims['P174'][3]

        # load three claims to use when making references
        self.ref_1 = pywikibot.Claim(self.repo, 'P174')
        self.ref_1.setTarget('ref_1')
        self.ref_2 = pywikibot.Claim(self.repo, 'P664')
        self.ref_2.setTarget('ref_2')
        self.unmatched_ref = pywikibot.Claim(self.repo, 'P174')
        self.unmatched_ref.setTarget('Unmatched_ref')

        sources_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.pywikibot.Claim.addSources')
        self.mock_add_sources = sources_patcher.start()
        self.addCleanup(sources_patcher.stop)

    def test_add_reference_empty_ref(self):
        self.assertFalse(
            self.wd_stuff.add_reference(item=None, claim=None, ref=None))
        self.mock_add_sources.assert_not_called()

    def test_add_reference_test_no_prior(self):
        reference = Reference(source_test=self.ref_1)
        self.assertTrue(
            self.wd_stuff.add_reference(
                item=self.wd_page,
                claim=self.claim_no_ref,
                ref=reference))
        self.mock_add_sources.assert_called_once_with(
            [self.ref_1], summary=None)

    def test_add_reference_notest_no_prior(self):
        reference = Reference(source_notest=self.ref_1)
        self.assertTrue(
            self.wd_stuff.add_reference(
                item=self.wd_page,
                claim=self.claim_no_ref,
                ref=reference))
        self.mock_add_sources.assert_called_once_with(
            [self.ref_1], summary=None)

    def test_add_reference_has_ref_and_one_more(self):
        reference = Reference(source_test=self.ref_1)
        self.assertFalse(
            self.wd_stuff.add_reference(
                item=self.wd_page,
                claim=self.claim_one_ref,
                ref=reference))
        self.mock_add_sources.assert_not_called()

    def test_add_reference_has_both(self):
        reference = Reference(
            source_test=self.ref_1, source_notest=self.ref_2)
        self.assertFalse(
            self.wd_stuff.add_reference(
                item=self.wd_page,
                claim=self.claim_one_ref,
                ref=reference))
        self.mock_add_sources.assert_not_called()

    def test_add_reference_has_test_only(self):
        reference = Reference(
            source_test=self.ref_1, source_notest=self.unmatched_ref)
        self.assertFalse(
            self.wd_stuff.add_reference(
                item=self.wd_page,
                claim=self.claim_one_ref,
                ref=reference))
        self.mock_add_sources.assert_not_called()

    def test_add_reference_has_notest_only(self):
        reference = Reference(
            source_test=self.unmatched_ref, source_notest=self.ref_2)
        self.assertTrue(
            self.wd_stuff.add_reference(
                item=self.wd_page,
                claim=self.claim_one_ref,
                ref=reference))
        self.mock_add_sources.assert_called_once_with(
            [self.unmatched_ref, self.ref_2], summary=None)

    def test_add_reference_with_summary(self):
        reference = Reference(source_test=self.ref_1)
        self.assertTrue(
            self.wd_stuff.add_reference(
                item=self.wd_page,
                claim=self.claim_no_ref,
                ref=reference,
                summary='test_me'))
        self.mock_add_sources.assert_called_once_with(
            [self.ref_1], summary='test_me')

    def test_add_reference_detect_when_multple_sources(self):
        reference = Reference(source_test=self.ref_1)
        self.assertFalse(
            self.wd_stuff.add_reference(
                item=self.wd_page,
                claim=self.claim_two_refs,
                ref=reference))
        self.mock_add_sources.assert_not_called()

    def test_add_reference_add_when_multple_sources(self):
        reference = Reference(source_test=self.ref_2)
        self.assertTrue(
            self.wd_stuff.add_reference(
                item=self.wd_page,
                claim=self.claim_two_refs,
                ref=reference))
        self.mock_add_sources.assert_called_once_with(
            [self.ref_2], summary=None)


class TestAddQualifier(BaseTest):

    """Test add_qualifier()."""

    def setUp(self):
        super(TestAddQualifier, self).setUp()
        self.claim = self.wd_page.claims['P174'][2]
        self.qual = Qualifier('P174', 'A qualifier')

        qualifier_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.pywikibot.Claim.addQualifier')
        make_claim_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.WikidataStuff.make_simple_claim')
        has_qualifier_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.WikidataStuff.has_qualifier')
        self.mock_add_qualifier = qualifier_patcher.start()
        self.mock_make_simple_claim = make_claim_patcher.start()
        self.mock_has_qualifier = has_qualifier_patcher.start()
        self.addCleanup(qualifier_patcher.stop)
        self.addCleanup(make_claim_patcher.stop)
        self.addCleanup(has_qualifier_patcher.stop)

    def test_add_qualifier_empty_qual(self):
        with self.assertRaises(pywikibot.Error) as e:
            self.wd_stuff.add_qualifier(item=None, claim=None, qual=None)
        self.assertEqual(
            str(e.exception),
            'Cannot call add_qualifier() without a qualifier.')
        self.mock_has_qualifier.assert_not_called()
        self.mock_make_simple_claim.assert_not_called()
        self.mock_add_qualifier.assert_not_called()

    def test_add_qualifier_has(self):
        self.mock_has_qualifier.return_value = True
        self.assertFalse(
            self.wd_stuff.add_qualifier(
                item=self.wd_page,
                claim=self.claim,
                qual=self.qual))
        self.mock_has_qualifier.assert_called_once_with(
            self.qual, self.claim)
        self.mock_make_simple_claim.assert_not_called()
        self.mock_add_qualifier.assert_not_called()

    def test_add_qualifier_has_not(self):
        self.mock_has_qualifier.return_value = False
        self.mock_make_simple_claim.return_value = 'test'
        self.assertTrue(
            self.wd_stuff.add_qualifier(
                item=self.wd_page,
                claim=self.claim,
                qual=self.qual))
        self.mock_has_qualifier.assert_called_once_with(
            self.qual, self.claim)
        self.mock_make_simple_claim.assert_called_once_with(
            self.qual.prop, self.qual.itis)
        self.mock_add_qualifier.assert_called_once_with(
            'test', summary=None)

    def test_add_qualifier_with_summary(self):
        self.mock_has_qualifier.return_value = False
        self.mock_make_simple_claim.return_value = 'test'
        self.assertTrue(
            self.wd_stuff.add_qualifier(
                item=self.wd_page,
                claim=self.claim,
                qual=self.qual,
                summary='test_me'))
        self.mock_has_qualifier.assert_called_once_with(
            self.qual, self.claim)
        self.mock_make_simple_claim.assert_called_once_with(
            self.qual.prop, self.qual.itis)
        self.mock_add_qualifier.assert_called_once_with(
            'test', summary='test_me')


class TestAddNewClaim(BaseTest):

    """Test add_new_claim()."""

    def setUp(self):
        super(TestAddNewClaim, self).setUp()

        # mock all writing calls
        add_qualifier_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.WikidataStuff.add_qualifier')
        add_reference_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.WikidataStuff.add_reference')
        add_claim_patcher = mock.patch(
            'wikidataStuff.wikidata_stuff.pywikibot.ItemPage.addClaim')
        self.mock_add_qualifier = add_qualifier_patcher.start()
        self.mock_add_reference = add_reference_patcher.start()
        self.mock_add_claim = add_claim_patcher.start()
        self.addCleanup(add_qualifier_patcher.stop)
        self.addCleanup(add_reference_patcher.stop)
        self.addCleanup(add_claim_patcher.stop)

        # defaults
        self.ref = None
        self.prop = 'P509'  # an unused property of type string
        self.value = 'A statement'
        self.qual_1 = Qualifier('P174', 'A qualifier')
        self.qual_2 = Qualifier('P664', 'Another qualifier')
        self.mock_ref_1 = mock.create_autospec(Reference)
        self.mock_ref_2 = mock.create_autospec(Reference)

    def test_add_new_claim_new_property(self):
        statement = Statement(self.value)
        self.wd_stuff.add_new_claim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_called_once()
        self.mock_add_qualifier.assert_not_called()
        self.mock_add_reference.assert_called_once()

    def test_add_new_claim_old_property_new_value(self):
        self.prop = 'P174'
        statement = Statement(self.value)
        self.wd_stuff.add_new_claim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_called_once()
        self.mock_add_qualifier.assert_not_called()
        self.mock_add_reference.assert_called_once()

    def test_add_new_claim_old_property_old_value(self):
        self.prop = 'P174'
        self.value = 'A string'
        statement = Statement(self.value)
        expected_claim = 'Q27399$3f62d521-4efe-e8de-8f2d-0d8a10e024cf'
        self.wd_stuff.add_new_claim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_not_called()
        self.mock_add_qualifier.assert_not_called()
        self.mock_add_reference.assert_called_once()

        # ensure the right claim was sourced
        self.assertEqual(
            self.mock_add_reference.call_args[0][1].toJSON()['id'],
            expected_claim)

    def test_add_new_claim_new_property_with_quals(self):
        statement = Statement(self.value)
        statement.add_qualifier(self.qual_1).add_qualifier(self.qual_2)
        self.wd_stuff.add_new_claim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_called_once()
        self.assertEqual(self.mock_add_qualifier.call_count, 2)
        self.mock_add_reference.assert_called_once()

    def test_add_new_claim_old_property_new_value_with_quals(self):
        self.prop = 'P174'
        statement = Statement(self.value)
        statement.add_qualifier(self.qual_1).add_qualifier(self.qual_2)
        self.wd_stuff.add_new_claim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_called_once()
        self.assertEqual(self.mock_add_qualifier.call_count, 2)
        self.mock_add_reference.assert_called_once()

    def test_add_new_claim_old_property_old_value_without_quals(self):
        self.prop = 'P174'
        self.value = 'A string'
        statement = Statement(self.value)
        statement.add_qualifier(self.qual_1).add_qualifier(self.qual_2)
        expected_claim = 'Q27399$3f62d521-4efe-e8de-8f2d-0d8a10e024cf'
        self.wd_stuff.add_new_claim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_not_called()
        self.assertEqual(self.mock_add_qualifier.call_count, 2)
        self.mock_add_reference.assert_called_once()
        self.assertEqual(
            self.mock_add_reference.call_args[0][1].toJSON()['id'],
            expected_claim)

    def test_add_new_claim_old_property_old_value_with_different_quals(self):
        self.prop = 'P174'
        self.value = 'A string entry with a qualifier'
        statement = Statement(self.value)
        statement.add_qualifier(self.qual_1).add_qualifier(self.qual_2)
        self.wd_stuff.add_new_claim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_called_once()
        self.assertEqual(self.mock_add_qualifier.call_count, 2)
        self.mock_add_reference.assert_called_once()

    def test_add_new_claim_old_property_old_value_with_same_quals(self):
        self.prop = 'P174'
        self.value = 'A string entry with many qualifiers'
        statement = Statement(self.value)
        statement.add_qualifier(self.qual_1).add_qualifier(self.qual_2)
        expected_claim = 'Q27399$b48a2630-4fbb-932d-4f01-eefcf1e73f59'
        self.wd_stuff.add_new_claim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_not_called()
        self.assertEqual(self.mock_add_qualifier.call_count, 2)
        self.mock_add_reference.assert_called_once()
        self.assertEqual(
            self.mock_add_reference.call_args[0][1].toJSON()['id'],
            expected_claim)

    def test_add_new_claim_edit_correct_qualified_claim(self):
        self.prop = 'P664'
        self.value = 'Duplicate_string'
        statement = Statement(self.value)
        statement.add_qualifier(
            Qualifier('P174', 'qualifier'))
        expected_claim = 'Q27399$a9b83de1-49d7-d033-939d-f430a232ffd0'
        self.wd_stuff.add_new_claim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_not_called()
        self.mock_add_claim.mock_add_qualifier()
        self.mock_add_reference.assert_called_once()
        self.assertEqual(
            self.mock_add_reference.call_args[0][1].toJSON()['id'],
            expected_claim)

    def test_add_new_claim_edit_correct_qualified_claim_with_ref(self):
        self.prop = 'P664'
        self.value = 'Duplicate_string_with_ref'
        statement = Statement(self.value)
        statement.add_qualifier(
            Qualifier('P174', 'qualifier'))
        expected_claim = 'Q27399$e63f47a3-45ea-e2fc-1363-8f6062205084'
        self.wd_stuff.add_new_claim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_not_called()
        self.mock_add_claim.mock_add_qualifier()
        self.mock_add_reference.assert_called_once()
        self.assertEqual(
            self.mock_add_reference.call_args[0][1].toJSON()['id'],
            expected_claim)

    def test_add_new_claim_call_special_has_claim(self):
        value = 'somevalue'
        statement = Statement(value, special=True)
        function = 'wikidataStuff.wikidata_stuff.WikidataStuff.has_special_claim'

        with mock.patch(function, autospec=True) as mock_has_special_claim:
            self.wd_stuff.add_new_claim(
                self.prop, statement, self.wd_page, self.ref)
            mock_has_special_claim.assert_called_once_with(
                self.wd_stuff, self.prop, value, self.wd_page)

    def test_add_new_claim_embedded_ref_used(self):
        statement = Statement(self.value)
        statement.add_reference(self.mock_ref_2)
        self.wd_stuff.add_new_claim(
            self.prop, statement, self.wd_page, None)
        self.mock_add_reference.assert_called_once()
        self.assertEqual(
            self.mock_add_reference.call_args[0][2],
            self.mock_ref_2)

    def test_add_new_claim_provided_ref_overrides_embedded_ref(self):
        statement = Statement(self.value)
        statement.add_reference(self.mock_ref_2)
        self.wd_stuff.add_new_claim(
            self.prop, statement, self.wd_page, self.mock_ref_1)
        self.mock_add_reference.assert_called_once()
        self.assertEqual(
            self.mock_add_reference.call_args[0][2],
            self.mock_ref_1)

    def test_add_new_claim_raise_error_on_bad_ref(self):
        statement = Statement(self.value)
        with self.assertRaises(pywikibot.Error) as e:
            self.wd_stuff.add_new_claim(
                self.prop, statement, self.wd_page, 'Not a ref')
        self.assertEqual(str(e.exception),
                         'The provided reference was not a '
                         'Reference object. Crashing')

    def test_add_new_claim_warning_on_duplicate_matching_claim(self):
        self.prop = 'P84'
        self.value = pywikibot.ItemPage(self.repo, 'Q505')
        statement = Statement(self.value)
        self.wd_stuff.add_new_claim(
            self.prop, statement, self.wd_page, self.ref)
        self.mock_warning.assert_called_once_with(
            'Problem adding P84 claim to [[wikidata:test:-1]]: '
            'Multiple identical claims')
        self.mock_add_claim.assert_not_called()
        self.mock_add_qualifier.assert_not_called()
        self.mock_add_reference.assert_not_called()


class TestMatchClaim(BaseTest):

    """Test match_claim()."""

    def setUp(self):
        super(TestMatchClaim, self).setUp()

        # defaults
        self.claims = []
        self.qualifiers = []
        self.force = False

        # Load claims to descriptive variables
        # note that only qualifiers + references matter, main value is ignored
        # the default qualifier in these is P174:"A qualifier"
        self.one_qual_no_ref = self.wd_page.claims['P174'][0]
        self.no_qual_two_ref = self.wd_page.claims['P174'][1]
        self.no_qual_no_ref = self.wd_page.claims['P174'][2]
        # Second qualifier P174:"Another qualifier"
        self.two_qual_no_ref = self.wd_page.claims['P174'][5]

        # load two qualifier
        self.matched_qualifier = Qualifier('P174', 'A qualifier')
        self.unmatched_qualifier = Qualifier('P174', 'Unmatched')

    def test_match_claim_empty_claim(self):
        # 0. no claims: None selected
        self.assertIsNone(
            self.wd_stuff.match_claim(
                self.claims, self.qualifiers, self.force))

    def test_match_claim_multiple_exact_raises_error(self):
        # 1. many exact matches: raise error (means duplicates on Wikidata)
        self.claims.append(self.no_qual_two_ref)
        self.claims.append(self.no_qual_no_ref)
        with self.assertRaises(pywikibot.Error) as e:
            self.wd_stuff.match_claim(
                self.claims, self.qualifiers, self.force)
        self.assertEqual(str(e.exception), 'Multiple identical claims')

    def test_match_claim_empty_qualifier_exact(self):
        # 2. if no qualifier select the unqualified
        self.claims.append(self.one_qual_no_ref)
        self.claims.append(self.no_qual_no_ref)
        expected_claim = self.no_qual_no_ref
        self.assertEqual(
            self.wd_stuff.match_claim(
                self.claims, self.qualifiers, self.force),
            expected_claim)

    def test_match_claim_one_qualifier_exact(self):
        # 2. if qualifier select the qualified
        self.claims.append(self.one_qual_no_ref)
        self.claims.append(self.no_qual_no_ref)
        self.claims.append(self.two_qual_no_ref)
        self.qualifiers.append(self.matched_qualifier)
        expected_claim = self.one_qual_no_ref
        self.assertEqual(
            self.wd_stuff.match_claim(
                self.claims, self.qualifiers, self.force),
            expected_claim)

    def test_match_claim_multiple_close_raises_error(self):
        # 3. unclaimed i equally close to any with claims
        self.claims.append(self.one_qual_no_ref)
        self.claims.append(self.two_qual_no_ref)
        with self.assertRaises(pywikibot.Error) as e:
            self.wd_stuff.match_claim(
                self.claims, self.qualifiers, self.force)
        self.assertEqual(str(e.exception), 'Multiple semi-identical claims')

    def test_match_claim_one_qualifier_close(self):
        # 4. if qualified select the closest match
        # (contains at least that qualifier)
        self.claims.append(self.no_qual_no_ref)
        self.claims.append(self.two_qual_no_ref)
        self.qualifiers.append(self.matched_qualifier)
        expected_claim = self.two_qual_no_ref
        self.assertEqual(
            self.wd_stuff.match_claim(
                self.claims, self.qualifiers, self.force),
            expected_claim)

    def test_match_claim_many_non_close(self):
        # 5. qualifier does not match any of the claims
        self.claims.append(self.one_qual_no_ref)
        self.claims.append(self.two_qual_no_ref)
        self.qualifiers.append(self.unmatched_qualifier)
        self.assertIsNone(
            self.wd_stuff.match_claim(
                self.claims, self.qualifiers, self.force))

    def test_match_claim_one_claim(self):
        # 6.1 If only one claim and
        # if claim unsourced and unqualified: select this
        self.claims.append(self.no_qual_no_ref)
        expected_claim = self.no_qual_no_ref
        self.qualifiers.append(self.unmatched_qualifier)
        self.assertEqual(
            self.wd_stuff.match_claim(
                self.claims, self.qualifiers, self.force),
            expected_claim)

    def test_match_claim_one_sourced_claim_forced(self):
        # 6.2 If only one claim and
        # if sourced and unqualified and force: select this
        self.claims.append(self.no_qual_two_ref)
        self.qualifiers.append(self.unmatched_qualifier)
        self.force = True
        expected_claim = self.no_qual_two_ref
        self.assertEqual(
            self.wd_stuff.match_claim(
                self.claims, self.qualifiers, self.force),
            expected_claim)

    def test_match_claim_one_sourced_claim_none_selected(self):
        # 6.3 If only one claim and it is sourced None is selected
        self.claims.append(self.no_qual_two_ref)
        self.qualifiers.append(self.unmatched_qualifier)
        self.assertIsNone(
            self.wd_stuff.match_claim(
                self.claims, self.qualifiers, self.force))

    def test_match_claim_one_qualified_claim_none_selected(self):
        # 6.3 If only one claim and it is qualified None is selected
        self.claims.append(self.one_qual_no_ref)
        self.qualifiers.append(self.unmatched_qualifier)
        self.assertIsNone(
            self.wd_stuff.match_claim(
                self.claims, self.qualifiers, self.force))

    def test_match_claim_one_qualified_claim_forced_none_selected(self):
        # 6.3 If only one claim and it is qualified None is selected
        # even if forced
        self.claims.append(self.one_qual_no_ref)
        self.qualifiers.append(self.unmatched_qualifier)
        self.force = True
        self.assertIsNone(
            self.wd_stuff.match_claim(
                self.claims, self.qualifiers, self.force))
