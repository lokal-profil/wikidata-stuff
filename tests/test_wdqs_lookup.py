# -*- coding: utf-8  -*-
"""Unit tests for WDQS lookup."""
from __future__ import unicode_literals

import unittest
import mock

import pywikibot

from wikidataStuff.wdqsLookup import (
    make_sparql_triple,
    make_select_wdqs_query,
    list_of_dict_to_list,
    list_of_dict_to_dict,
    sanitize_wdqs_result,
    process_query_results
)


# @todo: use autospec=True for patches but figure out why this causes errors
class TestMakeSparqlTriple(unittest.TestCase):

    """Test the make_sparql_triple method."""

    def test_make_sparql_triple_prop_w_p(self):
        expected = '?item wdt:P123 ?value . '
        result = make_sparql_triple('P123')
        self.assertEqual(result, expected)

    def test_make_sparql_triple_prop_wo_p(self):
        expected = '?item wdt:P123 ?value . '
        result = make_sparql_triple('123')
        self.assertEqual(result, expected)

    def test_make_sparql_triple_value_string(self):
        expected = '?item wdt:P123 something . '
        result = make_sparql_triple(
            'P123', value='something')
        self.assertEqual(result, expected)

    def test_make_sparql_triple_value_int(self):
        expected = '?item wdt:P123 345 . '
        result = make_sparql_triple(
            'P123', value=345)
        self.assertEqual(result, expected)

    def test_make_sparql_triple_label(self):
        expected = '?test wdt:P123 ?value . '
        result = make_sparql_triple(
            'P123', item_label='test')
        self.assertEqual(result, expected)

    def test_make_sparql_triple_qualifier(self):
        expected = '{ ?dummy0 pq:P123 ?dummy0_value . }'
        result = make_sparql_triple(
            'P123', qualifier=True)
        self.assertEqual(result, expected)

    def test_make_sparql_triple_qualifier_value(self):
        expected = '{ ?dummy0 pq:P123 something . }'
        result = make_sparql_triple(
            'P123', value='something', qualifier=True)
        self.assertEqual(result, expected)

    def test_make_sparql_triple_qualifier_label(self):
        expected = '{ ?test pq:P123 ?test_value . }'
        result = make_sparql_triple(
            'P123', item_label='test', qualifier=True)
        self.assertEqual(result, expected)


class TestMakeSelectWdqsQuery(unittest.TestCase):

    """Test the make_select_wdqs_query method."""

    def setUp(self):
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_simple_wdqs_query')
        self.mock_simple_wdqs_query = patcher.start()
        self.mock_simple_wdqs_query.return_value = 'wdqs_reply'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.process_query_results')
        self.mock_process_query_results = patcher.start()
        self.mock_process_query_results.return_value = 'processed_data'
        self.addCleanup(patcher.stop)

    def test_make_select_wdqs_query_defaults(self):
        expected_result = 'processed_data'
        expected_query = 'SELECT ?item WHERE { main_sparql }'
        result = make_select_wdqs_query('main_sparql')
        self.mock_simple_wdqs_query.assert_called_once_with(expected_query)
        self.mock_process_query_results.assert_called_once_with(
            'wdqs_reply', 'item', 'list', None, False)
        self.assertEqual(result, expected_result)

    def test_make_select_wdqs_query_label(self):
        expected_query = 'SELECT ?test WHERE { main_sparql }'
        make_select_wdqs_query('main_sparql', label='test')
        self.mock_simple_wdqs_query.assert_called_once_with(expected_query)
        self.mock_process_query_results.assert_called_once_with(
            'wdqs_reply', 'test', 'list', None, False)

    def test_make_select_wdqs_query_select_value(self):
        expected_query = 'SELECT ?item ?test WHERE { main_sparql }'
        make_select_wdqs_query('main_sparql', select_value='test')
        self.mock_simple_wdqs_query.assert_called_once_with(expected_query)
        self.mock_process_query_results.assert_called_once_with(
            'wdqs_reply', 'item', 'dict', 'test', False)

    def test_make_select_wdqs_query_select_qualifier(self):
        expected_query = ('SELECT ?item WHERE '
                          '{ main_sparql '
                          '?item qualifier_sparql }')
        make_select_wdqs_query('main_sparql', qualifiers='%s qualifier_sparql')
        self.mock_simple_wdqs_query.assert_called_once_with(expected_query)
        self.mock_process_query_results.assert_called_once_with(
            'wdqs_reply', 'item', 'list', None, False)

    def test_make_select_wdqs_query_optional_props(self):
        expected_query = (
            'SELECT ?item ?P1 ?P2 WHERE '
            '{ main_sparql '
            'OPTIONAL { ?item wdt:P1 ?P1 . } '
            'OPTIONAL { ?item wdt:P2 ?P2 . }  }')
        make_select_wdqs_query('main_sparql', optional_props=['P1', 'P2'])
        self.mock_simple_wdqs_query.assert_called_once_with(expected_query)
        self.mock_process_query_results.assert_called_once_with(
            'wdqs_reply', 'item', 'dict', None, False)

    def test_make_select_wdqs_query_optional_props_no_p(self):
        expected_query = (
            'SELECT ?item ?P1 ?P2 WHERE '
            '{ main_sparql '
            'OPTIONAL { ?item wdt:P1 ?P1 . } '
            'OPTIONAL { ?item wdt:P2 ?P2 . }  }')
        make_select_wdqs_query('main_sparql', optional_props=['1', '2'])
        self.mock_simple_wdqs_query.assert_called_once_with(expected_query)
        self.mock_process_query_results.assert_called_once_with(
            'wdqs_reply', 'item', 'dict', None, False)

    def test_make_select_wdqs_query_select_allow_select_and_optional(self):
        expected_query = (
            'SELECT ?item ?test ?P1 WHERE '
            '{ main_sparql '
            'OPTIONAL { ?item wdt:P1 ?P1 . }  }')
        make_select_wdqs_query(
            'main_sparql', optional_props=['P1'], select_value='test')
        self.mock_simple_wdqs_query.assert_called_once_with(expected_query)
        self.mock_process_query_results.assert_called_once_with(
            'wdqs_reply', 'item', 'dict', None, False)

    def test_make_select_wdqs_query_select_allow_multiple(self):
        expected_query = 'SELECT ?item WHERE { main_sparql }'
        make_select_wdqs_query('main_sparql', allow_multiple=True)
        self.mock_simple_wdqs_query.assert_called_once_with(expected_query)
        self.mock_process_query_results.assert_called_once_with(
            'wdqs_reply', 'item', 'list', None, True)

    def test_make_select_wdqs_query_select_allow_multiple_and_select(self):
        expected_query = 'SELECT ?item ?test WHERE { main_sparql }'
        make_select_wdqs_query(
            'main_sparql', allow_multiple=True, select_value='test')
        self.mock_simple_wdqs_query.assert_called_once_with(expected_query)
        self.mock_process_query_results.assert_called_once_with(
            'wdqs_reply', 'item', 'dict', 'test', True)

    def test_make_select_wdqs_query_select_allow_multiple_and_optional(self):
        expected_query = (
            'SELECT ?item ?P1 WHERE '
            '{ main_sparql '
            'OPTIONAL { ?item wdt:P1 ?P1 . }  }')
        make_select_wdqs_query(
            'main_sparql', allow_multiple=True, optional_props=['P1'])
        self.mock_simple_wdqs_query.assert_called_once_with(expected_query)
        self.mock_process_query_results.assert_called_once_with(
            'wdqs_reply', 'item', 'dict', None, True)


