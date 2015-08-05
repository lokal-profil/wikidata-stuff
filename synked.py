#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Quick bot for checking reciprocity of Wikidata-Kulturnav links

@todo: Add some type of simple htmloutput (e.g. bootstrap from json)
"""
import json
import urllib2


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


def testAll():
    """All"""
    DATASET_ID = None
    DATASET_Q = None
    response = compare(DATASET_ID, DATASET_Q)
    f = open('synk-All.json', 'w')
    f.write(json.dumps(response))
    f.close()


def testArkDes():
    """ArkDes"""
    DATASET_ID = '2b7670e1-b44e-4064-817d-27834b03067c'
    DATASET_Q = 'Q17373699'
    response = compare(DATASET_ID, DATASET_Q)
    f = open('synk-Arkdes.json', 'w')
    f.write(json.dumps(response))
    f.close()


def testSMM():
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
    response = compare(DATASET_ID, DATASET_Q)
    f = open('synk-SMM.json', 'w')
    f.write(json.dumps(response))
    f.close()

if __name__ == "__main__":
    testAll()
    testArkDes()
    testSMM()
