# -*- coding: utf-8 -*-
"""
Some common WDQS methods.

Originally meant as a quick replacement for WDQ searches so most things are
built from that perspective.

@todo: Deprecate bits of this in favour of new pywikibot.sparql
@todo: Rebuild as more OOP
"""
from __future__ import unicode_literals
from builtins import dict, str
import requests
import pywikibot

import wikidataStuff.helpers as helpers


BASE_URL = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql?' \
           'format=json&query='


# @todo: add tests
def make_simple_wdqs_query(query, verbose=False):
    """
    Make limited queries to the wdqs service for Wikidata.

    Allows for simpler queries to be asked and for the results to be somewhat
    processed.

    @param query: a SELECT SPARQL query (i.e. no prefix)
    @type query: str
    @param verbose: if the query should be outputted
    @type verbose: bool
    @return: results in the format [entry{hook:value}, ]
    @rtype: list of dicts
    """
    prefix = "" \
        "PREFIX wd: <http://www.wikidata.org/entity/>\n" \
        "PREFIX wdt: <http://www.wikidata.org/prop/direct/>\n" \
        "PREFIX p: <http://www.wikidata.org/prop/>\n" \
        "PREFIX pq: <http://www.wikidata.org/prop/qualifier/>\n" \
        "PREFIX pr: <http://www.wikidata.org/prop/reference/>\n"

    # perform query
    if verbose:
        pywikibot.output(prefix + query)

    r = requests.get(BASE_URL + requests.utils.quote(prefix + query))
    r.raise_for_status()
    j = r.json()

    try:
        data = []
        hooks = j['head']['vars']
        for binding in j['results']['bindings']:
            entry = dict()
            for hook in hooks:
                if binding.get(hook):
                    entry[hook] = binding[hook]['value']
                else:
                    entry[hook] = None
            data.append(entry.copy())
    except:
        raise pywikibot.Error('Shit went wronq with the wdqs query:\n'
                              '%s' % query)
    return data


def process_query_results(data, key, output_type, value_key=None,
                          allow_multiple=False):
    """
    Process results using sanitize_wdqs_result and list processing funtions.

    For 'list' the key is the key to look for in the dict.
    For 'dict' the key the key corresponding to the value to use as key for
        the new dict.

    @param data: the list of dicts
    @type data: list of dict
    @param key: the key to pass on to list processing
    @type key: str
    @param output_type: the desired output type. Either list or dict
    @type output_type: str
    @param value_key: the key corresponding to the value to use as value for
        the new dict. If not present the new dict is simply a dict of all keys
        other than key_key.
    @type value_key: str
    @param allow_multiple: if multiple values are allowed.
        If true 'value' is always a set.
    @type allow_multiple: bool
    @return: the dict of new key-value pairs
    @rtype: dict or list depending on output_type
    """
    if output_type not in ('list', 'dict'):
        raise pywikibot.Error(
            "process_query_results() requires output_type be either "
            "'list' or 'dict' not '{}'".format(output_type))

    processed_data = None
    if output_type == 'list':
        processed_data = list_of_dict_to_list(data, key)
    else:
        processed_data = list_of_dict_to_dict(
            data, key, value_key, allow_multiple)

    return sanitize_wdqs_result(processed_data)


def sanitize_wdqs_result(data):
    """
    Strip url component out of wdqs results.

    I.e. strip out http://www.wikidata.org/entity/
    For dicts it is assumed that it is the key which should be sanitized

    @param data: data to sanitize
    @type data: str, or list of str or dict
    @return: sanitized data
    @rtype: list of str
    """
    if helpers.is_str(data):
        return data.split('/')[-1]
    elif isinstance(data, list):
        for i, d in enumerate(data):
            data[i] = d.split('/')[-1]
        return data
    if isinstance(data, dict):
        new_data = dict()
        for k, v in data.items():
            new_data[k.split('/')[-1]] = v
        return new_data
    else:
        raise pywikibot.Error('sanitize_wdqs_result() requires a string, dict '
                              'or a list of strings. Not a %s' % type(data))


def list_of_dict_to_list(data, key):
    """
    Given a list of dicts, return a list of values for a given key.

    Crashes badly if the key is not present in each dict entry.

    @param data: the list of dicts
    @type data: list of dict
    @param key: the key to look for in the dict
    @type key: str
    @return: the list of matching  values
    @rtype: list
    """
    return [entry[key] for entry in data]


