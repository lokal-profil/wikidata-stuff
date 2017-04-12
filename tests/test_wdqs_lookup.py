# -*- coding: utf-8  -*-
"""Unit tests for converters."""
from __future__ import unicode_literals

import unittest
import mock
import sys

import pywikibot

from wikidataStuff.wdqsLookup import (
    make_sparql_triple,
    make_noclaim_sparql,
    make_string_sparql,
    make_claim_sparql,
    make_claim_qualifiers_sparql,
    make_claim_wdqs_search,
    make_select_wdqs_query,
    make_tree_sparql,
    make_tree_wdqs_search,
    make_string_wdqs_search,
    list_of_dict_to_list,
    list_of_dict_to_dict,
    sanitize_wdqs_result,
    process_query_results,
    sanitize_to_wdq_result,
    wdq_to_wdqs
)
PYTHON_VERSION = sys.version_info[:3]
if (PYTHON_VERSION[0] == 2):
    unittest.TestCase.assertCountEqual = unittest.TestCase.assertItemsEqual


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


class TestWDQFormatBase(unittest.TestCase):

    """Test base for various WDQ formatting methods."""

    def setUp(self):
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_sparql_triple')
        self.mock_sparql_triple = patcher.start()
        self.mock_sparql_triple.return_value = 'sparql_triple'
        self.addCleanup(patcher.stop)


class TestMakeNoclaimSparql(TestWDQFormatBase):

    """Test the make_noclaim_sparql method."""

    def test_make_noclaim_sparql_defaults(self):
        expected = 'FILTER NOT EXISTS { sparql_triple }'
        result = make_noclaim_sparql('P123', 456)
        self.mock_sparql_triple.assert_called_once_with(
            'P123', 456, None, False)
        self.assertEqual(result, expected)

    def test_make_noclaim_sparql_all_values_passed_on(self):
        expected = 'FILTER NOT EXISTS { sparql_triple }'
        result = make_noclaim_sparql(
            'P123', 456, item_label='test', qualifier=True)
        self.mock_sparql_triple.assert_called_once_with(
            'P123', 456, 'test', True)
        self.assertEqual(result, expected)

    def test_make_noclaim_sparql_trim_braces(self):
        self.mock_sparql_triple.return_value = '{ sparql_triple }'
        expected = 'FILTER NOT EXISTS { sparql_triple }'
        result = make_noclaim_sparql('P123', 456)
        self.assertEqual(result, expected)


class TestMakeStringSparql(TestWDQFormatBase):

    """Test the make_string_sparql method."""

    def test_make_string_sparql_defaults(self):
        expected = 'sparql_triple'
        result = make_string_sparql('P123', 'string')
        self.mock_sparql_triple.assert_called_once_with(
            'P123', '\"string\"', None, False)
        self.assertEqual(result, expected)

    def test_make_string_sparql_trim_double_quotes(self):
        expected = 'sparql_triple'
        result = make_string_sparql('P123', '"string"')
        self.mock_sparql_triple.assert_called_once_with(
            'P123', '\"string\"', None, False)
        self.assertEqual(result, expected)

    def test_make_string_sparql_trim_single_quotes(self):
        expected = 'sparql_triple'
        result = make_string_sparql('P123', "'string'")
        self.mock_sparql_triple.assert_called_once_with(
            'P123', '\"string\"', None, False)
        self.assertEqual(result, expected)

    @unittest.expectedFailure
    def test_make_string_sparql_apostrophe_failiure(self):
        expected = 'sparql_triple'
        result = make_string_sparql('P123', '"string\'"')
        self.mock_sparql_triple.assert_called_once_with(
            'P123', '\"string\'\"', None, False)
        self.assertEqual(result, expected)

    def test_make_string_sparql_all_values_passed_on(self):
        expected = 'sparql_triple'
        result = make_string_sparql(
            'P123', 'string', item_label='test', qualifier=True)
        self.mock_sparql_triple.assert_called_once_with(
            'P123', '\"string\"', 'test', True)
        self.assertEqual(result, expected)


