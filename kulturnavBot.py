#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statments about Architects in KulturNav.
    by Lokal_Profil

Based on http://git.wikimedia.org/summary/labs%2Ftools%2Fmultichill.git
    /bot/wikidata/rijksmuseum_import.py by Multichill

TODO: Should also get json for any items identified on wikidata but not
      on kulturnav
      Follow redirects

"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib
import pywikibot.data.wikidataquery as wdquery

# Needed only for WikidataStringSearch
import os.path
from WikidataStringSearch import WikidataStringSearch

EDIT_SUMMARY = u'kulturnavBot'
KULTURNAV_ID_P = '1248'
DATASET_Q = '17373699'
STATED_IN_P = '248'
IS_A_P = '31'
PUBLICATION_P = '577'
ARCHITECT_Q = '42973'


class KulturnavBot:
    """
    A bot to enrich and create information on Wikidata based on KulturNav info
    """
    def __init__(self, dictGenerator):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()

        self.architectIds = self.fillCache()

        # check if I am running on labs, for WikidataStringSearch

        self.onLabs = os.path.isfile(os.path.expanduser("~") + "/replica.my.cnf")
        if self.onLabs:
            self.wdss = WikidataStringSearch()

    def fillCache(self, queryoverride=u'', cacheMaxAge=0):
        """
        Query Wikidata to fill the cache of monuments we already have an object for
        """
        result = {}
        if queryoverride:
            query = queryoverride
        else:
            query = u'CLAIM[%s]' % KULTURNAV_ID_P
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(KULTURNAV_ID_P), ])

        if data.get('status').get('error') == 'OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(KULTURNAV_ID_P))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[prop[2]] = prop[0]

            if expectedItems == len(result):
                pywikibot.output('I now have %s items in cache' % expectedItems)

        return result

    def run(self, cutoff=None):
        """
        Starts the robot
        param cutoff: if present limits the number of records added in one go
        """
        count = 1
        for architect in self.generator:
            # print count, cutoff
            if cutoff and count > cutoff:
                break
            # Valuesworth searching for
            values = {u'dbpedia-owl:deathPlace': None,
                      u'dbpprop:deathDate': None,
                      u'dbpedia-owl:birthPlace': None,
                      u'dbpprop:birthDate': None,
                      u'foaf:firstName': None,
                      u'foaf:gender': None,
                      u'foaf:lastName': None,
                      u'foaf:name': None,
                      u'dcterms:identifier': None,
                      u'dcterms:modified': None,
                      u'wikidata': None,
                      u'libris-id': None}

            for entries in architect[u'@graph']:
                if u'sameAs' in entries.keys():
                    if type(entries[u'sameAs']) in (unicode, str):
                        # type changes depending on if it is one or many
                        # reported upstream
                        entries[u'sameAs'] = [entries[u'sameAs'], ]
                    for sa in entries[u'sameAs']:
                        if u'wikidata' in sa:
                            values[u'wikidata'] = sa.split('/')[-1]
                        elif u'libris.kb.se/auth/' in sa:
                            values[u'libris-id'] = sa.split('/')[-1]
                # since I have no clue which order these come in
                for k, v in values.iteritems():
                    if k in entries.keys() and v is None:
                        values[k] = entries[k]

            # print values
            # convert these to potential claims
            protoclaims = {u'P31': pywikibot.ItemPage(self.repo, u'Q5'),
                           u'P106': pywikibot.ItemPage(self.repo, u'Q%s' % ARCHITECT_Q),
                           u'P20': None,
                           u'P570': None,
                           u'P19': None,
                           u'P569': None,
                           u'P735': None,
                           u'P21': None,
                           u'P734': None,
                           u'P1477': None,
                           u'P1248': None,
                           u'P906': None}

            if values[u'dbpedia-owl:deathPlace']:
                protoclaims[u'P20'] = self.dbpedia2Wikidata(values[u'dbpedia-owl:deathPlace'])
            if values[u'dbpprop:deathDate']:
                protoclaims[u'P570'] = self.dbDate(values[u'dbpprop:deathDate'])
            if values[u'dbpedia-owl:birthPlace']:
                protoclaims[u'P19'] = self.dbpedia2Wikidata(values[u'dbpedia-owl:birthPlace'])
            if values[u'dbpprop:birthDate']:
                protoclaims[u'P569'] = self.dbDate(values[u'dbpprop:birthDate'])
            if values[u'foaf:firstName']:
                protoclaims[u'P735'] = self.dbName(values[u'foaf:firstName'], u'firstName')
            if values[u'foaf:gender']:
                protoclaims[u'P21'] = self.dbGender(values[u'foaf:gender'])
            if values[u'foaf:lastName']:
                protoclaims[u'P734'] = self.dbName(values[u'foaf:lastName'], u'lastName')
            if values[u'libris-id']:
                protoclaims[u'P906'] = values[u'libris-id']
            if values[u'dcterms:identifier']:
                protoclaims[u'P%s' % KULTURNAV_ID_P] = values[u'dcterms:identifier']

            # print u'%s: %s' % (values[u'wikidata'], protoclaims)

            # get the "last modified" timestamp
            date = self.dbDate(values[u'dcterms:modified'])

            # find the matching wikidata item
            # check wikidata first, then kulturNav
            architectItem = None
            if values[u'dcterms:identifier'] in self.architectIds:
                architectItemTitle = u'Q%s' % (self.architectIds.get(values[u'dcterms:identifier']),)
                if values[u'wikidata'] != architectItemTitle:
                    pywikibot.output(u'Identifier missmatch (skipping): %s, %s, %s' % (values[u'dcterms:identifier'], values[u'wikidata'], architectItemTitle))
                    continue
            else:
                architectItemTitle = values[u'wikidata']
            architectItem = pywikibot.ItemPage(self.repo, title=architectItemTitle)
            # TODO: check if redirect, if so update target

            # Add information if a match was found
            if architectItem and architectItem.exists():

                # make sure it is not matched to a group of people
                if self.hasClaim('P%s' % IS_A_P, pywikibot.ItemPage(self.repo, u'Q16334295'), architectItem):
                    pywikibot.output(u'%s is matched to a group of people, FIXIT' % values[u'wikidata'])
                    continue

                # add name as alias (if not the same as lable or existing alias)
                if values[u'foaf:name']:
                    pass  # This should either be added as P1477 or as an alias IFF not already in the lable/alias

                # add each property (if new) and source it
                for pcprop, pcvalue in protoclaims.iteritems():
                    if pcvalue:
                        if isinstance(pcvalue, unicode) and pcvalue in (u'somevalue', u'novalue'):  # special cases
                            self.addNewSpecialClaim(pcprop, pcvalue, architectItem, date)
                        else:
                            self.addNewClaim(pcprop, pcvalue, architectItem, date)
            # allow for limited runs
            count += 1

        # done
        pywikibot.output(u'Went over %d entries' % count)

    # Kulturnavspecific ones
    def dbpedia2Wikidata(self, item):
        """
        Converts a dbpedia reference to the equivalent wikidata item, if present
        param item: dict with @language, @value keys
        """
        if not all(x in item.keys() for x in (u'@value', u'@language')):
            print u'invalid dbpedia entry: %s' % item
            exit(1)

        site = pywikibot.Site(item[u'@language'], 'wikipedia')  # any site will work, this is just an example
        page = pywikibot.Page(site, item[u'@value'])
        if u'wikibase_item' in page.properties() and page.properties()[u'wikibase_item']:
            return pywikibot.ItemPage(self.repo, page.properties()[u'wikibase_item'])

    def dbDate(self, item):
        """
        Given a dbpprop date object (1922-09-17Z or 2014-07-11T08:14:46Z)
        this returns the equivalent pywikibot.WbTime object
        """
        item = item[u'@value'][:len('YYYY-MM-DD')].split('-')
        if len(item) == 3 and all(self.is_int(x) for x in item):
            # 1921-09-17Z or 2014-07-11T08:14:46Z
            return pywikibot.WbTime(year=int(item[0]), month=int(item[1]), day=int(item[2]))
        elif len(item) == 1 and self.is_int(item[0][:len('YYYY')]):
            # 1921Z
            return pywikibot.WbTime(year=int(item[0][:len('YYYY')]))
        elif len(item) == 2 and all(self.is_int(x) for x in (item[0], item[1][:len('MM')])):
            # 1921-09Z
            return pywikibot.WbTime(year=int(item[0]), month=int(item[1][:len('MM')]))
        else:
            print u'invalid dbpprop date entry: %s' % item
            exit(1)

    def dbGender(self, item):
        """
        Simply matches gender values to Q items
        """
        known = {u'male': u'Q6581097',
                 u'female': u'Q6581072',
                 u'unknown': u'somevalue'}  # a special case
        if item not in known.keys():
            print u'invalid gender entry: %s' % item
            return

        if known[item] in (u'somevalue', u'novalue'):
            return known[item]
        else:
            return pywikibot.ItemPage(self.repo, known[item])

    def searchGenerator(self, text, language):
        for q in self.wdss.search(text, language=language):
            yield pywikibot.ItemPage(self.repo, q)

    def dbName(self, name, typ):
        """
        Given a plaintext name (first or last) this checks if there is
        a matching object of the right type
        param name = {'@language': 'xx', '@value': 'xxx'}
        """
        prop = {u'lastName': (u'Q101352',),
                u'firstName': (u'Q12308941', u'Q11879590', u'Q202444')}

        # Skip any empty values
        if len(name['@value'].strip()) == 0:
            return

        # search for potential matches
        if self.onLabs:
            objgen = pagegenerators.PreloadingItemGenerator(
                        self.searchGenerator(
                            name['@value'], name['@language']))
            matches = []
            for obj in objgen:
                if u'P%s' % IS_A_P in obj.get().get('claims'):
                    # print 'claims:', obj.get().get('claims')[u'P31']
                    values = obj.get().get('claims')[u'P%s' % IS_A_P]
                    for v in values:
                        # print u'val:', v.getTarget()
                        if v.getTarget().title() in prop[typ]:
                            matches.append(obj)
            if len(matches) == 1:
                return matches[0]

        else:
            objgen = pagegenerators.PreloadingItemGenerator(
                        pagegenerators.WikidataItemGenerator(
                            pagegenerators.SearchPageGenerator(
                                name['@value'], step=None, total=10, namespaces=[0], site=self.repo)))

            # check if P31 and then if any of prop[typ] in P31
            for obj in objgen:
                # print obj.title()
                if name['@value'] in (obj.get().get('labels').get('en'),
                                      obj.get().get('labels').get('sv'),
                                      obj.get().get('aliases').get('en'),
                                      obj.get().get('aliases').get('sv')):
                    # print 'labels en:', obj.get().get('labels').get('en')
                    # print 'labels sv:', obj.get().get('labels').get('sv')
                    # Check if right type of object
                    if u'P%s' % IS_A_P in obj.get().get('claims'):
                        # print 'claims:', obj.get().get('claims')[u'P31']
                        values = obj.get().get('claims')[u'P%s' % IS_A_P]
                        for v in values:
                            # print u'val:', v.getTarget()
                            if v.getTarget().title() in prop[typ]:
                                return obj

    @staticmethod
    def is_int(s):
        try:
            int(s)
            return True
        except (ValueError, TypeError):
            return False

    def addReference(self, architectItem, claim, date, prop):
        """
        Add a reference with a stated in object and a retrieval date
        param date: must be a pywikibot.WbTime object
        """
        statedin = pywikibot.Claim(self.repo, u'P%s' % STATED_IN_P)
        itis = pywikibot.ItemPage(self.repo, u'Q%s' % DATASET_Q)
        statedin.setTarget(itis)

        # check if already present
        if self.hasRef(u'P%s' % STATED_IN_P, itis, claim):
            return False

        # if not then add
        retrieved = pywikibot.Claim(self.repo, u'P%s' % PUBLICATION_P)
        retrieved.setTarget(date)

        try:
            claim.addSources([statedin, retrieved])  # writes to database
            pywikibot.output('Adding reference claim to %s in %s' % (prop, architectItem))
            return True
        except pywikibot.data.api.APIError, e:
            if e.code == u'modification-failed':
                pywikibot.output(u'modification-failed error: ref to %s in %s' % (prop, architectItem))
                return False
            else:
                pywikibot.output(e)
                exit(1)

    # some more generic wikidata methods
    @staticmethod
    def hasRef(prop, itis, claim):
        """
        Checks if ref is already present
        """
        if claim.sources:
            for i in range(0, len(claim.sources)):
                if prop in claim.sources[i].keys():
                    for s in claim.sources[i][prop]:
                        if s.getTarget() == itis:
                            return True
                        # else:
                        #    pywikibot.output(s.getTarget())
        return False

    @staticmethod
    def hasClaim(prop, itis, item):
        """
        Checks if the claim already exists, if so returns that claim
        """
        if prop in item.claims.keys():
            for claim in item.claims[prop]:
                if claim.getTarget() == itis:
                    return claim
        return None

    @staticmethod
    def hasSpecialClaim(prop, snaktype, item):
        """
        hasClaim() in the special case of 'somevalue' and 'novalue'
        """
        if prop in item.claims.keys():
            for claim in item.claims[prop]:
                if claim.getSnakType() == snaktype:
                    return claim
        return None

    def addNewClaim(self, prop, itis, item, date):
        """
        Given an item, a property and a claim (in the itis format) this
        either adds the sourced claim, or sources it if already existing
        prop: a PXX code, unicode
        itis: a valid claim e.g. pywikibot.ItemPage(repo, "Q6581097")
        item: the item being checked
        """
        claim = pywikibot.Claim(self.repo, prop)
        claim.setTarget(itis)
        priorClaim = self.hasClaim(prop, itis, item)
        if priorClaim:
            self.addReference(item, priorClaim, date, prop)
        else:
            item.addClaim(claim)
            pywikibot.output('Adding %s claim to %s' % (prop, item))
            self.addReference(item, claim, date, prop)

    def addNewSpecialClaim(self, prop, snaktype, item, date):
        """
        addNewClaim() but for the special 'somevalue' and 'novalue'
        """
        if snaktype not in ['somevalue', 'novalue']:
            pywikibot.output('You passed a non-allowed snakvalue to addNewSpecialClaim(): %s' % snaktype)
            exit(1)
        claim = pywikibot.Claim(self.repo, prop)
        claim.setSnakType(snaktype)
        priorClaim = self.hasSpecialClaim(prop, snaktype, item)
        if priorClaim:
            self.addReference(item, priorClaim, date, prop)
        else:
            item.addClaim(claim)
            pywikibot.output('Adding %s claim to %s' % (prop, item))
            self.addReference(item, claim, date, prop)


