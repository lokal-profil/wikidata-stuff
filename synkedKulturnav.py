#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Quick bot for checking reciprocity of Wikidata-Kulturnav links

@todo: Add some type of simple htmloutput (e.g. bootstrap from json)
@todo: make use of WD.wdqLookup and/or wdqsLookup
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
    @rtype: tupple
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


def getKulturnav(dataset=None, data=None):
    """
    Use wdq to find all links from Wikidata to Kulturnav
    @param dataset the uuid corresponding to a dataset

    @return dict {uuid: qid}
    """
    # initialise if needed
    if data is None:
        data = {}

    # handle lists
    if isinstance(dataset, list):
        for d in dataset:
            getKulturnav(dataset=d, data=data)
        return data

    # single lookup
    batchSize = 250
    needles = (u'http://www.wikidata.org', 'https://www.wikidata.org')
    searchStr = u'*%2F%2Fwww.wikidata.org%2Fentity%2FQ*'
    matched_tags = ['entity.sameAs_s', 'concept.exactMatch_s']
    if dataset is None:
        dataset = ''
    else:
        dataset = 'entity.dataset_r:%s,' % dataset
    urlbase = u'http://kulturnav.org/api/search/%s' % dataset

    for match in matched_tags:
        offset = 0
        url = urlbase + u'%s:%s/' % (match, searchStr)
        j = json.load(urllib2.urlopen(url + '%d/%d' % (offset, batchSize)))
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
            offset += batchSize
            j = json.load(urllib2.urlopen(url + '%d/%d' % (offset, batchSize)))

    return data


def get_references(owner=None):
    """Query for the number of statments sourced through Kulturnav.

    @param owner: the Qid of the dataset owning organisation
    @type owner: str or None
    @return the number of sourced statment
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


def compare(kDataset=None, wDataset=None):
    """
    Compare the links from Wikidata to Kulturnav and vice versa

    @param datasetK the uuid corresponding to a dataset
    @param datasetW the qid corresponding to a dataset

    @return dict {_status, kulturnav_only, wikidata_only, mismatches}
    """
    kData = getKulturnav(kDataset)
    time, wData = get_wdq(wDataset)
    kCount = len(kData)
    wCount = len(wData)

    kOnly = {}
    mismatch = []
    for uuid, qid in kData.iteritems():
        if qid in wData.keys():
            if wData[qid] != uuid:
                mismatch.append((uuid, qid, wData[qid]))
            del wData[qid]
        else:
            kOnly[uuid] = qid

    for qid, uuid in wData.iteritems():
        if uuid in kOnly.keys():
            mismatch.append((qid, uuid, kOnly[uuid]))
            del kOnly[uuid]

    # prepare response
    status = {'wdq_time': time,
              'kulturnav_hits': kCount,
              'kulturnav_dataset': kDataset,
              'wikidata_hits': wCount,
              'wikidata_dataset': wDataset,
              'mismatches': len(mismatch)}
    response = {'_status': status,
                'kulturnav_only': kOnly,
                'wikidata_only': wData,
                'mismatches': mismatch}
    return response


def testAll(outDir):
    """Run test for all data."""
    outfile = '%ssynk-All.json' % outDir
    run_test(None, None, None, outfile)


def testArkDes(outDir):
    """Run test for ArkDes data."""
    dataset_id = '2b7670e1-b44e-4064-817d-27834b03067c'
    dataset_q = 'Q17373699'
    owner_q = 'Q4356728'
    outfile = '%ssynk-Arkdes.json' % outDir
    run_test(dataset_id, dataset_q, owner_q, outfile)


def testSMM(outDir):
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
    owner_q = 'Q10677695'
    outfile = '%ssynk-SMM.json' % outDir
    run_test(dataset_id, dataset_q, owner_q, outfile)


def testNatMus(outDir):
    """Run test for NatMus data."""
    dataset_id = 'c6efd155-8433-4c58-adc9-72db80c6ce50'
    dataset_q = 'Q22681075'
    owner_q = 'Q842858'
    outfile = '%ssynk-Natmus.json' % outDir
    run_test(dataset_id, dataset_q, owner_q, outfile)


def run_test(dataset_id, dataset_q, owner_q, outfile):
    """Run a test for a given set of parameters and output.

    @todo
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
    outDir = './'
    if len(argv) == 1:
        outDir = argv[0]
    testAll(outDir)
    testArkDes(outDir)
    testSMM(outDir)
    testNatMus(outDir)
