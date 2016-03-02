#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Quick bot for checking reciprocity of Wikidata-Kulturnav links.

@todo: Add some type of simple html output (e.g. bootstrap from json)
"""
import json
import urllib2
import wdqsLookup
import pywikibot.data.wikidataquery as wdquery


def get_wdq(dataset=None, data=None):
    """Find all links from Wikidata to Kulturnav using WDQ.

    @param dataset: Q-id (or list of Q-ids) corresponding to a dataset.
    @type dataset: str or list of str
    @param data: dictionary to which data should be added
    @type data: dict
    @return: (timestamp, dict {qid: uuid})
    @rtype: tuple
    """
    # initialise if needed
    data = data or {}

    # make query
    pid = '1248'
    query = u'CLAIM[%s]' % pid
    if dataset:
        query += u'{CLAIM[972:%s]}' % dataset.lstrip('Q')

    wd_queryset = wdquery.QuerySet(query)
    wd_query = wdquery.WikidataQuery(cacheMaxAge=0)
    j = wd_query.query(wd_queryset, props=[str(pid), ])

    # process data
    j = j['props'][pid]

    # extract pairs
    for i in j:
        data[u'Q%d' % i[0]] = i[2]

    # get current timestamp
    needle = u'Times :'
    stats = urllib2.urlopen(u'http://wdq.wmflabs.org/stats').read()
    stats = stats[stats.find(needle):]
    time = stats[len(needle):stats.find('\n')].strip(' -')

    return (time, data)


def get_kulturnav(dataset=None, data=None):
    """Use wdq to find all links from Wikidata to Kulturnav.

    @param dataset: the uuid corresponding to a dataset
    @type dataset: str
    @param data: object to add the matches to
    @type data: dict
    @return: matches as key-value pairs {uuid: qid}
    @rtype: dict
    """
    # initialise if needed
    if data is None:
        data = {}

    # handle lists
    if isinstance(dataset, list):
        for d in dataset:
            get_kulturnav(dataset=d, data=data)
        return data

    # single lookup
    batch_size = 250
    needles = (u'http://www.wikidata.org', 'https://www.wikidata.org')
    search_str = u'*%2F%2Fwww.wikidata.org%2Fentity%2FQ*'
    matched_tags = ['entity.sameAs_s', 'concept.exactMatch_s']
    if dataset is None:
        dataset = ''
    else:
        dataset = 'entity.dataset_r:%s,' % dataset
    urlbase = u'http://kulturnav.org/api/search/%s' % dataset

    for match in matched_tags:
        offset = 0
        url = urlbase + u'%s:%s/' % (match, search_str)
        j = json.load(urllib2.urlopen(url + '%d/%d' % (offset, batch_size)))
        while j:
            tag = match.split('_')[0]
            for i in j:
                # extract uuid and wikidata qid
                uuid = i[u'uuid']
                matches = i[u'properties'][tag]
                for m in matches:
                    if m[u'value'].startswith(needles):
                        qid = m[u'value'].split('/')[-1]
                        data[uuid] = qid

            # do next batch of requests
            offset += batch_size
            batch_url = url + '%d/%d' % (offset, batch_size)
            j = json.load(urllib2.urlopen(batch_url))

    return data


def get_references(owner=None):
    """Query for the number of statements sourced through Kulturnav.

    @param owner: the Qid of the dataset owning organisation
    @type owner: str or None
    @return: the number of sourced statement
    @rtype: int
    """
    query = ""\
        "SELECT (count(?statement) as ?mentions) WHERE {\n" \
        "   ?statement prov:wasDerivedFrom ?ref .\n" \
        "   ?ref pr:P248 ?dataset .\n" \
        "   ?dataset wdt:P31 wd:Q1172284 .\n" \
        "   ?dataset wdt:P361 wd:Q16323066 .\n"
    if owner:
        query += "   ?dataset wdt:P127 wd:%s .\n" % owner
    query += "}"

    # perform query
    data = wdqsLookup.make_simple_wdqs_query('mentions', query)
    return int(data[0])


def compare(k_dataset=None, w_dataset=None):
    """Compare the links from Wikidata to Kulturnav and vice versa.

    @param k_dataset: the uuid corresponding to a dataset
    @type k_dataset: str
    @param w_dataset: the qid corresponding to a dataset
    @type w_dataset: str
    @return: comparison {_status, kulturnav_only, wikidata_only, mismatches}
    @rtype: dict
    """
    k_data = get_kulturnav(k_dataset)
    time, w_data = get_wdq(w_dataset)
    k_count = len(k_data)
    w_count = len(w_data)

    k_only = {}
    mismatch = []
    for uuid, qid in k_data.iteritems():
        if qid in w_data.keys():
            if w_data[qid] != uuid:
                mismatch.append((uuid, qid, w_data[qid]))
            del w_data[qid]
        else:
            k_only[uuid] = qid

    for qid, uuid in w_data.iteritems():
        if uuid in k_only.keys():
            mismatch.append((qid, uuid, k_only[uuid]))
            del k_only[uuid]

    # prepare response
    status = {
        'wdq_time': time,
        'kulturnav_hits': k_count,
        'kulturnav_dataset': k_dataset,
        'wikidata_hits': w_count,
        'wikidata_dataset': w_dataset,
        'mismatches': len(mismatch)
    }
    response = {
        '_status': status,
        'kulturnav_only': k_only,
        'wikidata_only': w_data,
        'mismatches': mismatch
    }
    return response


def test_all(out_dir):
    """Run test for all data."""
    run_test(
        dataset_id=None,
        dataset_q=None,
        owner_q=None,
        outfile='%ssynk-All.json' % out_dir
    )


def test_ArkDes(out_dir):
    """Run test for ArkDes data."""
    run_test(
        dataset_id='2b7670e1-b44e-4064-817d-27834b03067c',
        dataset_q='Q17373699',
        owner_q='Q4356728',
        outfile='%ssynk-Arkdes.json' % out_dir
    )


def test_SMM(out_dir):
    """Run test for SMM data."""
    dataset_id = ['9a816089-2156-42ce-a63a-e2c835b20688',
                  'c43d8eba-030b-4542-b1ac-6a31a0ba6d00',
                  '51f2bd1f-7720-4f03-8d95-c22a85d26bbb',
                  'c6a7e732-650f-4fdb-a34c-366088f1ff0e',
                  '6a98b348-8c90-4ccc-9da7-42351bd4feb7',
                  'fb4faa4b-984a-404b-bdf7-9c24a298591e',
                  'b0fc1427-a9ab-4239-910a-cd02c02c4a76']
    dataset_q = ['Q20734454',
                 'Q20103697',
                 'Q20742915',
                 'Q20669482',
                 'Q20742975',
                 'Q20742782',
                 'Q20669386']
    run_test(
        dataset_id=dataset_id,
        dataset_q=dataset_q,
        owner_q='Q10677695',
        outfile='%ssynk-SMM.json' % out_dir
    )


def test_NatMus(out_dir):
    """Run test for NatMus data."""
    run_test(
        dataset_id='c6efd155-8433-4c58-adc9-72db80c6ce50',
        dataset_q='Q22681075',
        owner_q='Q842858',
        outfile='%ssynk-Natmus.json' % out_dir
    )


def run_test(dataset_id, dataset_q, owner_q, outfile):
    """Run a test for a given set of parameters and output.

    @param dataset_id: kulturnav uuid of the dataset
    @type dataset_id: str or list of str
    @param dataset_q: Wikidata qid of the dataset
    @type dataset_q: str or list of str
    @param owner_q: Wikidata qid of the "owner" organisation
    @type owner_q: str
    @param outfile: file to write to
    @type outfile: str
    """
    response = compare(dataset_id, dataset_q)
    response['_status']['source_references'] = get_references(owner_q)
    f = open(outfile, 'w')
    f.write(json.dumps(response))
    f.close()

if __name__ == "__main__":
    import sys
    usage = "Usage: python synkedKulturnav.py outdir\n" \
            "\toutdir(optional): dir in which to stick output. " \
            "Defaults to current."
    argv = sys.argv[1:]
    out_dir = './'
    if len(argv) == 1:
        out_dir = argv[0]
    test_all(out_dir)
    test_ArkDes(out_dir)
    test_SMM(out_dir)
    test_NatMus(out_dir)
