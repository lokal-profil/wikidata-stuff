# -*- coding: utf-8  -*-
"""Unit tests for PreviewItem."""
from __future__ import unicode_literals

import unittest
from mock import mock
from collections import OrderedDict

import pywikibot

from wikidataStuff.PreviewItem import PreviewItem
from wikidataStuff.WikidataStuff import WikidataStuff as WdS


class BasicFormatMocker(unittest.TestCase):

    """Patch some basic formatters and provide a repo."""

    def setUp(self):
        self.repo = pywikibot.Site('test', 'wikidata')

        # patch bold
        def bold_side_effect(val):
            return 'bold_{}'.format(val)

        bold_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.make_text_bold')
        self.mock_bold = bold_patcher.start()
        self.mock_bold.side_effect = bold_side_effect

        # patch italics
        def italics_side_effect(val):
            return 'italics_{}'.format(val)

        italics_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.make_text_italics')
        self.mock_italics = italics_patcher.start()
        self.mock_italics.side_effect = italics_side_effect

        self.addCleanup(bold_patcher.stop)
        self.addCleanup(italics_patcher.stop)

        # patch wikidata_template
        wd_template_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.make_wikidata_template')
        self.mock_wd_template = wd_template_patcher.start()
        self.mock_wd_template.side_effect = ['wd_template_{}'.format(i)
                                             for i in range(1, 5)]
        self.addCleanup(wd_template_patcher.stop)


class TestPreviewItemBase(BasicFormatMocker):

    """Shared setup for all instance method tests."""

    def setUp(self):
        super(TestPreviewItemBase, self).setUp()
        self.preview_item = PreviewItem(
            labels={}, descriptions={}, protoclaims={}, item=None, ref=None)


class TestMakeWikidataTemplate(unittest.TestCase):

    """Test the make_wikidata_template method."""

    def setUp(self):
        self.repo = pywikibot.Site('test', 'wikidata')

    def test_make_wikidata_template_empty(self):
        with self.assertRaises(ValueError) as cm:
            PreviewItem.make_wikidata_template('')
        self.assertEqual(
            str(cm.exception),
            'Sorry only items and properties are supported, not whatever '
            '"" is.'
        )

    def test_make_wikidata_template_none(self):
        with self.assertRaises(ValueError) as cm:
            PreviewItem.make_wikidata_template(None)
        self.assertEqual(
            str(cm.exception),
            'Sorry only items and properties are supported, not whatever '
            '"None" is.'
        )

    def test_make_wikidata_template_qid(self):
        expected = '{{Q|Q123}}'
        self.assertEqual(
            PreviewItem.make_wikidata_template('Q123'),
            expected
        )

    def test_make_wikidata_template_pid(self):
        expected = '{{P|P123}}'
        self.assertEqual(
            PreviewItem.make_wikidata_template('P123'),
            expected
        )

    def test_make_wikidata_template_item_page(self):
        expected = '{{Q|Q321}}'
        item = pywikibot.ItemPage(self.repo, 'Q321')
        self.assertEqual(
            PreviewItem.make_wikidata_template(item),
            expected
        )

    def test_make_wikidata_template_property_page(self):
        expected = '{{P|P321}}'
        prop = pywikibot.PropertyPage(self.repo, 'P321')
        self.assertEqual(
            PreviewItem.make_wikidata_template(prop),
            expected
        )

    def test_make_wikidata_template_bad_id_fail(self):
        with self.assertRaises(ValueError) as cm:
            PreviewItem.make_wikidata_template('dummy')
        self.assertEqual(
            str(cm.exception),
            'Sorry only items and properties are supported, not whatever '
            '"dummy" is.'
        )

    def test_make_wikidata_template_special_novalue(self):
        expected = "{{Q'|no value}}"
        self.assertEqual(
            PreviewItem.make_wikidata_template('novalue', special=True),
            expected
        )

    def test_make_wikidata_template_special_somevalue(self):
        expected = "{{Q'|some value}}"
        self.assertEqual(
            PreviewItem.make_wikidata_template('somevalue', special=True),
            expected
        )

    def test_make_wikidata_template_special_fail(self):
        with self.assertRaises(ValueError) as cm:
            PreviewItem.make_wikidata_template('dummy', special=True)
        self.assertEqual(
            str(cm.exception),
            'Sorry but "dummy" is not a recognized special value/snaktype.'
        )