def list_of_dict_to_dict(data, key_key, value_key=None, allow_multiple=False):
    """
    Given a list of dicts make a dict where the given key is used to get keys.

    Crashes badly if the key is not present in each dict entry.

    @param data: the list of dicts
    @type data: list of dict
    @param key_key: the key corresponding to the value to use as key for
        the new dict
    @type key_key: str
    @param value_key: the key corresponding to the value to use as value for
        the new dict. If not present the new dict is simply a dict of all keys
        other than key_key.
    @type value_key: str
    @param allow_multiple: if multiple values are allowed.
        If true 'value' is always a set.
    @type allow_multiple: bool
    @return: the dict of new key-value pairs
    @rtype: dict
    """
    if allow_multiple and not value_key:
        # Warning for now to see if this combo is used. Might upgrade to error.
        pywikibot.warning(
            'Duplicate values may cause a crash in without a value_key.')

    results = dict()
    for entry in data:
        key = entry[key_key]
        value = None
        if value_key:
            value = entry[value_key]
        else:
            value = entry.copy()
            del value[key_key]

        if allow_multiple:
            if key not in results:
                results[key] = set()
            results[key].add(value)
        elif key in results and value != results[key]:
            # two hits corresponding to different values
            raise pywikibot.Error(
                'Double ids in Wikidata (%s): %s, %s' %
                (key, value, results[key]))
        else:
            results[key] = value
    return results


def make_select_wdqs_query(main_query, label=None, select_value=None,
                           qualifiers=None, optional_props=None,
                           allow_multiple=False):
    """
    Put together a wdqs search query given a main query and any qualifiers.

    Note: This cannot (currently) handle multiple queries.

    @param main_query: sparql code for the main part of the query
    @type main_query: str
    @param label: label used for select, default to 'item'
    @type label: str
    @param select_value: a single value label to select for
        (also affect the format of the output)
    @type select_value: str
    @param qualifiers: sparql code for further filtering on qualifiers
    @type qualifiers: str
    @param allow_multiple: if multiple values are allowed for each item.
        If True then each entry is a set of values.
    @type allow_multiple: bool
    @param optional_props: list of other properties to optionally request
    @type optional_props: list of str
    """
    label = label or 'item'
    selects = []
    selects.append(label)
    if select_value:
        selects.append(select_value)

    # Standardise optional_props and add to selects
    if optional_props:
        # standardise input
        for k, v in enumerate(optional_props):
            optional_props[k] = 'P%s' % str(v).lstrip('P')

        selects += optional_props

    query = "SELECT ?%s WHERE { " % ' ?'.join(selects)
    query += main_query

    # add qualifiers
    if qualifiers:
        query += " "  # ensure at least one blank space
        query += qualifiers % ("?%s" % label)

    # add OPTIONALs
    if optional_props:
        query += " "  # ensure at least one blank space
        for opt_prop in optional_props:
            query += ("OPTIONAL { "
                      "?%s wdt:%s ?%s . "
                      "} " % (label, opt_prop, opt_prop))

    # close query
    query += " }"

    # make the query
    data = make_simple_wdqs_query(query)

    # sanitize the data differently based on input
    output_type = None
    value_key = None
    if not select_value and not optional_props:
        output_type = 'list'
    elif select_value and not optional_props:
        output_type = 'dict'
        value_key = select_value
    else:
        output_type = 'dict'

    return process_query_results(
        data, label, output_type, value_key, allow_multiple)


def make_sparql_triple(prop, value=None, item_label=None, qualifier=False):
    """
    Make sparql triple for a claim (either STRING or CLAIM).

    Can either be a main claim or a qualifier.

    @param prop: Property id, with or without P-prefix
    @type prop: str or int
    @param value: value of the object part of the tripple.
        (defaults to "?value" for a main claim or "?<item_label>_value" for a
        qualifier)
    @type value: str
    @param item_label: label used for the subject
        (defaults to "item" for a main claim or dummy0 for a qualifier)
    @type item_label: str
    @param qualifier: if the claim is a qualifier or not
    @type qualifier: bool
    @return: sparql code for the CLAIM (incl. qualifiers)
    @rtype: str
    """
    prop = 'P%s' % str(prop).lstrip('P')  # standardise input
    item = item_label or ('item' if not qualifier else 'dummy0')
    obj = value or ('?value' if not qualifier else '?%s_value' % item)
    pred = 'wdt' if not qualifier else 'pq'

    sparql = "?%s %s:%s %s . " % (item, pred, prop, obj)

    if qualifier:
        sparql = '{ %s }' % sparql.strip()

    return sparql
