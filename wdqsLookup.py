# -*- coding: utf-8 -*-
"""Some common WDQS methods.

Meant as a quick replacement for WDQ searches (which always time out) to be
used until there is a proper pywikibot module.
"""
import json
import urllib
import urllib2
import pywikibot

BASE_URL = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql?' \
           'format=json&query='


def make_simple_wdqs_query(hook, query, verbose=False):
    """Make limited queries to the wdqs service for wikidata.

    This will behave badly for anything selecting for more than one variable.
    It needs to be supplied with either where or override_query.

    @todo: get hook from j['head']

    @param hook: the selected variable (or one of them) as specified in the
        query or override_query parameter
    @type hook: str
    @param query: a SELECT SPARQL query (i.e. no prefix)
    @type query: str
    @param verbose: if the query should be outputted
    @type verbose: bool
    @return: results matching the hook
    @rtype: list
    """
    prefix = "" \
        "prefix wdt: <http://www.wikidata.org/prop/direct/>\n" \
        "prefix prov: <http://www.w3.org/ns/prov#>\n" \
        "prefix pr: <http://www.wikidata.org/prop/reference/>\n" \
        "prefix wd: <http://www.wikidata.org/entity/>\n"

    # perform query
    if verbose:
        pywikibot.output(prefix + query)
    j = json.load(urllib2.urlopen(BASE_URL + urllib.quote(prefix + query)))

    try:
        data = []
        for binding in j['results']['bindings']:
            data.append(binding[hook]['value'])
    except:
        raise pywikibot.Error('shit went wronq with the wdqs query:\n'
                              '%s' % query)
    return data


def wdq_to_wdqs(wdq_query):
    """A wrapper for easily swapping in wdqs for WDQ queries.

    Tries to convert the query & convert the results to the same
    format as that outputted by WDQ.

    @param wdq_query: the WDQ query
    @type wdq_query: str
    @return: the resulting Q ids, without Q prefix
    @rtype: list of str
    """
    if wdq_query.startswith('STRING'):
        # STRING[prop:"string"]
        prop, sep, string = wdq_query[len('STRING['):-len(']')].partition(':')
        data = make_string_wdqs_search(prop, string.strip('\'"'))
    elif wdq_query.startswith('TREE'):
        # TREE[item_1][prop_2][prop_3]
        part = wdq_query[len('TREE['):-len(']')].split('][')
        data = make_tree_wdqs_search(part[0], part[1], part[2])
    else:
        raise NotImplementedError("Please Implement a method for wdq_queries "
                                  "of type: %s" % wdq_query)

    # format data to WDQ output
    return sanitize_to_wdq_result(data)


def sanitize_to_wdq_result(data):
    """Format data to match WDQ output.

    @param data: data to sanitize
    @type data: list of str
    @return: sanitized data
    @rtype: list of int
    """
    for i, d in enumerate(data):
        # strip out http://www.wikidata.org/entity/
        data[i] = int(d.lstrip('Q'))
    return data


def sanitize_wdqs_result(data):
    """Strip url component out of wdqs results.

    I.e. strip out http://www.wikidata.org/entity/

    @param data: data to sanitize
    @type data: list of str
    @return: sanitized data
    @rtype: list of str
    """
    for i, d in enumerate(data):
        data[i] = d.split('/')[-1]
    return data


def make_string_wdqs_search(prop, string):
    """Make a simple string search and return matching items.

    A replacement for the WDQ STRING[prop:"string"].

    @param prop: Property id, with or without P
    @type prop: str or int
    @param string: the string to search for
    @type string: str
    @return: the resulting Q ids, with Q prefix
    @rtype: list of str
    """
    prop = 'P%s' % str(prop).lstrip('P')
    query = ""\
        "SELECT ?item WHERE { " \
        "?item wdt:%s \"%s\" " \
        "}"

    # make the query
    data = make_simple_wdqs_query('item', query % (prop, string))
    return sanitize_wdqs_result(data)


def make_tree_wdqs_search(item_1, prop_2, prop_3):
    """Make a simple TREE search and return matching items.

    A replacement for the WDQ TREE[item_1][prop_2][prop_3]. Depending on which
    are present the resulting queriy becomes:

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
    @return: the resulting Q ids, with Q prefix
    @rtype: list of str
    """
    query = "SELECT ?item WHERE { "
    # handle each component
    if not item_1:
        raise pywikibot.Error('Tree searchesrequires a starting item')
    item_1 = 'Q%s' % str(item_1).lstrip('Q')

    if prop_2:
        prop_2 = 'P%s' % str(prop_2).lstrip('P')
        query += "?tree0 (wdt:%s)* ?item . " % prop_2
    if prop_3:
        prop_3 = 'P%s' % str(prop_3).lstrip('P')
        if prop_2:
            query += "?tree0 (wdt:%s)* wd:%s . " % (prop_3, item_1)
        else:
            query += "?item (wdt:%s)* wd:%s . " % (prop_3, item_1)
    else:
        query += "BIND (wd:Q1 AS ?item) " % item_1
    query += "}"

    # make the query
    data = make_simple_wdqs_query('item', query)
    return sanitize_wdqs_result(data)