class TestFormatItem(TestPreviewItemBase):

    """Test the format_item method."""

    def test_format_item_none(self):
        self.preview_item.item = None
        self.assertEqual(
            self.preview_item.format_item(),
            '–'
        )

    def test_format_item_with_item(self):
        self.preview_item.item = 'anything'
        self.preview_item.format_item()
        self.mock_wd_template.assert_called_once_with('anything')


class TestFormatDescriptions(TestPreviewItemBase):

    """Test the format_descriptions method."""

    def test_format_descriptions_empty(self):
        self.preview_item.desc_dict = {}
        self.assertEqual(self.preview_item.format_descriptions(), '')

    def test_make_wikidata_template_with_data(self):
        descriptions = {
            'en': 'en_desc',
            'sv': 'sv_desc'
        }
        self.preview_item.desc_dict = OrderedDict(
            sorted(descriptions.items(), key=lambda t: t[0]))
        expected = (
            '* bold_en: en_desc\n'
            '* bold_sv: sv_desc\n'
        )
        self.assertEqual(self.preview_item.format_descriptions(), expected)
        self.mock_bold.assert_has_calls([mock.call('en'), mock.call('sv')])


class TestFormatLabels(TestPreviewItemBase):

    """Test the format_labels method."""

    def test_format_labels_empty(self):
        self.preview_item.labels_dict = {}
        self.assertEqual(self.preview_item.format_labels(), '')

    def test_format_labels_with_multiple_langs(self):
        labels = {
            'en': ['en_label'],
            'sv': ['sv_label']
        }
        self.preview_item.labels_dict = OrderedDict(
            sorted(labels.items(), key=lambda t: t[0]))
        expected = (
            '* bold_en: italics_en_label\n'
            '* bold_sv: italics_sv_label\n'
        )
        self.assertEqual(self.preview_item.format_labels(), expected)
        self.mock_bold.assert_has_calls([mock.call('en'), mock.call('sv')])

    def test_format_labels_with_multiple_names(self):
        self.preview_item.labels_dict = {
            'en': ['en_label', 'en_alias_1', 'en_alias_2']
        }
        expected = (
            '* bold_en: italics_en_label | en_alias_1 | en_alias_2\n'
        )
        self.assertEqual(self.preview_item.format_labels(), expected)
        self.mock_bold.assert_called_once_with('en')
        self.mock_italics.assert_called_once_with('en_label')