class TestMakeClaimSparql(TestWDQFormatBase):

    """Test the make_claim_sparql method."""

    def test_make_claim_sparql_defaults(self):
        expected = 'sparql_triple'
        result = make_claim_sparql('P123')
        self.mock_sparql_triple.assert_called_once_with(
            'P123', None, None, False)
        self.assertEqual(result, expected)

    def test_make_claim_sparql_q_value(self):
        expected = 'sparql_triple'
        result = make_claim_sparql('P123', q_value='Q456')
        self.mock_sparql_triple.assert_called_once_with(
            'P123', 'wd:Q456', None, False)
        self.assertEqual(result, expected)

    def test_make_claim_sparql_q_value_no_q(self):
        expected = 'sparql_triple'
        result = make_claim_sparql('P123', q_value='456')
        self.mock_sparql_triple.assert_called_once_with(
            'P123', 'wd:Q456', None, False)
        self.assertEqual(result, expected)

    def test_make_claim_sparql_value_label(self):
        expected = 'sparql_triple'
        result = make_claim_sparql('P123', value_label='label')
        self.mock_sparql_triple.assert_called_once_with(
            'P123', '?label', None, False)
        self.assertEqual(result, expected)

    def test_make_claim_sparql_all_values_passed_on(self):
        expected = 'sparql_triple'
        result = make_claim_sparql(
            'P123', item_label='item_label', qualifier=True)
        self.mock_sparql_triple.assert_called_once_with(
            'P123', None, 'item_label', True)
        self.assertEqual(result, expected)

    def test_make_claim_sparql_illegal_combo(self):
        with self.assertRaises(pywikibot.Error):
            make_claim_sparql(
                'P123', q_value='Q456', value_label='value_label')
        self.mock_sparql_triple.assert_not_called()


class TestMakeClaimQualifiersSparql(unittest.TestCase):

    """Test the make_claim_qualifiers_sparql method."""

    def setUp(self):
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_claim_sparql')
        self.mock_claim_sparql = patcher.start()
        self.mock_claim_sparql.return_value = 'sparql'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_string_sparql')
        self.mock_string_sparql = patcher.start()
        self.mock_string_sparql.return_value = 'sparql'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_noclaim_sparql')
        self.mock_noclaim_sparql = patcher.start()
        self.mock_noclaim_sparql.return_value = 'sparql'
        self.addCleanup(patcher.stop)

    def test_make_claim_qualifiers_sparql_detect_claim(self):
        make_claim_qualifiers_sparql('P123', '{CLAIM[prop:val]}')
        self.mock_claim_sparql.assert_called_once_with(
            'prop', 'val', qualifier=True)
        self.mock_string_sparql.assert_not_called()
        self.mock_noclaim_sparql.assert_not_called()

    def test_make_claim_qualifiers_sparql_detect_string(self):
        make_claim_qualifiers_sparql('P123', '{STRING[prop:"string"]}')
        self.mock_claim_sparql.assert_not_called()
        self.mock_string_sparql.assert_called_once_with(
            'prop', '"string"', qualifier=True)
        self.mock_noclaim_sparql.assert_not_called()

    def test_make_claim_qualifiers_sparql_detect_noclaim(self):
        make_claim_qualifiers_sparql('P123', '{NOCLAIM[prop:val]}')
        self.mock_claim_sparql.assert_not_called()
        self.mock_string_sparql.assert_not_called()
        self.mock_noclaim_sparql.assert_called_once_with(
            'prop', 'val', qualifier=True)

    def test_make_claim_qualifiers_sparql_unsupported(self):
        with self.assertRaises(NotImplementedError):
            make_claim_qualifiers_sparql('P123', '{TREE[Q456]}')
        self.mock_claim_sparql.assert_not_called()
        self.mock_string_sparql.assert_not_called()
        self.mock_noclaim_sparql.assert_not_called()

    def test_make_claim_qualifiers_sparql_single_qualifiers(self):
        expected = "%s p:P123 ?dummy0 . { sparql } "
        result = make_claim_qualifiers_sparql(
            'P123', '{CLAIM[prop:val]}')
        self.assertEqual(result, expected)

    def test_make_claim_qualifiers_sparql_single_qualifiers_no_p(self):
        expected = "%s p:P123 ?dummy0 . { sparql } "
        result = make_claim_qualifiers_sparql(
            '123', '{CLAIM[prop:val]}')
        self.assertEqual(result, expected)

    def test_make_claim_qualifiers_sparql_multiple_qualifiers_inside(self):
        expected = "%s p:P123 ?dummy0 . { sparql } UNION { sparql } "
        result = make_claim_qualifiers_sparql(
            'P123', '{CLAIM[prop:val,prop2:val2]}')
        self.assertEqual(result, expected)
        expected_calls = [
            mock.call('prop', 'val', qualifier=True),
            mock.call('prop2', 'val2', qualifier=True)]
        self.mock_claim_sparql.assert_has_calls(expected_calls)
        self.mock_string_sparql.assert_not_called()
        self.mock_noclaim_sparql.assert_not_called()

    def test_make_claim_qualifiers_sparql_multiple_qualifiers_different(self):
        expected = "%s p:P123 ?dummy0 . { sparql } UNION { sparql } "
        result = make_claim_qualifiers_sparql(
            'P123', '{CLAIM[prop:val] OR STRING[prop:string]}')
        self.assertEqual(result, expected)
        self.mock_claim_sparql.assert_called_once_with(
            'prop', 'val', qualifier=True)
        self.mock_string_sparql.assert_called_once_with(
            'prop', 'string', qualifier=True)
        self.mock_noclaim_sparql.assert_not_called()

    def test_make_claim_qualifiers_sparql_multiple_qualifiers_same(self):
        make_claim_qualifiers_sparql(
            'P123', '{CLAIM[prop:val] OR CLAIM[prop2:val2]}')
        expected_calls = [
            mock.call('prop', 'val', qualifier=True),
            mock.call('prop2', 'val2', qualifier=True)]
        self.mock_claim_sparql.assert_has_calls(expected_calls)
        self.mock_string_sparql.assert_not_called()
        self.mock_noclaim_sparql.assert_not_called()


