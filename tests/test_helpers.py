# -*- coding: utf-8  -*-
"""Unit tests for helpers."""
from __future__ import unicode_literals

import unittest
import mock

from wikidataStuff.helpers import (
    get_unit_q,
    is_number,
    is_int,
    is_pos_int,
    sig_fig_error,
    fill_cache_wdqs,
    fill_cache,
    convert_language_dict_to_json
)


class TestIsInt(unittest.TestCase):

    """Test the is_int method."""

    def test_is_int_empty_string_fail(self):
        s = ''
        result = is_int(s)
        self.assertEqual(result, False)

    def test_is_int_none_fail(self):
        s = None
        result = is_int(s)
        self.assertEqual(result, False)

    def test_is_int_random_string_fail(self):
        s = 'random_string'
        result = is_int(s)
        self.assertEqual(result, False)

    def test_is_int_float_fail(self):
        s = '123.456'
        result = is_int(s)
        self.assertEqual(result, False)

    def test_is_int_valid_negative_int_succeed(self):
        s = '-123'
        result = is_int(s)
        self.assertEqual(result, True)

    def test_is_int_valid_int_succeed(self):
        s = '123'
        result = is_int(s)
        self.assertEqual(result, True)


class TestIsPosInt(unittest.TestCase):

    """Test the is_pos_int method."""

    def test_is_pos_int_empty_string_fail(self):
        s = ''
        result = is_pos_int(s)
        self.assertEqual(result, False)

    def test_is_pos_int_none_fail(self):
        s = None
        result = is_pos_int(s)
        self.assertEqual(result, False)

    def test_is_pos_int_random_string_fail(self):
        s = 'random_string'
        result = is_pos_int(s)
        self.assertEqual(result, False)

    def test_is_pos_int_float_fail(self):
        s = '123.456'
        result = is_pos_int(s)
        self.assertEqual(result, False)

    def test_is_pos_int_negative_int_fail(self):
        s = '-123'
        result = is_pos_int(s)
        self.assertEqual(result, False)

    def test_is_pos_int_valid_int_succeed(self):
        s = '123'
        result = is_pos_int(s)
        self.assertEqual(result, True)


class TestIsNumber(unittest.TestCase):

    """Test the is_number method."""

    def test_is_number_empty_string_fail(self):
        s = ''
        result = is_number(s)
        self.assertEqual(result, False)

    def test_is_number_none_fail(self):
        s = None
        result = is_number(s)
        self.assertEqual(result, False)

    def test_is_number_random_string_fail(self):
        s = 'random_string'
        result = is_number(s)
        self.assertEqual(result, False)

    def test_is_number_valid_int_succeed(self):
        s = '123'
        result = is_number(s)
        self.assertEqual(result, True)

    def test_is_number_valid_float_succeed(self):
        s = '123.456'
        result = is_number(s)
        self.assertEqual(result, True)

    def test_is_number_valid_negative_float_succeed(self):
        s = '-123.456'
        result = is_number(s)
        self.assertEqual(result, True)


class TestSigFigError(unittest.TestCase):

    """Test sig_fig_error()."""

    def test_sig_fig_error_zero(self):
        self.assertEqual(sig_fig_error("0"), 0.5)

    def test_sig_fig_error_one(self):
        self.assertEqual(sig_fig_error("1"), 0.5)

    def test_sig_fig_error_big_int(self):
        self.assertEqual(sig_fig_error("200"), 50.0)

    def test_sig_fig_error_exact_int(self):
        self.assertEqual(sig_fig_error("1010"), 5.0)

    def test_sig_fig_error_negative_int(self):
        self.assertEqual(sig_fig_error("-220"), 5.0)

    def test_sig_fig_error_zero_padded_int(self):
        self.assertEqual(sig_fig_error("03300"), 50.0)

    def test_sig_fig_error_decimal_zero(self):
        self.assertEqual(sig_fig_error("0.0"), 0.05)

    def test_sig_fig_error_with_decimal(self):
        self.assertEqual(sig_fig_error("11.0"), 0.05)

    def test_sig_fig_error_with_only_decimal(self):
        self.assertEqual(sig_fig_error("0.1"), 0.05)

    def test_sig_fig_error_negative_with_decimal(self):
        self.assertEqual(sig_fig_error("-0.1234"), 0.00005)


