#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Quick bot for checking reciprocity of Wikidata-Kulturnav links

@todo: Add some type of simple htmloutput (e.g. bootstrap from json)
"""
import json
import urllib2
import urllib


def getWDQ(dataset=None, data=None):
    """
    Use wdq to find all links from Wikidata to Kulturnav
    @param dataset the qid (or list of qids) corresponding to a dataset
    @return tupple (timestamp, dict {qid: uuid})
    """
    # initialise if needed
    if data is None:
        data = {}

    # handle lists
    if isinstance(dataset, list):
        for d in dataset:
            time, data = getWDQ(dataset=d, data=data)
        return time, data

    # single query
    pid = '1248'
    claim = u'CLAIM[%s]' % pid
    if dataset is not None:
        claim += u'{CLAIM[972:%s]}' % dataset[1:]

    url = u'https://wdq.wmflabs.org/api?q=%s&props=%s' % (claim, pid)
    j = json.load(urllib2.urlopen(url))
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
        while len(j) > 0:
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


def getReferences(owner=None):
    """
    Ask the query service for the number of statments being sourced
    through Kulturnav.
    """
    baseUrl = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql?' \
              'format=json&query='
    query = "prefix wdt: <http://www.wikidata.org/prop/direct/>\n" \
            "prefix prov: <http://www.w3.org/ns/prov#>\n" \
            "prefix pr: <http://www.wikidata.org/prop/reference/>\n" \
            "PREFIX wd: <http://www.wikidata.org/entity/>\n" \
            "SELECT (count(?statement) as ?mentions) WHERE {\n" \
            "   ?statement prov:wasDerivedFrom ?ref .\n" \
            "   ?ref pr:P248 ?dataset .\n" \
            "   ?dataset wdt:P31 wd:Q1172284 .\n" \
            "   ?dataset wdt:P361 wd:Q16323066 .\n"
    if owner is not None:
        query += "   ?dataset wdt:P127 wd:%s .\n" % owner
    query += "}"

    # performe query
    j = json.load(urllib2.urlopen(baseUrl + urllib.quote(query)))
    return int(j['results']['bindings'][0]['mentions']['value'])


def compare(kDataset=None, wDataset=None):
    """
    Compare the links from Wikidata to Kulturnav and vice versa

    @param datasetK the uuid corresponding to a dataset
    @param datasetW the qid corresponding to a dataset

    @return dict {_status, kulturnav_only, wikidata_only, mismatches}
    """
    kData = getKulturnav(kDataset)
    time, wData = getWDQ(wDataset)
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
    """All"""
    DATASET_ID = None
    DATASET_Q = None
    response = compare(DATASET_ID, DATASET_Q)
    response['_status']['source_references'] = getReferences()
    f = open('%ssynk-All.json' % outDir, 'w')
    f.write(json.dumps(response))
    f.close()


def testArkDes(outDir):
    """ArkDes"""
    DATASET_ID = '2b7670e1-b44e-4064-817d-27834b03067c'
    DATASET_Q = 'Q17373699'
    OWNER_Q = 'Q4356728'
    response = compare(DATASET_ID, DATASET_Q)
    response['_status']['source_references'] = getReferences(OWNER_Q)
    f = open('%ssynk-Arkdes.json' % outDir, 'w')
    f.write(json.dumps(response))
    f.close()


def testSMM(outDir):
    """All SMM"""
    DATASET_ID = ['9a816089-2156-42ce-a63a-e2c835b20688',
                  'c43d8eba-030b-4542-b1ac-6a31a0ba6d00',
                  '51f2bd1f-7720-4f03-8d95-c22a85d26bbb',
                  'c6a7e732-650f-4fdb-a34c-366088f1ff0e',
                  '6a98b348-8c90-4ccc-9da7-42351bd4feb7',
                  'fb4faa4b-984a-404b-bdf7-9c24a298591e',
                  'b0fc1427-a9ab-4239-910a-cd02c02c4a76']
    DATASET_Q = ['Q20734454',
                 'Q20103697',
                 'Q20742915',
                 'Q20669482',
                 'Q20742975',
                 'Q20742782',
                 'Q20669386']
    OWNER_Q = 'Q10677695'
    response = compare(DATASET_ID, DATASET_Q)
    response['_status']['source_references'] = getReferences(OWNER_Q)
    f = open('%ssynk-SMM.json' % outDir, 'w')
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