class TestMakeClaimWdqsSearch(unittest.TestCase):

    """Test the make_claim_wdqs_search method."""

    def setUp(self):
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_claim_sparql')
        self.mock_claim_sparql = patcher.start()
        self.mock_claim_sparql.return_value = 'claim_sparql'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_select_wdqs_query')
        self.mock_select_wdqs_query = patcher.start()
        self.mock_select_wdqs_query.return_value = 'query data'
        self.addCleanup(patcher.stop)

    def test_make_claim_wdqs_search_defaults(self):
        expected = 'query data'
        result = make_claim_wdqs_search('P123')
        self.mock_claim_sparql.assert_called_once_with(
            'P123', None)
        self.mock_select_wdqs_query.assert_called_once_with(
            'claim_sparql', 'item', None, None, None, False)
        self.assertEqual(result, expected)

    def test_make_claim_wdqs_search_get_values(self):
        make_claim_wdqs_search('P123', get_values=True)
        self.mock_claim_sparql.assert_called_once_with(
            'P123', None)
        self.mock_select_wdqs_query.assert_called_once_with(
            'claim_sparql', 'item', 'value', None, None, False)

    def test_make_claim_wdqs_search_q_value(self):
        make_claim_wdqs_search('P123', q_value='Q456')
        self.mock_claim_sparql.assert_called_once_with(
            'P123', 'Q456')
        self.mock_select_wdqs_query.assert_called_once_with(
            'claim_sparql', 'item', None, None, None, False)

    def test_make_claim_wdqs_search_all_values_passed_on(self):
        make_claim_wdqs_search(
            'P123', qualifiers='qual_sparql', optional_props=['P1', 'P2'],
            allow_multiple=True)
        self.mock_claim_sparql.assert_called_once_with(
            'P123', None)
        self.mock_select_wdqs_query.assert_called_once_with(
            'claim_sparql', 'item', None, 'qual_sparql', ['P1', 'P2'], True)

    def test_make_claim_wdqs_search_illegal_combo(self):
        with self.assertRaises(pywikibot.Error):
            make_claim_wdqs_search(
                'P123', get_values=True, q_value='Q456')
        self.mock_claim_sparql.assert_not_called()
        self.mock_select_wdqs_query.assert_not_called()


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


class TestMakeTreeSparql(unittest.TestCase):

    """Test the make_tree_sparql method."""

    def test_make_tree_sparql_first_only(self):
        expected = ('SELECT ?item WHERE { '
                    'BIND (wd:Q1 AS ?item) '
                    '}')
        result = make_tree_sparql('Q1', None, None)
        self.assertEqual(result, expected)

    def test_make_tree_sparql_first_and_last(self):
        expected = ('SELECT ?item WHERE { '
                    '?item (wdt:P3)* wd:Q1 . '
                    '}')
        result = make_tree_sparql('Q1', None, 'P3')
        self.assertEqual(result, expected)

    def test_make_tree_sparql_first_two_only(self):
        expected = ('SELECT ?item WHERE { '
                    '?tree0 (wdt:P2)* ?item . '
                    'BIND (wd:Q1 AS ?tree0) '
                    '}')
        result = make_tree_sparql('Q1', 'P2', None)
        self.assertEqual(result, expected)

    def test_make_tree_sparql_all_three(self):
        expected = ('SELECT ?item WHERE { '
                    '?tree0 (wdt:P2)* ?item . '
                    '?tree0 (wdt:P3)* wd:Q1 . '
                    '}')
        result = make_tree_sparql('Q1', 'P2', 'P3')
        self.assertEqual(result, expected)

    def test_make_tree_sparql_all_three_no_p_q(self):
        expected = ('SELECT ?item WHERE { '
                    '?tree0 (wdt:P2)* ?item . '
                    '?tree0 (wdt:P3)* wd:Q1 . '
                    '}')
        result = make_tree_sparql('1', '2', '3')
        self.assertEqual(result, expected)

    def test_make_tree_sparql_all_three_w_label(self):
        expected = ('SELECT ?test WHERE { '
                    '?tree0 (wdt:P2)* ?test . '
                    '?tree0 (wdt:P3)* wd:Q1 . '
                    '}')
        result = make_tree_sparql('Q1', 'P2', 'P3', item_label='test')
        self.assertEqual(result, expected)


