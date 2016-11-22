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

    """Test hasClaim()."""

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
        function = 'wikidataStuff.WikidataStuff.WikidataStuff.compareWbTimeClaim'

        with mock.patch(function, autospec=True) as mock_compare_WbTime:
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


class TestHasQualifier(BaseTest):

    """Test hasQualifier()."""

    # test for test_qual = None

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

    """Test hasAllQualifiers()."""

    def setUp(self):
        super(TestHasAllQualifiers, self).setUp()
        self.claim = self.wd_page.claims['P174'][4]  # 2 quals
        self.quals = []

    def test_has_all_qualifiers_none(self):
        with self.assertRaises(TypeError):
            self.wd_stuff.hasAllQualifiers(None, self.claim)

    def test_has_all_qualifiers_empty(self):
        self.claim = self.wd_page.claims['P174'][2]  # no quals
        expected = (True, True)
        self.assertEquals(
            self.wd_stuff.hasAllQualifiers(self.quals, self.claim),
            expected)

    def test_has_all_qualifiers_has_all(self):
        self.quals.append(
            WD.WikidataStuff.Qualifier('P174', 'A qualifier'))
        self.quals.append(
            WD.WikidataStuff.Qualifier('P664', 'Another qualifier'))
        expected = (True, True)
        self.assertEquals(
            self.wd_stuff.hasAllQualifiers(self.quals, self.claim),
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
            self.wd_stuff.hasAllQualifiers(self.quals, self.claim),
            expected)

    def test_has_all_qualifiers_has_all_plus_one(self):
        self.quals.append(
            WD.WikidataStuff.Qualifier('P174', 'A qualifier'))
        expected = (False, True)
        self.assertEquals(
            self.wd_stuff.hasAllQualifiers(self.quals, self.claim),
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
        self.prop = 'P174'  # an unused property of type string
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

    # should fail once proper comparisons are done
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

    # should fail once proper comparisons are done
    def test_add_new_claim_old_property_old_value_with_different_quals(self):
        self.prop = 'P174'
        self.value = 'A string entry with a qualifier'
        statement = WD.WikidataStuff.Statement(self.value)
        statement.addQualifier(self.quals[0]).addQualifier(self.quals[1])
        expected_claim = 'Q27399$50b7cccb-4e9d-6f5d-d9c9-6b85d771c2d4'
        self.wd_stuff.addNewClaim(self.prop, statement, self.wd_page, self.ref)

        self.mock_add_claim.assert_not_called()
        self.assertEquals(self.mock_add_qualifier.call_count, 2)
        self.mock_add_reference.assert_called_once()
        self.assertEquals(
            self.mock_add_reference.call_args[0][1].toJSON()['id'],
            expected_claim)

    # should change once proper comparisons are done
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

    # test_add_new_claim_old_property_old_value_without_quals_and_ref
    # test_add_new_claim_old_property_old_value_with_different_quals_and_ref
    # test_add_new_claim_old_property_old_value_with_same_quals_and_ref
    # statements with quals and target with source
    # statement.force

    @unittest.expectedFailure  # issue #21 - sourcing wrong claim
    def test_add_new_modify_source_correct_qualified_claim(self):
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

    @unittest.expectedFailure  # issue #21 - adding new claim
    def test_add_new_modify_source_correct_qualified_claim_with_ref(self):
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

    def test_add_new_call_special_has_claim(self):
        value = 'somevalue'
        statement = WD.WikidataStuff.Statement(value, special=True)
        function = 'wikidataStuff.WikidataStuff.WikidataStuff.hasSpecialClaim'

        with mock.patch(function, autospec=True) as mock_has_special_claim:
            self.wd_stuff.addNewClaim(
                self.prop, statement, self.wd_page, self.ref)
            mock_has_special_claim.assert_called_once_with(
                self.wd_stuff, self.prop, value, self.wd_page)
