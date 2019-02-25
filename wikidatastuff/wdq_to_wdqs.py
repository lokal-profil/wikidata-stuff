# -*- coding: utf-8 -*-
"""
Functionality for using old WDQ syntax to get WDQS results.

The results are also formatted as WDQ reults.

@todo: investigate which bits can be replaced using
       https://tools.wmflabs.org/wdq2sparql/w2s.php?wdq=<wdq_query>
"""
from __future__ import unicode_literals
from builtins import str
import pywikibot

from wikidatastuff.helpers import std_p, std_q
from wikidatastuff.wdqs_lookup import (
    make_select_wdqs_query,
    make_simple_wdqs_query,
    make_sparql_triple,
    process_query_results
)


# @todo: Need support for 'CLAIM[195:qid1,195:qid2]'
def wdq_to_wdqs(wdq_query):
    """
    Convert legacy WDQ queries to WDQS and execute.

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
                "Please Implement a method for wdq_queries of type: {}".format(
                    wdq_query))
        prop, sep, item = main_claim.partition(':')
        item = item or None

        qual_sparql = None
        if wdq_query.rfind(']') != wdq_query.find(']'):
            if wdq_query[wdq_query.find(']') + 1] == '{':
                qualifiers = wdq_query[wdq_query.find(']') + 1:]
                qual_sparql = make_claim_qualifiers_sparql(prop, qualifiers)
            else:
                raise NotImplementedError(
                    "Please Implement a method for wdq_queries of "
                    "type: {}".format(wdq_query))

        data = make_claim_wdqs_search(prop, q_value=item,
                                      qualifiers=qual_sparql)
    else:
        raise NotImplementedError("Please Implement a method for wdq_queries "
                                  "of type: {}".format(wdq_query))

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
    item_1 = std_q(item_1)
    prop_2 = std_p(prop_2) if prop_2 else None
    prop_3 = std_p(prop_3) if prop_3 else None

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
    main_prop = std_p(main_prop)
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

        qualifier = qualifier[len('{}['.format(typ)):-len(']')]
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
        value = 'wd:{}'.format(std_q(q_value))  # standardise input
    else:
        value = '?{}'.format(value_label) if value_label else None

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