class TestFormatItis(BasicFormatMocker):

    """Test the format_itis method."""

    def setUp(self):
        super(TestFormatItis, self).setUp()
        timestring_patcher = mock.patch(
            'wikidataStuff.PreviewItem.pywikibot.WbTime.toTimestr')
        self.mock_format_timestring = timestring_patcher.start()
        self.mock_format_timestring.return_value = 'formatted_WbTime'
        self.addCleanup(timestring_patcher.stop)

    def test_format_itis_none(self):
        itis = None
        expected = 'None'
        self.assertEqual(PreviewItem.format_itis(itis), expected)
        self.mock_wd_template.assert_not_called()
        self.mock_format_timestring.assert_not_called()

    def test_format_itis_item_page(self):
        itis = pywikibot.ItemPage(self.repo, 'Q123')
        expected = 'wd_template_1'
        self.assertEqual(PreviewItem.format_itis(itis), expected)
        self.mock_wd_template.assert_called_once_with(itis)
        self.mock_format_timestring.assert_not_called()

    def test_format_itis_quantity(self):
        itis = pywikibot.WbQuantity(123, site=self.repo)
        expected = '123'
        self.assertEqual(PreviewItem.format_itis(itis), expected)
        self.mock_wd_template.assert_not_called()
        self.mock_format_timestring.assert_not_called()

    def test_format_itis_quantity_unit(self):
        unit = pywikibot.ItemPage(self.repo, 'Q123')
        itis = pywikibot.WbQuantity(123, unit=unit, site=self.repo)
        expected = '123 wd_template_1'
        self.assertEqual(PreviewItem.format_itis(itis), expected)
        self.mock_wd_template.assert_called_once_with(unit)
        self.mock_format_timestring.assert_not_called()

    def test_format_itis_time(self):
        itis = pywikibot.WbTime(year=1999)
        expected = 'formatted_WbTime'
        self.assertEqual(PreviewItem.format_itis(itis), expected)
        self.mock_wd_template.assert_not_called()
        self.mock_format_timestring.assert_called_once()

    def test_format_itis_other(self):
        itis = [1, 2, 3]
        expected = '[1, 2, 3]'
        self.assertEqual(PreviewItem.format_itis(itis), expected)
        self.mock_wd_template.assert_not_called()
        self.mock_format_timestring.assert_not_called()

    def test_format_itis_special(self):
        itis = 'dummy'
        expected = 'wd_template_1'
        self.assertEqual(
            PreviewItem.format_itis(itis, special=True),
            expected
        )
        self.mock_wd_template.assert_called_once_with(itis, special=True)
        self.mock_format_timestring.assert_not_called()

    def test_format_itis_statement_item(self):
        item = pywikibot.ItemPage(self.repo, 'Q123')
        itis = WdS.Statement(item)
        expected = 'wd_template_1'
        self.assertEqual(
            PreviewItem.format_itis(itis),
            expected
        )
        self.mock_wd_template.assert_called_once_with(item)
        self.mock_format_timestring.assert_not_called()

    def test_format_itis_statement_other(self):
        itis = WdS.Statement('dummy')
        expected = 'dummy'
        self.assertEqual(
            PreviewItem.format_itis(itis),
            expected
        )
        self.mock_wd_template.assert_not_called()
        self.mock_format_timestring.assert_not_called()

    def test_format_itis_statement_detect_special(self):
        itis = WdS.Statement('novalue', special=True)
        expected = 'wd_template_1'
        self.assertEqual(
            PreviewItem.format_itis(itis),
            expected
        )
        self.mock_wd_template.assert_called_once_with('novalue', special=True)
        self.mock_format_timestring.assert_not_called()


class TestFormatClaim(BasicFormatMocker):

    """Test the format_claim method."""

    def setUp(self):
        super(TestFormatClaim, self).setUp()
        itis_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.format_itis')
        self.mock_format_itis = itis_patcher.start()
        self.mock_format_itis.return_value = 'formatted_itis'
        self.addCleanup(itis_patcher.stop)

    def test_format_claim_basic(self):
        claim = pywikibot.Claim(self.repo, 'P123')
        claim.setTarget('1')
        expected = 'wd_template_1: formatted_itis'
        self.assertEqual(PreviewItem.format_claim(claim), expected)
        self.mock_wd_template.assert_called_once_with('P123')
        self.mock_format_itis.assert_called_once_with('1', False)

    def test_format_claim_special(self):
        claim = pywikibot.Claim(self.repo, 'P123')
        claim.setSnakType('novalue')
        expected = 'wd_template_1: formatted_itis'
        self.assertEqual(PreviewItem.format_claim(claim), expected)
        self.mock_wd_template.assert_called_once_with('P123')
        self.mock_format_itis.assert_called_once_with('novalue', True)