class TestListOfDictToDict(unittest.TestCase):

    """Test the list_of_dict_to_dict method."""

    def setUp(self):
        self.data = [
            {'a': 'A', 'b': 'B'},
            {'a': 'alpha', 'b': 'beta', 'c': 'gamma'},
            {'a': 'alef', 'b': 'bet', 'c': 'gimel'}
        ]
        self.dupe_data = [
            {'a': 'A', 'b': 'B'},
            {'a': 'alpha', 'b': 'beta', 'c': 'gamma'},
            {'a': 'alef', 'b': 'bet', 'c': 'gimel'},
            {'a': 'A', 'b': 'bonus'}
        ]

    def test_list_of_dict_to_dict(self):
        expected = {
            'A': {'b': 'B'},
            'alpha': {'b': 'beta', 'c': 'gamma'},
            'alef': {'b': 'bet', 'c': 'gimel'},
        }
        result = list_of_dict_to_dict(self.data, 'a')
        self.assertCountEqual(result, expected)

    def test_list_of_dict_to_dict_value_key(self):
        expected = {
            'A': 'B',
            'alpha': 'beta',
            'alef': 'bet',
        }
        result = list_of_dict_to_dict(self.data, 'a', value_key='b')
        self.assertCountEqual(result, expected)

    def test_list_of_dict_to_dict_allowed_duplicates(self):
        expected = {
            'A': set(['B', 'bonus']),
            'alpha': set(['beta']),
            'alef': set(['bet']),
        }
        result = list_of_dict_to_dict(
            self.dupe_data, 'a', value_key='b', allow_multiple=True)
        self.assertCountEqual(result, expected)

    def test_list_of_dict_to_dict_allowed_duplicates_wo_value_key(self):
        patcher = mock.patch('wikidataStuff.wdqsLookup.pywikibot.warning')
        self.mock_warning = patcher.start()
        self.addCleanup(patcher.stop)

        with self.assertRaises(TypeError) as cm:
            list_of_dict_to_dict(self.dupe_data, 'a', allow_multiple=True)
            self.mock_warning.assert_called_once()
        self.assertEqual(
            str(cm.exception), "unhashable type: 'dict'")

    def test_list_of_dict_to_dict_dissallowed_duplicates_wo_value_key(self):
        with self.assertRaises(pywikibot.Error) as cm:
            list_of_dict_to_dict(self.dupe_data, 'a')
        self.assertTrue(
            str(cm.exception).startswith('Double ids in Wikidata'))

    def test_list_of_dict_to_dict_dissallowed_duplicates_w_value_key(self):
        with self.assertRaises(pywikibot.Error) as cm:
            list_of_dict_to_dict(self.dupe_data, 'a', value_key='b')
        self.assertEqual(
            str(cm.exception), 'Double ids in Wikidata (A): bonus, B')

    def test_list_of_dict_to_dict_missing_key(self):
        with self.assertRaises(KeyError):
            list_of_dict_to_dict(self.data, 'c',)

    def test_list_of_dict_to_dict_missing_value_key(self):
        with self.assertRaises(KeyError):
            list_of_dict_to_dict(self.data, 'a', value_key='c')


