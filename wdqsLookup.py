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


def make_simple_wdqs_query(query, verbose=False):
    """Make limited queries to the wdqs service for wikidata.

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
        hooks = j['head']['vars']
        for binding in j['results']['bindings']:
            entry = {}
            for hook in hooks:
                entry[hook] = binding[hook]['value']
            data.append(entry.copy())
    except:
        raise pywikibot.Error('Shit went wronq with the wdqs query:\n'
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
    For dicts it is assumed that it is the key which should be sanitized

    @param data: data to sanitize
    @type data: str, or list of str or dict
    @return: sanitized data
    @rtype: list of str
    """
    if isinstance(data, (str, unicode)):
        return data.split('/')[-1]
    elif isinstance(data, list):
        for i, d in enumerate(data):
            data[i] = d.split('/')[-1]
        return data
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.iteritems():
            new_data[k.split('/')[-1]] = v
        return new_data
    else:
        raise pywikibot.Error('sanitize_wdqs_result() requires a string, dict '
                              ' or a list of strings. Not a %s' % type(data))


def list_of_dict_to_list(data, key):
    """Given a list of dicts, return a list of values for a given key.

    Crashes badly if the key is not present in each dict entry.

    @param data: the list of dicts
    @type data: lsit of dict
    @param key: the key to look for in the dict
    @type key: str
    @return: the list of matching  values
    @rtype: list
    """
    results = []
    for entry in data:
        results.append(entry[key])
    return results


def list_of_dict_to_dict(data, key_key, value_key):
    """Given a list of dicts make a dict where the given key is used to get keys.

    Crashes badly if the key is not present in each dict entry.

    @param data: the list of dicts
    @type data: lsit of dict
    @param key_key: the key corresponding to the value to use as key for
        the new dict
    @type key_key: str
    @param value_key: the key corresponding to the value to use as value for
        the new dict
    @type value_key: str
    @return: the dict of new key-value pairs
    @rtype: dict
    """
    results = {}
    for entry in data:
        if entry[key_key] in results.keys() and \
                entry[value_key] != results[entry[key_key]]:
            # two hits corresponding to different values
            raise pywikibot.Error('Double ids in Wikidata: %s, %s' %
                                  (entry[value_key], results[entry[key_key]]))
        results[entry[key_key]] = entry[value_key]
    return results


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
    data = make_simple_wdqs_query(query % (prop, string))
    return sanitize_wdqs_result(
        list_of_dict_to_list(data, 'item'))


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
    data = make_simple_wdqs_query(query)
    return sanitize_wdqs_result(
        list_of_dict_to_list(data, 'item'))


def make_claim_wdqs_search(prop, get_values=False):
    """Make a simple search for items with a certain property.

    A replacement for the WDQ CLAIM[prop] with get_values corresponding to the
    props addon (but limited to the same prop as queried).

    @param prop: Property id, with or without P
    @type prop: str or int
    @param get_values: whether to also return the values
    @type get_values: bool
    @return: the resulting Q-ids, with Q prefix and values if requested
    @rtype: list of str or dict
    """
    prop = 'P%s' % str(prop).lstrip('P')
    query = ""
    if get_values:
        query += "SELECT ?item ?value WHERE { "
    else:
        query += "SELECT ?item WHERE { "
    query += ""\
        "?item wdt:%s ?value " \
        "}"

    # make the query
    data = make_simple_wdqs_query(query % (prop))
    if not get_values:
        return sanitize_wdqs_result(
            list_of_dict_to_list(data, 'item'))
    else:
        return sanitize_wdqs_result(
            list_of_dict_to_dict(data, 'item', 'value'))