class TestFormatReference(BasicFormatMocker):

    """Test the format_reference method."""

    def setUp(self):
        super(TestFormatReference, self).setUp()
        claim_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.format_claim')
        self.mock_format_claim = claim_patcher.start()
        self.mock_format_claim.side_effect = ['formatted_claim_{}'.format(i)
                                              for i in range(1, 5)]
        self.addCleanup(claim_patcher.stop)

        self.claim_1 = pywikibot.Claim(self.repo, 'P123')
        self.claim_1.setTarget('1')
        self.claim_2 = pywikibot.Claim(self.repo, 'P123')
        self.claim_2.setTarget('2')
        self.claim_3 = pywikibot.Claim(self.repo, 'P123')
        self.claim_3.setTarget('3')
        self.claim_4 = pywikibot.Claim(self.repo, 'P123')
        self.claim_4.setTarget('4')

    def test_format_reference_basic(self):
        ref = WdS.Reference(
            source_test=[self.claim_1, self.claim_2],
            source_notest=[self.claim_3, self.claim_4]
        )
        expected = (
            ':italics_tested:\n'
            ':*formatted_claim_1\n'
            ':*formatted_claim_2\n'
            ':italics_not tested:\n'
            ':*formatted_claim_3\n'
            ':*formatted_claim_4\n'
        )
        self.assertEqual(PreviewItem.format_reference(ref), expected)

        self.mock_format_claim.assert_has_calls([
            mock.call(self.claim_1),
            mock.call(self.claim_2),
            mock.call(self.claim_3),
            mock.call(self.claim_4)
        ])
        self.mock_italics.assert_has_calls([
            mock.call('tested'),
            mock.call('not tested')
        ])

    def test_format_reference_no_test(self):
        ref = WdS.Reference(source_notest=self.claim_1)
        expected = (
            ':italics_not tested:\n'
            ':*formatted_claim_1\n'
        )
        self.assertEqual(PreviewItem.format_reference(ref), expected)

        self.mock_format_claim.assert_called_once_with(self.claim_1)
        self.mock_italics.assert_called_once_with('not tested')

    def test_format_reference_no_notest(self):
        ref = WdS.Reference(source_test=self.claim_1)
        expected = (
            ':italics_tested:\n'
            ':*formatted_claim_1\n'
        )
        self.assertEqual(PreviewItem.format_reference(ref), expected)

        self.mock_format_claim.assert_called_once_with(self.claim_1)
        self.mock_italics.assert_called_once_with('tested')


class TestFormatQual(BasicFormatMocker):

    """Test the format_qual method."""

    def setUp(self):
        super(TestFormatQual, self).setUp()
        itis_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.format_itis')
        self.mock_format_itis = itis_patcher.start()
        self.mock_format_itis.return_value = 'formatted_itis'
        self.addCleanup(itis_patcher.stop)

    def test_format_qual_basic(self):
        qual = WdS.Qualifier('P123', 'val')
        self.assertEqual(
            PreviewItem.format_qual(qual), 'wd_template_1: formatted_itis')
        self.mock_wd_template.assert_called_once_with('P123')
        self.mock_format_itis.assert_called_once_with('val')