def getKulturnavGenerator(maxHits=500):
    """
    Generator of the entries at Kulturnav based on a serch for all items
    of type person in the Architects dataset which contains wikidata as a
    sameAs value.
    """
    urls = {'http%3A%2F%2Fwww.wikidata.org%2Fentity%2FQ*': u'http://www.wikidata.org/entity/',
            'https%3A%2F%2Fwww.wikidata.org%2Fentity%2FQ*': u'https://www.wikidata.org/entity/'}
    searchurl = 'http://kulturnav.org/api/search/entityType:Person,entity.dataset_r:2b7670e1-b44e-4064-817d-27834b03067c,entity.sameAs_s:%s/%d/%d'
    queryurl = 'http://kulturnav.org/%s?format=application/ld%%2Bjson'

    # get all id's in KulturNav which link to wikidata
    wdDict = {}
    for q, u in urls.iteritems():
        offset = 0
        # overviewPage = json.load(urllib.urlopen(searchurl % (q, offset, maxHits)))
        searchPage = urllib.urlopen(searchurl % (q, offset, maxHits))
        searchData = searchPage.read()
        overviewPage = json.loads(searchData)

        while len(overviewPage) > 0:
            for o in overviewPage:
                sameAs = o[u'properties'][u'entity.sameAs']
                for s in sameAs:
                    if s[u'value'].startswith(u):
                        wdDict[o[u'uuid']] = s[u'value'][len(u):]
                        break
            # continue
            offset += maxHits
            searchPage = urllib.urlopen(searchurl % (q, offset, maxHits))
            searchData = searchPage.read()
            overviewPage = json.loads(searchData)

    # get the record for each of these entries
    for kulturnavId, wikidataId in wdDict.iteritems():
        # jsonData = json.load(urllib.urlopen(queryurl % kulturnavId))
        recordPage = urllib.urlopen(queryurl % kulturnavId)
        recordData = recordPage.read()
        jsonData = json.loads(recordData)
        if jsonData.get(u'@graph'):
            yield jsonData
        else:
            print jsonData


def main(cutoff=None, maxHits=250):
    kulturnavGenerator = getKulturnavGenerator(maxHits=maxHits)

    kulturnavBot = KulturnavBot(kulturnavGenerator)
    kulturnavBot.run(cutoff=cutoff)


if __name__ == "__main__":
    usage = u'Usage:\tpython kulturnavBot.py cutoff\n' \
            u'\twhere cutoff is an optional integer'
    import sys
    argv = sys.argv[1:]
    if len(argv) == 0:
        main()
    elif len(argv) == 1:
        main(cutoff=int(argv[0]))
    else:
        print usage
