#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Unit tests for WikidataStuff."""
from __future__ import unicode_literals
import json
import mock
import os
import unittest

import pywikibot

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

        # silence output
        output_patcher = mock.patch(
            'wikidataStuff.WikidataStuff.pywikibot.output')
        self.mock_output = output_patcher.start()
        self.addCleanup(output_patcher.stop)


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

    """Test has_claim()."""

    def test_has_claim_prop_not_present(self):
        prop = 'P0'
        itis = 'A string'
        self.assertEquals(
            self.wd_stuff.has_claim(prop, itis, self.wd_page),
            [])

    def test_has_claim_prop_but_not_value(self):
        prop = 'P174'
        itis = 'An unknown string'
        self.assertEquals(
            self.wd_stuff.has_claim(prop, itis, self.wd_page),
            [])

    def test_has_claim_simple_match(self):
        prop = 'P174'
        itis = 'A string'
        expected = 'Q27399$3f62d521-4efe-e8de-8f2d-0d8a10e024cf'

        hits = self.wd_stuff.has_claim(prop, itis, self.wd_page)
        self.assertEquals(len(hits), 1)
        self.assertEquals(
            hits[0].toJSON()['id'],
            expected)

    def test_has_claim_match_independent_of_reference(self):
        prop = 'P174'
        itis = 'A string with a reference'
        expected = 'Q27399$ef9f73ce-4cd5-13e5-a0bf-4ad835d8f9c3'

        hits = self.wd_stuff.has_claim(prop, itis, self.wd_page)
        self.assertEquals(len(hits), 1)
        self.assertEquals(
            hits[0].toJSON()['id'],
            expected)

    def test_has_claim_match_item_type(self):
        prop = 'P84'
        itis = pywikibot.ItemPage(self.repo, 'Q1341')
        expected = 'Q27399$58a0a8bc-46e4-3dc6-16fe-e7c364103c9b'

        hits = self.wd_stuff.has_claim(prop, itis, self.wd_page)
        self.assertEquals(len(hits), 1)
        self.assertEquals(
            hits[0].toJSON()['id'],
            expected)

    def test_has_claim_match_WbTime_type(self):
        prop = 'P74'
        itis = pywikibot.WbTime(year=2016, month=11, day=22, site=self.repo)
        function = 'wikidataStuff.WikidataStuff.WikidataStuff.compareWbTimeClaim'

        with mock.patch(function, autospec=True) as mock_compare_WbTime:
            self.wd_stuff.has_claim(prop, itis, self.wd_page)
            mock_compare_WbTime.assert_called_once_with(
                self.wd_stuff, itis, itis)

    def test_has_claim_match_independent_of_qualifier(self):
        prop = 'P174'
        itis = 'A string entry with a qualifier'
        expected = 'Q27399$50b7cccb-4e9d-6f5d-d9c9-6b85d771c2d4'

        hits = self.wd_stuff.has_claim(prop, itis, self.wd_page)
        self.assertEquals(len(hits), 1)
        self.assertEquals(
            hits[0].toJSON()['id'],
            expected)

    def test_has_claim_match_multiple(self):
        prop = 'P664'
        itis = 'Duplicate_string'
        expected_1 = 'Q27399$221e4451-46d7-8c4a-53cb-47a4e0d09660'
        expected_2 = 'Q27399$a9b83de1-49d7-d033-939d-f430a232ffd0'

        hits = self.wd_stuff.has_claim(prop, itis, self.wd_page)
        self.assertEquals(len(hits), 2)
        self.assertEquals(
            hits[0].toJSON()['id'],
            expected_1)
        self.assertEquals(
            hits[1].toJSON()['id'],
            expected_2)