class TestFormatProtoclaims(TestPreviewItemBase):

    """Test the format_protoclaims method."""

    def setUp(self):
        super(TestFormatProtoclaims, self).setUp()
        itis_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.format_itis')
        self.mock_format_itis = itis_patcher.start()
        self.mock_format_itis.side_effect = ['formatted_itis_{}'.format(i)
                                             for i in range(1, 5)]
        self.addCleanup(itis_patcher.stop)

        qual_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.format_qual')
        self.mock_format_qual = qual_patcher.start()
        self.mock_format_qual.side_effect = ['formatted_qual_{}'.format(i)
                                             for i in range(1, 5)]
        self.addCleanup(qual_patcher.stop)

        ref_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.format_reference')
        self.mock_format_ref = ref_patcher.start()
        self.mock_format_ref.side_effect = ['formatted_reference_{}'.format(i)
                                            for i in range(1, 5)]
        self.addCleanup(ref_patcher.stop)

    def test_format_protoclaims_no_protoclaims(self):
        self.preview_item.protoclaims = {}
        expected = (
            "{| class='wikitable'\n"
            "|-\n"
            "! Property\n"
            "! Value\n"
            "! Qualifiers\n"
            "|}"
        )
        self.assertEqual(self.preview_item.format_protoclaims(), expected)
        self.mock_wd_template.assert_not_called()
        self.mock_format_itis.assert_not_called()
        self.mock_format_qual.assert_not_called()
        self.mock_format_ref.assert_not_called()

    def test_format_protoclaims_no_single_none_claim(self):
        self.preview_item.protoclaims = {'P123': None}
        expected = (
            "{| class='wikitable'\n"
            "|-\n"
            "! Property\n"
            "! Value\n"
            "! Qualifiers\n"
            "|}"
        )
        self.assertEqual(self.preview_item.format_protoclaims(), expected)
        self.mock_wd_template.assert_not_called()
        self.mock_format_itis.assert_not_called()
        self.mock_format_qual.assert_not_called()
        self.mock_format_ref.assert_not_called()

    def test_format_protoclaims_single(self):
        itis = WdS.Statement('dummy')
        self.preview_item.protoclaims = {'P123': itis}
        expected = (
            "{| class='wikitable'\n"
            "|-\n"
            "! Property\n"
            "! Value\n"
            "! Qualifiers\n"
            '|-\n'
            '| wd_template_1 \n'
            '| formatted_itis_1 \n'
            '|  \n'
            "|}"
        )
        self.assertEqual(self.preview_item.format_protoclaims(), expected)
        self.mock_wd_template.assert_called_once_with('P123')
        self.mock_format_itis.assert_called_once_with(itis)
        self.mock_format_qual.assert_not_called()
        self.mock_format_ref.assert_not_called()

    def test_format_protoclaims_single_with_qual(self):
        itis = WdS.Statement('dummy')
        qual = WdS.Qualifier('P321', 'qual_dummy')
        itis._quals.add(qual)
        self.preview_item.protoclaims = {'P123': itis}
        expected = (
            "{| class='wikitable'\n"
            "|-\n"
            "! Property\n"
            "! Value\n"
            "! Qualifiers\n"
            '|-\n'
            '| wd_template_1 \n'
            '| formatted_itis_1 \n'
            '| formatted_qual_1 \n'
            "|}"
        )
        self.assertEqual(self.preview_item.format_protoclaims(), expected)
        self.mock_wd_template.assert_called_once_with('P123')
        self.mock_format_itis.assert_called_once_with(itis)
        self.mock_format_qual.assert_called_once_with(qual)
        self.mock_format_ref.assert_not_called()

    def test_format_protoclaims_single_with_multiple_qual(self):
        itis = WdS.Statement('dummy')
        qual_1 = WdS.Qualifier('P321', 'qual_dummy')
        qual_2 = WdS.Qualifier('P213', 'qual_dummy')
        itis._quals.add(qual_1)
        itis._quals.add(qual_2)
        self.preview_item.protoclaims = {'P123': itis}
        expected = (
            "{| class='wikitable'\n"
            "|-\n"
            "! Property\n"
            "! Value\n"
            "! Qualifiers\n"
            '|-\n'
            '| wd_template_1 \n'
            '| formatted_itis_1 \n'
            '| * formatted_qual_1 \n'
            '* formatted_qual_2 \n'
            "|}"
        )
        self.assertEqual(self.preview_item.format_protoclaims(), expected)
        self.mock_wd_template.assert_called_once_with('P123')
        self.mock_format_itis.assert_called_once_with(itis)
        self.mock_format_qual.assert_has_calls([
            mock.call(qual_1),
            mock.call(qual_2)],
            any_order=True
        )
        self.mock_format_ref.assert_not_called()

    def test_format_protoclaims_multple_same_prop(self):
        itis_1 = WdS.Statement('foo')
        itis_2 = WdS.Statement('bar')
        self.preview_item.protoclaims = {'P123': [itis_1, itis_2]}
        expected = (
            "{| class='wikitable'\n"
            "|-\n"
            "! Property\n"
            "! Value\n"
            "! Qualifiers\n"
            '|-\n'
            '| wd_template_1 \n'
            '| formatted_itis_1 \n'
            '|  \n'
            '|-\n'
            '| wd_template_1 \n'
            '| formatted_itis_2 \n'
            '|  \n'
            "|}"
        )
        self.assertEqual(self.preview_item.format_protoclaims(), expected)
        self.mock_wd_template.assert_called_once_with('P123')
        self.mock_format_itis.assert_has_calls([
            mock.call(itis_1),
            mock.call(itis_2)
        ])
        self.mock_format_qual.assert_not_called()
        self.mock_format_ref.assert_not_called()

    def test_format_protoclaims_multple_different_prop(self):
        itis_1 = WdS.Statement('foo')
        itis_2 = WdS.Statement('bar')
        protoclaims = {'P123': itis_1, 'P321': itis_2}
        self.preview_item.protoclaims = OrderedDict(
            sorted(protoclaims.items(), key=lambda t: int(t[0][1:])))
        expected = (
            "{| class='wikitable'\n"
            "|-\n"
            "! Property\n"
            "! Value\n"
            "! Qualifiers\n"
            '|-\n'
            '| wd_template_1 \n'
            '| formatted_itis_1 \n'
            '|  \n'
            '|-\n'
            '| wd_template_2 \n'
            '| formatted_itis_2 \n'
            '|  \n'
            "|}"
        )
        self.assertEqual(self.preview_item.format_protoclaims(), expected)
        self.mock_wd_template.assert_has_calls([
            mock.call('P123'),
            mock.call('P321')],
            any_order=True
        )
        self.mock_format_itis.assert_has_calls([
            mock.call(itis_1),
            mock.call(itis_2)],
            any_order=True
        )
        self.mock_format_qual.assert_not_called()
        self.mock_format_ref.assert_not_called()

    def test_format_protoclaims_ref_adds_column(self):
        claim_1 = pywikibot.Claim(self.repo, 'P123')
        claim_1.setTarget('1')
        ref_1 = WdS.Reference(claim_1)
        itis_1 = WdS.Statement('foo')
        itis_2 = WdS.Statement('bar').add_reference(ref_1)

        self.preview_item.protoclaims = {'P123': [itis_1, itis_2]}
        expected = (
            "{| class='wikitable'\n"
            "|-\n"
            "! Property\n"
            "! Value\n"
            "! Qualifiers\n"
            "! References\n"
            '|-\n'
            '| wd_template_1 \n'
            '| formatted_itis_1 \n'
            '|  \n'
            '|  \n'
            '|-\n'
            '| wd_template_1 \n'
            '| formatted_itis_2 \n'
            '|  \n'
            '| \nformatted_reference_1 \n'
            "|}"
        )
        self.assertEqual(self.preview_item.format_protoclaims(), expected)
        self.mock_wd_template.assert_called_once_with('P123')
        self.mock_format_itis.assert_has_calls([
            mock.call(itis_1),
            mock.call(itis_2)
        ])
        self.mock_format_qual.assert_not_called()
        self.mock_format_ref.assert_called_once_with(ref_1)

    def test_format_protoclaims_ref_adds_column_set_default(self):
        claim_1 = pywikibot.Claim(self.repo, 'P123')
        claim_1.setTarget('1')
        ref_1 = WdS.Reference(claim_1)
        claim_2 = pywikibot.Claim(self.repo, 'P123')
        claim_2.setTarget('2')
        ref_2 = WdS.Reference(claim_2)
        itis_1 = WdS.Statement('foo')
        itis_2 = WdS.Statement('bar').add_reference(ref_1)

        self.preview_item.ref = ref_2
        self.preview_item.protoclaims = {'P123': [itis_1, itis_2]}
        expected = (
            "{| class='wikitable'\n"
            "|-\n"
            "! Property\n"
            "! Value\n"
            "! Qualifiers\n"
            "! References\n"
            '|-\n'
            '| wd_template_1 \n'
            '| formatted_itis_1 \n'
            '|  \n'
            '| italics_default reference \n'
            '|-\n'
            '| wd_template_1 \n'
            '| formatted_itis_2 \n'
            '|  \n'
            '| \nformatted_reference_1 \n'
            "|}"
        )
        self.assertEqual(self.preview_item.format_protoclaims(), expected)
        self.mock_wd_template.assert_called_once_with('P123')
        self.mock_format_itis.assert_has_calls([
            mock.call(itis_1),
            mock.call(itis_2)
        ])
        self.mock_format_qual.assert_not_called()
        self.mock_format_ref.assert_called_once_with(ref_1)