class TestMakeTreeWdqsSearch(unittest.TestCase):

    """Test the make_tree_wdqs_search method."""

    def setUp(self):
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_tree_sparql')
        self.mock_tree_sparql = patcher.start()
        self.mock_tree_sparql.return_value = 'sparql'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_simple_wdqs_query')
        self.mock_simple_wdqs_query = patcher.start()
        self.mock_simple_wdqs_query.return_value = 'query_data'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.process_query_results')
        self.mock_process_query_results = patcher.start()
        self.mock_process_query_results.return_value = 'processed_data'
        self.addCleanup(patcher.stop)

    def test_make_tree_wdqs_search_basic_search(self):
        result = make_tree_wdqs_search('Q1', 'P2', 'P3')
        self.mock_tree_sparql.assert_called_once_with(
            'Q1', 'P2', 'P3', item_label='item')
        self.mock_simple_wdqs_query.assert_called_once_with(
            'sparql')
        self.mock_process_query_results.assert_called_once_with(
            'query_data', 'item', 'list')
        self.assertEqual(result, 'processed_data')

    def test_make_tree_wdqs_search_error_on_not_first(self):
        with self.assertRaises(pywikibot.Error):
            make_tree_wdqs_search(None, None, None)
        self.mock_tree_sparql.assert_not_called()
        self.mock_process_query_results.assert_not_called()


class TestMakeStringWdqsSearch(unittest.TestCase):

    """Test the make_string_wdqs_search method."""

    def setUp(self):
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_string_sparql')
        self.mock_string_sparql = patcher.start()
        self.mock_string_sparql.return_value = 'sparql'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_select_wdqs_query')
        self.mock_select_wdqs_query = patcher.start()
        self.mock_select_wdqs_query.return_value = 'processed_data'
        self.addCleanup(patcher.stop)

    def test_make_string_wdqs_search_basic_search(self):
        result = make_string_wdqs_search('P1', '"string"')
        self.mock_string_sparql.assert_called_once_with(
            'P1', '"string"')
        self.mock_select_wdqs_query.assert_called_once_with(
            'sparql', 'item')
        self.assertEqual(result, 'processed_data')


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
        self.assertEqual(
            str(cm.exception),
            "Double ids in Wikidata (A): {u'b': u'bonus'}, {u'b': u'B'}")

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


class TestSanitizeToWdqResult(unittest.TestCase):

    """Test the sanitize_to_wdq_result method."""

    def test_sanitize_to_wdq_result(self):
        data = ['Q123', 'Q456']
        expected = [123, 456]
        result = sanitize_to_wdq_result(data)
        self.assertEqual(result, expected)

    def test_sanitize_to_wdq_result_other_type_raises_error(self):
        data = 'Q123'
        with self.assertRaises(pywikibot.Error):
            sanitize_to_wdq_result(data)