class TestFillCacheWdqs(unittest.TestCase):

    """Test fill_cache_wdqs()."""

    def setUp(self):
        patcher = mock.patch('wikidataStuff.WdqToWdqs.make_claim_wdqs_search')
        self.mock_wdqs_search = patcher.start()
        self.mock_wdqs_search.return_value = {
            'Q123': ['abc', 'def'],
            'Q456': ['ghi']
        }
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.helpers.pywikibot.output')
        self.mock_output = patcher.start()
        self.addCleanup(patcher.stop)

    def test_fill_cache_wdqs_prop_w_p(self):
        expected = {'abc': 123, 'def': 123, 'ghi': 456}
        result = fill_cache_wdqs('P123')
        self.mock_wdqs_search.assert_called_once_with(
            'P123', get_values=True, allow_multiple=True
        )
        self.mock_output.assert_not_called()
        self.assertCountEqual(result, expected)

    def test_fill_cache_wdqs_prop_wo_p(self):
        expected = {'abc': 123, 'def': 123, 'ghi': 456}
        result = fill_cache_wdqs('123')
        self.mock_wdqs_search.assert_called_once_with(
            'P123', get_values=True, allow_multiple=True
        )
        self.mock_output.assert_not_called()
        self.assertCountEqual(result, expected)

    def test_fill_cache_wdqs_no_strip(self):
        expected = {'abc': 'Q123', 'def': 'Q123', 'ghi': 'Q456'}
        result = fill_cache_wdqs('P123', no_strip=True)
        self.mock_wdqs_search.assert_called_once_with(
            'P123', get_values=True, allow_multiple=True
        )
        self.mock_output.assert_not_called()
        self.assertCountEqual(result, expected)

    def test_fill_cache_wdqs_non_unique(self):
        self.mock_wdqs_search.return_value = {
            'Q123': ['abc', 'def'],
            'Q456': ['ghi', 'abc']
        }
        expected = {'abc': 123, 'def': 123, 'ghi': 456}
        result = fill_cache_wdqs('123')
        self.mock_wdqs_search.assert_called_once_with(
            'P123', get_values=True, allow_multiple=True
        )
        self.mock_output.assert_called_once()
        # Note that we cannot easily check the sent value since order of the
        # dict is not guaranteed
        self.assertCountEqual(result, expected)

    def test_fill_cache_wdqs_queryoverride_trigger_error(self):
        with self.assertRaises(NotImplementedError):
            fill_cache_wdqs('123', queryoverride='A')
        self.mock_wdqs_search.assert_not_called()
        self.mock_output.assert_not_called()


class TestFillCache(unittest.TestCase):

    """Test fill_cache()."""

    def setUp(self):
        patcher = mock.patch('wikidataStuff.helpers.fill_cache_wdqs')
        self.mock_fill_cache_wdqs = patcher.start()
        self.mock_fill_cache_wdqs.return_value = 'fill_cache_wdqs return value'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.helpers.pywikibot.warning')
        self.warning = patcher.start()
        self.addCleanup(patcher.stop)

    def test_fill_cache_redirects_and_warns(self):
        expected = 'fill_cache_wdqs return value'
        result = fill_cache('P123', 'override', 'max_age')
        self.mock_fill_cache_wdqs.assert_called_once_with(
            'P123', queryoverride='override')
        self.warning.assert_called_once_with(
            'fill_cache is deprecated. Use fill_cache_wdqs instead.')
        self.assertEqual(result, expected)


class TestGetUnitQ(unittest.TestCase):

    """Test get_unit_q()."""

    def test_get_unit_q_empty(self):
        self.assertEqual(get_unit_q(''), None)

    def test_get_unit_q_match(self):
        self.assertEqual(get_unit_q('km2'), 'Q712226')

    def test_get_unit_q_no_match(self):
        self.assertEqual(get_unit_q('foo'), None)

    def test_get_unit_q_raised(self):
        self.assertEqual(get_unit_q('km²'), 'Q712226')


class TestConvertLanguageDictToJson(unittest.TestCase):

    """Test the convert_language_dict_to_json method."""

    def test_convert_language_dict_to_json_empty(self):
        self.assertEqual(
            convert_language_dict_to_json({}, 'labels'),
            {}
        )

    def test_convert_language_dict_to_json_single(self):
        expected = {
            'en': {
                'language': 'en',
                'value': 'foo'
            }
        }
        data = {'en': 'foo'}
        self.assertEqual(
            convert_language_dict_to_json(data, 'labels'),
            expected
        )

    def test_convert_language_dict_to_json_multiple(self):
        expected = {
            'en': {
                'language': 'en',
                'value': 'foo'
            },
            'sv': {
                'language': 'sv',
                'value': 'bar'
            }
        }
        data = {'en': 'foo', 'sv': 'bar'}
        self.assertEqual(
            convert_language_dict_to_json(data, 'labels'),
            expected
        )

    def test_convert_language_dict_to_json_alias_list(self):
        expected = {
            'en': {
                'language': 'en',
                'value': ['foo', 'bar']
            }
        }
        data = {'en': ['foo', 'bar']}
        self.assertEqual(
            convert_language_dict_to_json(data, 'aliases'),
            expected
        )

    def test_convert_language_dict_to_json_non_alias_list_one(self):
        expected = {
            'en': {
                'language': 'en',
                'value': 'foo'
            }
        }
        data = {'en': ['foo', ]}
        self.assertEqual(
            convert_language_dict_to_json(data, 'labels'),
            expected
        )

    def test_convert_language_dict_to_json_non_alias_list_multiple(self):
        data = {'en': ['foo', 'bar']}
        with self.assertRaises(ValueError) as cm:
            convert_language_dict_to_json(data, 'labels')
        self.assertEqual(
            str(cm.exception),
            'labels must not have a list of values for a single language.'
        )
        with self.assertRaises(ValueError) as cm:
            convert_language_dict_to_json(data, 'descriptions')

    def test_convert_language_dict_to_json_wrong_type(self):
        with self.assertRaises(ValueError) as cm:
            convert_language_dict_to_json({}, 'foo')
        self.assertEqual(
            str(cm.exception),
            '"foo" is not a valid type for convert_language_dict_to_json().'
        )
