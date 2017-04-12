# -*- coding: utf-8 -*-
"""
Some common WDQS methods.

Meant as a quick replacement for WDQ searches (which always time out) to be
used until there is a proper pywikibot module.

@todo: split of the WDQ replacement bits and the pure WDQS bits.
@todo: Deprecate bits of this in favour of pywikibot.sparql
@todo: Rebuild as more OOP
"""
from __future__ import unicode_literals
from builtins import dict, str
import json
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
    j = json.loads(r.content)

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


# @todo: Need support for u'CLAIM[195:qid1,195:qid2]'
def wdq_to_wdqs(wdq_query):
    """
    A wrapper for easily swapping in wdqs for WDQ queries.

    Tries to convert the query & convert the results to the same
    format as that outputted by WDQ. In addition to the caught exceptions this
    cannot handle:
    * non-CLAIM/NOCLAIM/STRING qualifiers e.g. CLAIM[...]{AROUND[...]}
    * multiple values CLAIM[pid:qid,pid2:qid2] (supported in qualifiers)
    * anything with AND
    * OR outside of qualifiers
    could possibly be replaced by a call to
    https://tools.wmflabs.org/wdq2sparql/w2s.php?wdq=<wdq_query>

    Note that this should in no way be considered complete and will not support
    a bunch of edge cases.

    @param wdq_query: the WDQ query
    @type wdq_query: str
    @return: the resulting Q ids, without Q prefix
    @rtype: list of str
    """
    if wdq_query.startswith('STRING'):
        # @todo: should check nothing comes after the STRING[]
        # STRING[prop:"string"]
        prop, sep, string = wdq_query[len('STRING['):-len(']')].partition(':')
        data = make_string_wdqs_search(prop, string.strip('\'"'))
    elif wdq_query.startswith('TREE'):
        # @todo: should check nothing comes after the TREE[][][]
        # TREE[item_1][prop_2][prop_3]
        part = wdq_query[len('TREE['):-len(']')].split('][')
        data = make_tree_wdqs_search(part[0], part[1], part[2])
    elif wdq_query.startswith('CLAIM'):
        # WDQ CLAIM[prop], CLAIM[prop:qid] and CLAIM[prop]{qualifiers}
        # but not CLAIM[pid:qid,pid2:qid2]
        main_claim = wdq_query[len('CLAIM['):wdq_query.find(']')]
        if ',' in main_claim:
            raise NotImplementedError(
                "Please Implement a method for wdq_queries of type: %s" %
                wdq_query)
        prop, sep, item = main_claim.partition(':')
        item = item or None

        qual_sparql = None
        if wdq_query.rfind(']') != wdq_query.find(']'):
            if wdq_query[wdq_query.find(']') + 1] == '{':
                qualifiers = wdq_query[wdq_query.find(']') + 1:]
                qual_sparql = make_claim_qualifiers_sparql(prop, qualifiers)
            else:
                raise NotImplementedError(
                    "Please Implement a method for wdq_queries of type: %s" %
                    wdq_query)

        data = make_claim_wdqs_search(prop, q_value=item,
                                      qualifiers=qual_sparql)
    else:
        raise NotImplementedError("Please Implement a method for wdq_queries "
                                  "of type: %s" % wdq_query)

    # format data to WDQ output
    return sanitize_to_wdq_result(data)


def sanitize_to_wdq_result(data):
    """
    Format data to match WDQ output.

    @param data: data to sanitize
    @type data: list of str
    @return: sanitized data
    @rtype: list of int
    """
    if not isinstance(data, list):
        raise pywikibot.Error(
            "sanitize_to_wdq_result() requires input data to be a list of "
            "strings not a '{}'".format(type(data)))

    for i, d in enumerate(data):
        # convert Q123 to int 123
        data[i] = int(d.lstrip('Q'))
    return data