class TestHasQualifier(BaseTest):

    """Test hasQualifier()."""

    def test_has_qualifier_no_qualifier(self):
        claim = self.wd_page.claims['P664'][0]
        test_qual = WD.WikidataStuff.Qualifier('P174', 'qualifier')
        self.assertFalse(self.wd_stuff.hasQualifier(test_qual, claim))

    def test_has_qualifier_different_qualifier_prop(self):
        claim = self.wd_page.claims['P664'][1]
        test_qual = WD.WikidataStuff.Qualifier('P0', 'qualifier')
        self.assertFalse(self.wd_stuff.hasQualifier(test_qual, claim))

    def test_has_qualifier_different_qualifier_value(self):
        claim = self.wd_page.claims['P664'][1]
        test_qual = WD.WikidataStuff.Qualifier('P174', 'Another qualifier')
        self.assertFalse(self.wd_stuff.hasQualifier(test_qual, claim))

    def test_has_qualifier_same_qualifier(self):
        claim = self.wd_page.claims['P664'][1]
        test_qual = WD.WikidataStuff.Qualifier('P174', 'qualifier')
        self.assertTrue(self.wd_stuff.hasQualifier(test_qual, claim))

    def test_has_qualifier_multiple_qualifiers_different_prop(self):
        claim = self.wd_page.claims['P174'][4]
        expect_qual_1 = WD.WikidataStuff.Qualifier('P174', 'A qualifier')
        expect_qual_2 = WD.WikidataStuff.Qualifier('P664', 'Another qualifier')
        unexpected_qual = WD.WikidataStuff.Qualifier('P174', 'Not a qualifier')
        self.assertTrue(self.wd_stuff.hasQualifier(expect_qual_1, claim))
        self.assertTrue(self.wd_stuff.hasQualifier(expect_qual_2, claim))
        self.assertFalse(self.wd_stuff.hasQualifier(unexpected_qual, claim))

    def test_has_qualifier_multiple_qualifiers_same_prop(self):
        claim = self.wd_page.claims['P174'][5]
        expect_qual_1 = WD.WikidataStuff.Qualifier('P174', 'A qualifier')
        expect_qual_2 = WD.WikidataStuff.Qualifier('P174', 'Another qualifier')
        unexpected_qual = WD.WikidataStuff.Qualifier('P174', 'Not a qualifier')
        self.assertTrue(self.wd_stuff.hasQualifier(expect_qual_1, claim))
        self.assertTrue(self.wd_stuff.hasQualifier(expect_qual_2, claim))
        self.assertFalse(self.wd_stuff.hasQualifier(unexpected_qual, claim))


class TestHasAllQualifiers(BaseTest):

    """Test has_all_qualifiers()."""

    def setUp(self):
        super(TestHasAllQualifiers, self).setUp()
        self.claim = self.wd_page.claims['P174'][4]  # 2 quals
        self.quals = []

    def test_has_all_qualifiers_none(self):
        with self.assertRaises(TypeError):
            self.wd_stuff.has_all_qualifiers(None, self.claim)

    def test_has_all_qualifiers_empty(self):
        self.claim = self.wd_page.claims['P174'][2]  # no quals
        expected = (True, True)
        self.assertEquals(
            self.wd_stuff.has_all_qualifiers(self.quals, self.claim),
            expected)

    def test_has_all_qualifiers_has_all(self):
        self.quals.append(
            WD.WikidataStuff.Qualifier('P174', 'A qualifier'))
        self.quals.append(
            WD.WikidataStuff.Qualifier('P664', 'Another qualifier'))
        expected = (True, True)
        self.assertEquals(
            self.wd_stuff.has_all_qualifiers(self.quals, self.claim),
            expected)

    def test_has_all_qualifiers_has_all_but_one(self):
        self.quals.append(
            WD.WikidataStuff.Qualifier('P174', 'A qualifier'))
        self.quals.append(
            WD.WikidataStuff.Qualifier('P664', 'Another qualifier'))
        self.quals.append(
            WD.WikidataStuff.Qualifier('P174', 'Not a qualifier'))
        expected = (False, False)
        self.assertEquals(
            self.wd_stuff.has_all_qualifiers(self.quals, self.claim),
            expected)

    def test_has_all_qualifiers_has_all_plus_one(self):
        self.quals.append(
            WD.WikidataStuff.Qualifier('P174', 'A qualifier'))
        expected = (False, True)
        self.assertEquals(
            self.wd_stuff.has_all_qualifiers(self.quals, self.claim),
            expected)