class TestWdqToWdqs(unittest.TestCase):

    """Test the wdq_to_wdqs method."""

    def setUp(self):
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_string_wdqs_search')  # noqa E501
        self.mock_string_wdqs_search = patcher.start()
        self.mock_string_wdqs_search.return_value = 'string_result'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_tree_wdqs_search')
        self.mock_tree_wdqs_search = patcher.start()
        self.mock_tree_wdqs_search.return_value = 'tree_result'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_claim_wdqs_search')
        self.mock_claim_wdqs_search = patcher.start()
        self.mock_claim_wdqs_search.return_value = 'claim_result'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.make_claim_qualifiers_sparql')  # noqa E501
        self.mock_claim_qualifiers_sparql = patcher.start()
        self.mock_claim_qualifiers_sparql.return_value = 'claim_qualifier'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('wikidataStuff.wdqsLookup.sanitize_to_wdq_result')
        self.mock_sanitize_to_wdq_result = patcher.start()
        self.mock_sanitize_to_wdq_result.return_value = 'sanitized_data'
        self.addCleanup(patcher.stop)

    def test_wdq_to_wdqs_detect_string(self):
        result = wdq_to_wdqs('STRING[123:"test"]')
        self.assertEqual(result, 'sanitized_data')
        self.mock_string_wdqs_search.assert_called_once_with('123', 'test')
        self.mock_tree_wdqs_search.assert_not_called()
        self.mock_claim_wdqs_search.assert_not_called()
        self.mock_claim_qualifiers_sparql.assert_not_called()
        self.mock_sanitize_to_wdq_result.assert_called_once_with(
            'string_result')
        self.assertEqual(result, 'sanitized_data')

    def test_wdq_to_wdqs_detect_tree(self):
        result = wdq_to_wdqs('TREE[1][2][3]')
        self.mock_string_wdqs_search.assert_not_called()
        self.mock_tree_wdqs_search.assert_called_once_with('1', '2', '3')
        self.mock_claim_wdqs_search.assert_not_called()
        self.mock_claim_qualifiers_sparql.assert_not_called()
        self.mock_sanitize_to_wdq_result.assert_called_once_with(
            'tree_result')
        self.assertEqual(result, 'sanitized_data')

    def test_wdq_to_wdqs_detect_claim(self):
        result = wdq_to_wdqs('CLAIM[123]')
        self.mock_string_wdqs_search.assert_not_called()
        self.mock_tree_wdqs_search.assert_not_called()
        self.mock_claim_wdqs_search.assert_called_once_with(
            '123', q_value=None, qualifiers=None)
        self.mock_claim_qualifiers_sparql.assert_not_called()
        self.mock_sanitize_to_wdq_result.assert_called_once_with(
            'claim_result')
        self.assertEqual(result, 'sanitized_data')

    def test_wdq_to_wdqs_detect_claim_w_item(self):
        result = wdq_to_wdqs('CLAIM[123:456]')
        self.mock_string_wdqs_search.assert_not_called()
        self.mock_tree_wdqs_search.assert_not_called()
        self.mock_claim_wdqs_search.assert_called_once_with(
            '123', q_value='456', qualifiers=None)
        self.mock_claim_qualifiers_sparql.assert_not_called()
        self.mock_sanitize_to_wdq_result.assert_called_once_with(
            'claim_result')
        self.assertEqual(result, 'sanitized_data')

    def test_wdq_to_wdqs_detect_claim_w_qualifiers(self):
        result = wdq_to_wdqs(
            'CLAIM[123:456]{STRING[bad] OR CLAIM[good,bad]}')
        self.mock_string_wdqs_search.assert_not_called()
        self.mock_tree_wdqs_search.assert_not_called()
        self.mock_claim_wdqs_search.assert_called_once_with(
            '123', q_value='456', qualifiers='claim_qualifier')
        self.mock_claim_qualifiers_sparql.assert_called_once_with(
            '123', '{STRING[bad] OR CLAIM[good,bad]}')
        self.mock_sanitize_to_wdq_result.assert_called_once_with(
            'claim_result')
        self.assertEqual(result, 'sanitized_data')

    def test_sanitize_to_wdq_result_comma_in_claim_not_ok(self):
        with self.assertRaises(NotImplementedError):
            wdq_to_wdqs('CLAIM[123:456,789:0]')

    def test_sanitize_to_wdq_result_cannot_handle_multiple_claims(self):
        with self.assertRaises(NotImplementedError):
            wdq_to_wdqs('CLAIM[123:456,789:0] AND STRING[1:"test"]')

    @unittest.expectedFailure
    def test_sanitize_to_wdq_result_cannot_handle_multiple_claims_string(self):
        with self.assertRaises(NotImplementedError):
            wdq_to_wdqs('STRING[123:"test"] AND something')

    @unittest.expectedFailure
    def test_sanitize_to_wdq_result_cannot_handle_multiple_claims_tree(self):
        with self.assertRaises(NotImplementedError):
            wdq_to_wdqs('TREE[1][2][3] AND something')

    def test_sanitize_to_wdq_result_other_type_raises_error(self):
        with self.assertRaises(NotImplementedError):
            wdq_to_wdqs('AROUND[test]')