def process_query_results(data, key, output_type, value_key=None,
                          allow_multiple=False):
    """
    Wrapper function around sanitize_wdqs_result and list processing funtions.

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


# @todo: can also add optional_props, allow_multiple
def make_string_wdqs_search(prop, string):
    """
    Make a simple string search and return matching items.

    A replacement for the WDQ STRING[prop:"string"].

    @param prop: Property id, with or without P
    @type prop: str or int
    @param string: the string to search for (with or without quotes)
    @type string: str
    @return: the resulting Q ids, with Q prefix
    @rtype: list of str
    """
    query = make_string_sparql(prop, string)

    # make the query
    return make_select_wdqs_query(query, 'item')


def make_tree_wdqs_search(item_1, prop_2, prop_3):
    """
    Make a simple TREE search and return matching items.

    A replacement for the WDQ TREE[item_1][prop_2][prop_3].

    @param item_1: First item id, with or without Q
    @type item_1: str or int
    @param prop_2: Second property id, with or without P
    @type prop_2: str or int
    @param prop_3: Second property id, with or without P
    @type prop_3: str or int
    @return: the resulting Q ids, with Q prefix
    @rtype: list of str
    """
    label = 'item'
    if not item_1:
        raise pywikibot.Error('Tree searches require a starting item')

    query = make_tree_sparql(item_1, prop_2, prop_3, item_label=label)

    # make the query
    data = make_simple_wdqs_query(query)
    return process_query_results(data, label, 'list')


# @todo: add item_label=None arg (with 'item' as default)
def make_tree_sparql(item_1, prop_2, prop_3, item_label=None):
    """
    Make a simple TREE search and return matching items.

    A replacement for the WDQ TREE[item_1][prop_2][prop_3]. Depending on which
    are present the resulting query becomes:

    All three:
        SELECT ?item WHERE {
        ?tree0 (wdt:P2)* ?item .
        ?tree0 (wdt:P3)* wd:Q1 .
        }
    First two only:
        SELECT ?item WHERE {
        ?tree0 (wdt:P2)* ?item .
        BIND (wd:Q1 AS ?tree0)
        }
    First and last only:
        SELECT ?item WHERE {
        ?item (wdt:P3)* wd:Q1 .
        }
    First only:
        SELECT ?item WHERE {
        BIND (wd:Q1 AS ?item)
        }

    @param item_1: First item id, with or without Q
    @type item_1: str or int
    @param prop_2: Second property id, with or without P
    @type prop_2: str or int
    @param prop_3: Second property id, with or without P
    @type prop_3: str or int
    @param item_label: label used for the subject
        (defaults to "item" for a main claim or "dummy0" for a qualifier)
    @type item_label: str
    @return: the resulting Q ids, with Q prefix
    @rtype: list of str
    """
    # standardise inout
    label = item_label or 'item'
    item_1 = 'Q%s' % str(item_1).lstrip('Q')
    prop_2 = 'P%s' % str(prop_2).lstrip('P') if prop_2 else None
    prop_3 = 'P%s' % str(prop_3).lstrip('P') if prop_3 else None

    query = "SELECT ?{item} WHERE ".format(item=label)
    query += "{ "
    if prop_2 and prop_3:
        query += "?tree0 (wdt:{P2})* ?{item} . ".format(P2=prop_2, item=label)
        query += "?tree0 (wdt:{P3})* wd:{Q1} . ".format(Q1=item_1, P3=prop_3)
    elif prop_2:
        query += "?tree0 (wdt:{P2})* ?{item} . ".format(P2=prop_2, item=label)
        query += "BIND (wd:{Q1} AS ?tree0) ".format(Q1=item_1)
    elif prop_3:
        query += "?item (wdt:{P3})* wd:{Q1} . ".format(Q1=item_1, P3=prop_3)
    else:
        query += "BIND (wd:{Q1} AS ?{item}) ".format(Q1=item_1, item=label)
    query += "}"

    return query


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


# @todo: rebuild wdq_to_wdqs to deal with multiple
# @todo: rebuild with q_value=None/True/False/str/int where True/False is
#        todays get_values and None/str/int are todays q_value
def make_claim_wdqs_search(prop, get_values=False, q_value=None,
                           qualifiers=None, optional_props=None,
                           allow_multiple=False):
    """
    Make a simple search for items with a certain property.

    A replacement for the WDQ CLAIM[prop] and CLAIM[prop:qid] with get_values
    corresponding to the props addon (more props are specified using
    optional_props).

    @param prop: Property id, with or without P-prefix
    @type prop: str or int
    @param get_values: whether to also return the values
    @type get_values: bool
    @param q_value: sets the expected value of the prop; CLAIM[prop:q_value]
        must be a Q item (with or without Q-prefix).
    @type q_value: str
    @param qualifiers: sparql code for further filtering on qualifiers. Must be
        formated to take the item_label as format string argument.
    @type qualifiers: str
    @param optional_props: list of other properties to optionally request
    @type optional_props: list
    @param allow_multiple: if multiple values are allowed for each item.
        If True then each entry is a set of values.
    @type allow_multiple: bool
    @return: the resulting Q-ids, with Q prefix and values if requested
    @rtype: list of str or dict
    """
    # check for illegal combinations
    if q_value and get_values:
        raise pywikibot.Error('Cannot combine q_value and get_value for '
                              'make_claim_wdqs_search.')

    query = make_claim_sparql(prop, q_value)

    # handle get_values
    select_value = None
    if get_values:
        select_value = 'value'

    # make query
    return make_select_wdqs_query(query, 'item', select_value, qualifiers,
                                  optional_props, allow_multiple)


def make_claim_qualifiers_sparql(main_prop, qualifiers):
    """
    Make the required sparql for qualifiers to a CLAIM.

    I.e. a qualifier like CLAIM[pid]{CLAIM[pid:qid]}.
    Only supports qualifiers of CLAIM, NOCLAIM and STRING type.

    Known issues:
    Will not handle AND correctly.
    Fails if a STRING claim contains a "," or an " OR ".
    Will fail if you tried to do any grouping with brackets.

    @param main_prop: the property (pid) of the main CLAIM
    @type main_prop: str
    @param qualifiers: the qualifier string including "{}"
    @type qualifiers: str
    @return: sparql code for (all) qualifiers
    @rtype: str
    """
    main_prop = 'P%s' % str(main_prop).lstrip('P')
    qualifier_sparqls = []

    for qualifier in [q.strip() for q in qualifiers.strip('{}').split(' OR ')]:
        typ = func = None
        if qualifier.startswith('CLAIM'):
            typ = 'CLAIM'
            func = make_claim_sparql
        elif qualifier.startswith('STRING'):
            typ = 'STRING'
            func = make_string_sparql
        elif qualifier.startswith('NOCLAIM'):
            typ = 'NOCLAIM'
            func = make_noclaim_sparql
        else:
            raise NotImplementedError(
                "Please implement a method for non CLAIM/NOCLAIM/STRING "
                "qualifiers.")

        qualifier = qualifier[len('%s[' % typ):-len(']')]
        for qual in [q.strip() for q in qualifier.split(',')]:
            prop, sep, val = qual.partition(':')
            qualifier_sparqls.append(func(prop, val, qualifier=True))

    subquery = ("%%s p:%s ?dummy0 . "
                "{ %s } " % (main_prop,
                             " } UNION { ".join(qualifier_sparqls)))
    return subquery


def make_claim_sparql(prop, q_value=None, item_label=None, value_label=None,
                      qualifier=False):
    """
    Make sparql component for a CLAIM type claim.

    Can either be a main claim or a qualifier.
    Covers both CLAIM[prop] and CLAIM[prop:qid].

    @param prop: Property id, with or without P-prefix
    @type prop: str or int
    @param q_value: sets the expected value of the prop; CLAIM[prop:q_value]
        must be a Q item (with or without Q-prefix).
    @type q_value: str or int
    @param item_label: label used for the subject
        (defaults to "item" for a main claim or "dummy0" for a qualifier)
    @type item_label: str
    @param value_label: label used for the object. Cannot be combined with
        q_value. (defaults to "value" for a main claim or "<item_label>_value"
        for a qualifier)
    @type value_label: str
    @param qualifier: if the claim is a qualifier or not
    @type qualifier: bool
    @return: sparql code for the CLAIM (incl. qualifiers)
    @rtype: str
    """
    # check for illegal combinations
    if q_value and value_label:
        raise pywikibot.Error('Cannot combine q_value and value_label in '
                              'make_claim_sparql_new.')

    # handle value
    if q_value:
        value = 'wd:Q%s' % str(q_value).lstrip('Q')  # standardise input
    else:
        value = '?%s' % value_label if value_label else None

    return make_sparql_triple(prop, value, item_label, qualifier)


def make_string_sparql(prop, string, item_label=None, qualifier=False):
    """
    Make sparql component for a STRING type claim.

    Can either be a main claim or a qualifier.

    Note that this cannot handle strings ending with an apostrophe.

    @param prop: the property (pid)
    @type prop: str or int
    @param string: the string value (with or without quotes)
    @type string: str
    @param item_label: label used for the subject
        (defaults to "item" for a main claim or "dummy0" for a qualifier)
    @type item_label: str
    @param qualifier: if the claim is a qualifier or not
    @type qualifier: bool
    @return: sparql code for STRING claim
    @rtype: str
    """
    value = '\"%s\"' % string.strip('\'"')
    return make_sparql_triple(prop, value, item_label, qualifier)


def make_noclaim_sparql(prop, value, item_label=None, qualifier=False):
    """
    Make sparql component for a NOCLAIM type claim.

    Can either be a main claim or a qualifier.

    @param prop: the property (pid)
    @type prop: str or int
    @param value: the value (should always be None?)
    @type value: str
    @param item_label: label used for the subject
        (defaults to "item" for a main claim or "dummy0" for a qualifier)
    @type item_label: str
    @param qualifier: if the claim is a qualifier or not
    @type qualifier: bool
    @return: sparql code for NOCLAIM claim
    @rtype: str
    """
    sparql = make_sparql_triple(prop, value, item_label, qualifier)
    # braces are always needed (but we do not need double braces
    return 'FILTER NOT EXISTS { %s }' % sparql.strip('{} ')


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