class TestAddNewClaim(BaseTest):

    """Test addNewClaim()."""

    def setUp(self):
        super(TestAddNewClaim, self).setUp()

        # mock all writing calls
        add_qualifier_patcher = mock.patch(
            'wikidataStuff.WikidataStuff.WikidataStuff.addQualifier')
        add_reference_patcher = mock.patch(
            'wikidataStuff.WikidataStuff.WikidataStuff.addReference')
        add_claim_patcher = mock.patch(
            'wikidataStuff.WikidataStuff.pywikibot.ItemPage.addClaim')
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
        self.quals = [
            WD.WikidataStuff.Qualifier('P174', 'A qualifier'),
            WD.WikidataStuff.Qualifier('P664', 'Another qualifier')
        ]

    def test_add_new_claim_new_property(self):
        statement = WD.WikidataStuff.Statement(self.value)
        self.wd_stuff.addNewClaim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_called_once()
        self.mock_add_qualifier.assert_not_called()
        self.mock_add_reference.assert_called_once()

    def test_add_new_claim_old_property_new_value(self):
        self.prop = 'P174'
        statement = WD.WikidataStuff.Statement(self.value)
        self.wd_stuff.addNewClaim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_called_once()
        self.mock_add_qualifier.assert_not_called()
        self.mock_add_reference.assert_called_once()

    def test_add_new_claim_old_property_old_value(self):
        self.prop = 'P174'
        self.value = 'A string'
        statement = WD.WikidataStuff.Statement(self.value)
        expected_claim = 'Q27399$3f62d521-4efe-e8de-8f2d-0d8a10e024cf'
        self.wd_stuff.addNewClaim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_not_called()
        self.mock_add_qualifier.assert_not_called()
        self.mock_add_reference.assert_called_once()

        # ensure the right claim was sourced
        self.assertEquals(
            self.mock_add_reference.call_args[0][1].toJSON()['id'],
            expected_claim)

    def test_add_new_claim_new_property_with_quals(self):
        statement = WD.WikidataStuff.Statement(self.value)
        statement.addQualifier(self.quals[0]).addQualifier(self.quals[1])
        self.wd_stuff.addNewClaim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_called_once()
        self.assertEquals(self.mock_add_qualifier.call_count, 2)
        self.mock_add_reference.assert_called_once()

    def test_add_new_claim_old_property_new_value_with_quals(self):
        self.prop = 'P174'
        statement = WD.WikidataStuff.Statement(self.value)
        statement.addQualifier(self.quals[0]).addQualifier(self.quals[1])
        self.wd_stuff.addNewClaim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_called_once()
        self.assertEquals(self.mock_add_qualifier.call_count, 2)
        self.mock_add_reference.assert_called_once()

    def test_add_new_claim_old_property_old_value_without_quals(self):
        self.prop = 'P174'
        self.value = 'A string'
        statement = WD.WikidataStuff.Statement(self.value)
        statement.addQualifier(self.quals[0]).addQualifier(self.quals[1])
        expected_claim = 'Q27399$3f62d521-4efe-e8de-8f2d-0d8a10e024cf'
        self.wd_stuff.addNewClaim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_not_called()
        self.assertEquals(self.mock_add_qualifier.call_count, 2)
        self.mock_add_reference.assert_called_once()
        self.assertEquals(
            self.mock_add_reference.call_args[0][1].toJSON()['id'],
            expected_claim)

    def test_add_new_claim_old_property_old_value_with_different_quals(self):
        self.prop = 'P174'
        self.value = 'A string entry with a qualifier'
        statement = WD.WikidataStuff.Statement(self.value)
        statement.addQualifier(self.quals[0]).addQualifier(self.quals[1])
        self.wd_stuff.addNewClaim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_called_once()
        self.assertEquals(self.mock_add_qualifier.call_count, 2)
        self.mock_add_reference.assert_called_once()

    def test_add_new_claim_old_property_old_value_with_same_quals(self):
        self.prop = 'P174'
        self.value = 'A string entry with many qualifiers'
        statement = WD.WikidataStuff.Statement(self.value)
        statement.addQualifier(self.quals[0]).addQualifier(self.quals[1])
        expected_claim = 'Q27399$b48a2630-4fbb-932d-4f01-eefcf1e73f59'
        self.wd_stuff.addNewClaim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_not_called()
        self.assertEquals(self.mock_add_qualifier.call_count, 2)
        self.mock_add_reference.assert_called_once()
        self.assertEquals(
            self.mock_add_reference.call_args[0][1].toJSON()['id'],
            expected_claim)

    def test_add_new_claim_edit_correct_qualified_claim(self):
        self.prop = 'P664'
        self.value = 'Duplicate_string'
        statement = WD.WikidataStuff.Statement(self.value)
        statement.addQualifier(
            WD.WikidataStuff.Qualifier('P174', 'qualifier'))
        expected_claim = 'Q27399$a9b83de1-49d7-d033-939d-f430a232ffd0'
        self.wd_stuff.addNewClaim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_not_called()
        self.mock_add_claim.mock_add_qualifier()
        self.mock_add_reference.assert_called_once()
        self.assertEquals(
            self.mock_add_reference.call_args[0][1].toJSON()['id'],
            expected_claim)

    def test_add_new_claim_edit_correct_qualified_claim_with_ref(self):
        self.prop = 'P664'
        self.value = 'Duplicate_string_with_ref'
        statement = WD.WikidataStuff.Statement(self.value)
        statement.addQualifier(
            WD.WikidataStuff.Qualifier('P174', 'qualifier'))
        expected_claim = 'Q27399$e63f47a3-45ea-e2fc-1363-8f6062205084'
        self.wd_stuff.addNewClaim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_not_called()
        self.mock_add_claim.mock_add_qualifier()
        self.mock_add_reference.assert_called_once()
        self.assertEquals(
            self.mock_add_reference.call_args[0][1].toJSON()['id'],
            expected_claim)

    def test_add_new_claim_call_special_has_claim(self):
        value = 'somevalue'
        statement = WD.WikidataStuff.Statement(value, special=True)
        function = 'wikidataStuff.WikidataStuff.WikidataStuff.has_special_claim'

        with mock.patch(function, autospec=True) as mock_has_special_claim:
            self.wd_stuff.addNewClaim(
                self.prop, statement, self.wd_page, self.ref)
            mock_has_special_claim.assert_called_once_with(
                self.wd_stuff, self.prop, value, self.wd_page)

    def test_add_new_claim_raise_error_on_bad_ref(self):
        statement = WD.WikidataStuff.Statement(self.value)
        with self.assertRaises(pywikibot.Error) as e:
            self.wd_stuff.addNewClaim(
                self.prop, statement, self.wd_page, 'Not a ref')
        self.assertEquals(str(e.exception),
                          'The provided reference was not a '
                          'Reference object. Crashing')

    def test_add_new_claim_reraise_error_on_duplicate_matching_claim(self):
        self.prop = 'P84'
        self.value = pywikibot.ItemPage(self.repo, 'Q505')
        statement = WD.WikidataStuff.Statement(self.value)
        with self.assertRaises(pywikibot.Error) as e:
            self.wd_stuff.addNewClaim(
                self.prop, statement, self.wd_page, self.ref)
        self.assertEquals(str(e.exception),
                          'Problem adding P84 claim to [[wikidata:test:-1]]: '
                          'Multiple identical claims')


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
        self.matched_qualifier = self.wd_stuff.Qualifier('P174', 'A qualifier')
        self.unmatched_qualifier = self.wd_stuff.Qualifier('P174', 'Unmatched')

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
        self.assertEquals(str(e.exception), 'Multiple identical claims')

    def test_match_claim_empty_qualifier_exact(self):
        # 2. if no qualifier select the unqualified
        self.claims.append(self.one_qual_no_ref)
        self.claims.append(self.no_qual_no_ref)
        expected_claim = self.no_qual_no_ref
        self.assertEquals(
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
        self.assertEquals(
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
        self.assertEquals(str(e.exception), 'Multiple semi-identical claims')

    def test_match_claim_one_qualifier_close(self):
        # 4. if qualified select the closest match
        # (contains at least that qualifier)
        self.claims.append(self.no_qual_no_ref)
        self.claims.append(self.two_qual_no_ref)
        self.qualifiers.append(self.matched_qualifier)
        expected_claim = self.two_qual_no_ref
        self.assertEquals(
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
        self.assertEquals(
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
        self.assertEquals(
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