class TestMakePreviewPage(TestPreviewItemBase):

    """Test the make_preview_page method."""

    def setUp(self):
        super(TestMakePreviewPage, self).setUp()
        label_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.format_labels')
        self.mock_format_label = label_patcher.start()
        self.mock_format_label.return_value = 'formatted_label'
        self.addCleanup(label_patcher.stop)

        description_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.format_descriptions')
        self.mock_format_description = description_patcher.start()
        self.mock_format_description.return_value = 'formatted_description'
        self.addCleanup(description_patcher.stop)

        item_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.format_item')
        self.mock_format_item = item_patcher.start()
        self.mock_format_item.return_value = 'formatted_item'
        self.addCleanup(item_patcher.stop)

        reference_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.format_reference')
        self.mock_format_reference = reference_patcher.start()
        self.mock_format_reference.return_value = 'formatted_reference'
        self.addCleanup(reference_patcher.stop)

        protoclaim_patcher = mock.patch(
            'wikidataStuff.PreviewItem.PreviewItem.format_protoclaims')
        self.mock_format_protoclaim = protoclaim_patcher.start()
        self.mock_format_protoclaim.return_value = 'formatted_protoclaim'
        self.addCleanup(protoclaim_patcher.stop)

    def test_make_preview_page_basic(self):
        self.preview_item.ref = 'refs'
        expected = (
            'bold_Labels | Aliases:\nformatted_label\n\n'
            'bold_Descriptions:\nformatted_description\n\n'
            'bold_Matching item: formatted_item\n\n'
            'bold_Default reference (same for all claims):\n'
            'formatted_reference\n\n'
            'bold_Claims:\nformatted_protoclaim\n\n'
        )
        self.assertEqual(self.preview_item.make_preview_page(), expected)
        self.mock_bold.assert_has_calls([
            mock.call('Labels | Aliases'),
            mock.call('Descriptions'),
            mock.call('Matching item'),
            mock.call('Default reference (same for all claims)'),
            mock.call('Claims')
        ])
        self.mock_format_label.assert_called_once()
        self.mock_format_description.assert_called_once()
        self.mock_format_item.assert_called_once()
        self.mock_format_reference.assert_called_once_with('refs')
        self.mock_format_protoclaim.assert_called_once()

    def test_make_preview_page_no_ref(self):
        self.preview_item.ref = None
        expected = (
            'bold_Labels | Aliases:\nformatted_label\n\n'
            'bold_Descriptions:\nformatted_description\n\n'
            'bold_Matching item: formatted_item\n\n'
            'bold_Claims:\nformatted_protoclaim\n\n'
        )
        self.assertEqual(self.preview_item.make_preview_page(), expected)
        self.mock_bold.assert_has_calls([
            mock.call('Labels | Aliases'),
            mock.call('Descriptions'),
            mock.call('Matching item'),
            mock.call('Claims')
        ])
        self.mock_format_label.assert_called_once()
        self.mock_format_description.assert_called_once()
        self.mock_format_item.assert_called_once()
        self.mock_format_reference.assert_not_called()
        self.mock_format_protoclaim.assert_called_once()