class TestListOfDictToList(unittest.TestCase):

    """Test the list_of_dict_to_list method."""

    def setUp(self):
        self.data = [
            {'a': 'A', 'b': 'B'},
            {'a': 'alpha', 'b': 'beta', 'c': 'gamma'},
            {'a': 'alef', 'b': 'bet', 'c': 'gimel'}
        ]

    def test_list_of_dict_to_list(self):
        expected = ['A', 'alpha', 'alef']
        result = list_of_dict_to_list(self.data, 'a')
        self.assertCountEqual(result, expected)

    def test_list_of_dict_to_list_missing_key(self):
        with self.assertRaises(KeyError):
            list_of_dict_to_list(self.data, 'c')


class TestSanitizeWdqsResult(unittest.TestCase):

    """Test the sanitize_wdqs_result method."""

    def test_sanitize_wdqs_result_str(self):
        data = 'http://www.wikidata.org/entity/Q123'
        expected = 'Q123'
        result = sanitize_wdqs_result(data)
        self.assertEqual(result, expected)

    def test_sanitize_wdqs_result_list(self):
        data = ['http://www.wikidata.org/entity/Q123',
                'http://www.wikidata.org/entity/Q456']
        expected = ['Q123', 'Q456']
        result = sanitize_wdqs_result(data)
        self.assertEqual(result, expected)

    def test_sanitize_wdqs_result_dict(self):
        data = {
            'http://www.wikidata.org/entity/Q123': 'http://www.wikidata.org/entity/Q456',  # noqa E501
            'http://www.wikidata.org/entity/Q678': {'a/b': 'c/d'}
        }
        expected = {
            'Q123': 'http://www.wikidata.org/entity/Q456',
            'Q678': {'a/b': 'c/d'}
        }
        result = sanitize_wdqs_result(data)
        self.assertCountEqual(result, expected)

    def test_sanitize_wdqs_result_other_raises_error(self):
        data = None
        with self.assertRaises(pywikibot.Error):
            sanitize_wdqs_result(data)


class TestProcessQueryResults(unittest.TestCase):

    """Test the process_query_results method."""

    def setUp(self):
        patcher = mock.patch('wikidataStuff.wdqsLookup.list_of_dict_to_list')
        self.mock_dict_to_list = patcher.start()
        self.mock_dict_to_list.return_value = 'processed_data_list'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.list_of_dict_to_dict')
        self.mock_dict_to_dict = patcher.start()
        self.mock_dict_to_dict.return_value = 'processed_data_dict'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.sanitize_wdqs_result')
        self.mock_sanitize_wdqs_result = patcher.start()
        self.mock_sanitize_wdqs_result.return_value = 'sanitized_data'
        self.addCleanup(patcher.stop)

    def test_process_query_results_list(self):
        result = process_query_results('data', 'key', 'list', value_key='v_k',
                                       allow_multiple=True)
        self.mock_dict_to_list.assert_called_once_with('data', 'key')
        self.mock_dict_to_dict.assert_not_called()
        self.mock_sanitize_wdqs_result.assert_called_once_with(
            'processed_data_list')
        self.assertEqual(result, 'sanitized_data')

    def test_process_query_results_dict(self):
        result = process_query_results('data', 'key', 'dict', value_key='v_k',
                                       allow_multiple=True)
        self.mock_dict_to_list.assert_not_called()
        self.mock_dict_to_dict.assert_called_once_with(
            'data', 'key', 'v_k', True)
        self.mock_sanitize_wdqs_result.assert_called_once_with(
            'processed_data_dict')
        self.assertEqual(result, 'sanitized_data')

    def test_process_query_results_dict_defaults(self):
        result = process_query_results('data', 'key', 'dict')
        self.mock_dict_to_list.assert_not_called()
        self.mock_dict_to_dict.assert_called_once_with(
            'data', 'key', None, False)
        self.mock_sanitize_wdqs_result.assert_called_once_with(
            'processed_data_dict')
        self.assertEqual(result, 'sanitized_data')

    def test_process_query_results_other_output_type(self):
        with self.assertRaises(pywikibot.Error):
            process_query_results('data', 'key', 'bla')
