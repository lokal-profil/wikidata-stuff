#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and sourced statements about entities also present in
KulturNav (https://www.wikidata.org/wiki/Q16323066).

Based on http://git.wikimedia.org/summary/labs%2Ftools%2Fmultichill.git
    /bot/wikidata/rijksmuseum_import.py by Multichill

Author: Lokal_Profil
License: MIT

See https://github.com/lokal-profil/wikidata-stuff/issues for TODOs
"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib2
import pywikibot.data.wikidataquery as wdquery

# Needed only for WikidataStringSearch
import os.path
from WikidataStringSearch import WikidataStringSearch

FOO_BAR = u'A multilingual result (or one with multiple options) was ' \
          u'encountered but I have yet to support that functionality'


class KulturnavBot(object):
    """
    A bot to enrich and create information on Wikidata based on KulturNav info
    """
    EDIT_SUMMARY = 'KulturnavBot'
    KULTURNAV_ID_P = '1248'
    DATASET_Q = None
    STATED_IN_P = '248'
    IS_A_P = '31'
    PUBLICATION_P = '577'
    CATALOG_P = '972'
    DATASET_ID = None
    ENTITY_TYPE = None
    MAP_TAG = None

    def __init__(self, dictGenerator):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()

        self.itemIds = self.fillCache()

        # check if I am running on labs, for WikidataStringSearch

        self.onLabs = os.path.isfile(
            os.path.expanduser("~") +
            "/replica.my.cnf")
        if self.onLabs:
            self.wdss = WikidataStringSearch()

    @classmethod
    def setVariables(cls, dataset_q, dataset_id, entity_type,
                     map_tag, edit_summary=None):
        cls.DATASET_Q = dataset_q
        cls.DATASET_ID = dataset_id
        cls.ENTITY_TYPE = entity_type
        cls.MAP_TAG = map_tag
        if edit_summary is not None:
            cls.EDIT_SUMMARY = edit_summary

    def fillCache(self, queryoverride=u'', cacheMaxAge=0):
        """
        Query Wikidata to fill the cache of entities which have an object
        """
        result = {}
        if queryoverride:
            query = queryoverride
        else:
            query = u'CLAIM[%s]' % self.KULTURNAV_ID_P
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(self.KULTURNAV_ID_P), ])

        if data.get('status').get('error') == 'OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(self.KULTURNAV_ID_P))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[prop[2]] = prop[0]

            if expectedItems == len(result):
                pywikibot.output('I now have %s items in cache' %
                                 expectedItems)

        return result

    def run(self, cutoff=None):
        """
        Starts the robot
        param cutoff: if present limits the number of records added in one go
        """
        raise NotImplementedError("Please Implement this method")

    # KulturNav specific ones
    def dbpedia2Wikidata(self, item):
        """
        Converts a dbpedia reference to the equivalent Wikidata item,
        if present
        param item: dict with @language, @value keys
        """
        if KulturnavBot.foobar(item):
            return
        if not all(x in item.keys() for x in (u'@value', u'@language')):
            print u'invalid dbpedia entry: %s' % item
            exit(1)

        # any site will work, this is just an example
        site = pywikibot.Site(item[u'@language'], 'wikipedia')
        page = pywikibot.Page(site, item[u'@value'])
        if u'wikibase_item' in page.properties() and \
           page.properties()[u'wikibase_item']:
            return pywikibot.ItemPage(
                self.repo,
                page.properties()[u'wikibase_item'])

    def dbDate(self, item):
        """
        Given a dbpprop date object (1922-09-17Z or 2014-07-11T08:14:46Z)
        this returns the equivalent pywikibot.WbTime object
        """
        item = item[:len('YYYY-MM-DD')].split('-')
        if len(item) == 3 and all(self.is_int(x) for x in item):
            # 1921-09-17Z or 2014-07-11T08:14:46Z
            d = int(item[2])
            if d == 0:
                d = None
            m = int(item[1])
            if m == 0:
                m = None
            return pywikibot.WbTime(
                year=int(item[0]),
                month=m,
                day=d)
        elif len(item) == 1 and self.is_int(item[0][:len('YYYY')]):
            # 1921Z
            return pywikibot.WbTime(year=int(item[0][:len('YYYY')]))
        elif len(item) == 2 and \
                all(self.is_int(x) for x in (item[0], item[1][:len('MM')])):
            # 1921-09Z
            m = int(item[1][:len('MM')])
            if m == 0:
                m = None
            return pywikibot.WbTime(
                year=int(item[0]),
                month=m)
        else:
            pywikibot.output(u'invalid dbpprop date entry: %s' % item)
            exit(1)

    def dbGender(self, item):
        """
        Simply matches gender values to Q items
        """
        known = {u'male': u'Q6581097',
                 u'female': u'Q6581072',
                 u'unknown': u'somevalue'}  # a special case
        if item not in known.keys():
            pywikibot.output(u'invalid gender entry: %s' % item)
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
        if KulturnavBot.foobar(name):
            return
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
                if u'P%s' % self.IS_A_P in obj.get().get('claims'):
                    # print 'claims:', obj.get().get('claims')[u'P31']
                    values = obj.get().get('claims')[u'P%s' % self.IS_A_P]
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
                        name['@value'], step=None, total=10,
                        namespaces=[0], site=self.repo)))

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
                    if u'P%s' % self.IS_A_P in obj.get().get('claims'):
                        # print 'claims:', obj.get().get('claims')[u'P31']
                        values = obj.get().get('claims')[u'P%s' % self.IS_A_P]
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

    def addReference(self, item, claim, date, prop):
        """
        Add a reference with a stated in object and a retrieval date
        param date: must be a pywikibot.WbTime object
        """
        statedin = pywikibot.Claim(self.repo, u'P%s' % self.STATED_IN_P)
        itis = pywikibot.ItemPage(self.repo, u'Q%s' % self.DATASET_Q)
        statedin.setTarget(itis)

        # check if already present (with any date)
        if self.hasRef(u'P%s' % self.STATED_IN_P, itis, claim):
            return False

        # if not then add
        retrieved = pywikibot.Claim(self.repo, u'P%s' % self.PUBLICATION_P)
        retrieved.setTarget(date)

        try:
            claim.addSources([statedin, retrieved])  # writes to database
            pywikibot.output('Adding reference claim to %s in %s' %
                             (prop, item))
            return True
        except pywikibot.data.api.APIError, e:
            if e.code == u'modification-failed':
                pywikibot.output(u'modification-failed error: '
                                 u'ref to %s in %s' % (prop, item))
                return False
            else:
                pywikibot.output(e)
                exit(1)

    def addLabelOrAlias(self, nameObj, item):
        """
        Adds a name as either a label (if none) or an alias

        param nameObj = {'@language': 'xx', '@value': 'xxx'}
        """
        if KulturnavBot.foobar(nameObj):
            return
        lang = nameObj['@language']
        name = nameObj['@value']
        summary = u'%s: Added %s in [%s]' % (self.EDIT_SUMMARY, '%s', lang)
        # look at label
        if not item.labels or lang not in item.labels.keys():
            # add name to label
            labels = {lang: name}
            summary %= 'label'
            item.editLabels(labels, summary=summary)
            pywikibot.output(summary)
        elif name != item.labels[lang]:
            # look at aliases
            summary %= 'alias'
            if not item.aliases or lang not in item.aliases.keys():
                aliases = {lang: [name, ]}
                item.editAliases(aliases, summary=summary)
                pywikibot.output(summary)
            elif name not in item.aliases[lang]:
                aliases = {lang: item.aliases[lang]}
                aliases[lang].append(name)
                item.editAliases(aliases, summary=summary)
                pywikibot.output(summary)

    # some more generic Wikidata methods
    def hasRef(self, prop, itis, claim):
        """
        Checks if a given reference is already present at the given claim
        """
        if claim.sources:
            for i in range(0, len(claim.sources)):
                if prop in claim.sources[i].keys():
                    for s in claim.sources[i][prop]:
                        if self.bypassRedirect(s.getTarget()) == itis:
                            return True
                        # else:
                        #    pywikibot.output(s.getTarget())
        return False

    def bypassRedirect(self, item):
        """
        Checks if an item is a Redirect, and if so returns the
        target item instead of the original.
        This is needed for itis comparisons

        Not that this should either be called before an
        item.exists()/item.get() call or a new one must be made afterwards

        return ItemPage
        """
        # skip all non-ItemPage
        if not isinstance(item, pywikibot.ItemPage):
            return item

        if item.isRedirectPage():
            targetPage = item.getRedirectTarget()
            # targetPage is a Page, so use title to make an ItemPage
            target = pywikibot.ItemPage(self.repo, targetPage.title())
            return target
        else:
            return item

    def addQualifier(self, item, claim, prop, itis):
        """
        Check if a qualifier is present at the given claim,
        otherwise add it

        Known issue: This will qualify an already referenced claim
            this must therefore be tested before
        """
        # check if already present
        if self.hasQualifier(prop, itis, claim):
            return False

        qClaim = pywikibot.Claim(self.repo, prop)
        qClaim.setTarget(itis)

        try:
            claim.addQualifier(qClaim)  # writes to database
            pywikibot.output('Adding qualifier to %s in %s' % (prop, item))
            return True
        except pywikibot.data.api.APIError, e:
            if e.code == u'modification-failed':
                pywikibot.output(u'modification-failed error: '
                                 u'qualifier to %s in %s' % (prop, item))
                return False
            else:
                pywikibot.output(e)
                exit(1)

    def hasQualifier(self, prop, itis, claim):
        """
        Checks if qualifier is already present
        """
        if claim.qualifiers:
            if prop in claim.qualifiers.keys():
                for s in claim.qualifiers[prop]:
                    if self.bypassRedirect(s.getTarget()) == itis:
                        return True
                    # else:
                    #    pywikibot.output(s.getTarget())
        return False

    def hasClaim(self, prop, itis, item):
        """
        Checks if the claim already exists, if so returns that claim
        """
        if prop in item.claims.keys():
            for claim in item.claims[prop]:
                if self.bypassRedirect(claim.getTarget()) == itis:
                    return claim
        return None

    def hasSpecialClaim(self, prop, snaktype, item):
        """
        hasClaim() in the special case of 'somevalue' and 'novalue'
        """
        if prop in item.claims.keys():
            for claim in item.claims[prop]:
                if claim.getSnakType() == snaktype:
                    return claim
        return None

    def addNewClaim(self, prop, itis, item, date, qual=None, snaktype=None):
        """
        Given an item, a property and a claim (in the itis format) this
        either adds the sourced claim, or sources it if already existing

        Known issues:
        * Only allows one qualifier to be added
        * Will source a claim with other qualifiers

        prop: a PXX code, unicode
        itis: a valid claim e.g. pywikibot.ItemPage(repo, "Q6581097")
        item: the item being checked
        qual: optional qualifier to add to claim, dict{prop, itis, force}
            prop and itis: are formulated as those for the claim
            force: (bool) add even to a sourced claim
        snaktype: somevalue/novalue
            (should only ever be set through addNewSpecialClaim)
        """
        claim = pywikibot.Claim(self.repo, prop)

        # handle special cases
        if snaktype is None:
            claim.setTarget(itis)
            priorClaim = self.hasClaim(prop, itis, item)
        else:
            claim.setSnakType(snaktype)
            priorClaim = self.hasSpecialClaim(prop, snaktype, item)

        validQualifier = (
            qual is not None and
            isinstance(qual, dict) and
            set(qual.keys()) == set(['prop', 'itis', 'force'])
        )

        if priorClaim and validQualifier:
            # cannot add a qualifier to a previously sourced claim
            if not priorClaim.sources:
                # if unsourced
                self.addQualifier(item, priorClaim,
                                  qual[u'prop'], qual[u'itis'])
                self.addReference(item, priorClaim, date, prop)
            elif self.hasQualifier(qual[u'prop'], qual[u'itis'], priorClaim):
                # if qualifier already present
                self.addReference(item, priorClaim, date, prop)
            elif qual[u'force']:
                # if force is set
                self.addQualifier(item, priorClaim,
                                  qual[u'prop'], qual[u'itis'])
                self.addReference(item, priorClaim, date, prop)
            else:
                # add new qualified claim
                item.addClaim(claim)
                pywikibot.output('Adding %s claim to %s' % (prop, item))
                self.addQualifier(item, claim, qual[u'prop'], qual[u'itis'])
                self.addReference(item, claim, date, prop)
        elif priorClaim:
            self.addReference(item, priorClaim, date, prop)
        else:
            item.addClaim(claim)
            pywikibot.output('Adding %s claim to %s' % (prop, item))
            if validQualifier:
                self.addQualifier(item, claim, qual[u'prop'], qual[u'itis'])
            self.addReference(item, claim, date, prop)

    def addNewSpecialClaim(self, prop, snaktype, item, date, qual=None):
        """
        addNewClaim() but for the special 'somevalue' and 'novalue'
        """
        if snaktype not in ['somevalue', 'novalue']:
            pywikibot.output(u'You passed a non-allowed snakvalue to '
                             u'addNewSpecialClaim(): %s' % snaktype)
            exit(1)

        # pass it on to addNewClaim with itis=None
        self.addNewClaim(
            prop,
            None,
            item,
            date,
            qual=qual,
            snaktype=snaktype)

    @classmethod
    def getKulturnavGenerator(cls, maxHits=500):
        """
        Generator of the entries at KulturNav based on a search for all items
        of given type in the given dataset which contains Wikidata as a
        given value.
        """
        urls = {
            'http%3A%2F%2Fwww.wikidata.org%2Fentity%2FQ*': u'http://www.wikidata.org/entity/',
            'https%3A%2F%2Fwww.wikidata.org%2Fentity%2FQ*': u'https://www.wikidata.org/entity/'}
        searchurl = 'http://kulturnav.org/api/search/entityType:%s,entity.dataset_r:%s,%s:%s' % (
            cls.ENTITY_TYPE,
            cls.DATASET_ID,
            cls.MAP_TAG,
            '%s/%d/%d')
        queryurl = 'http://kulturnav.org/%s?format=application/ld%%2Bjson'

        # get all id's in KulturNav which link to Wikidata
        wdDict = {}
        for q, u in urls.iteritems():
            offset = 0
            # overviewPage = json.load(urllib2.urlopen(searchurl % (q, offset, maxHits)))
            searchPage = urllib2.urlopen(searchurl % (q, offset, maxHits))
            searchData = searchPage.read()
            overviewPage = json.loads(searchData)

            while len(overviewPage) > 0:
                for o in overviewPage:
                    sameAs = o[u'properties'][cls.MAP_TAG[:cls.MAP_TAG.rfind('_')]]
                    for s in sameAs:
                        if s[u'value'].startswith(u):
                            wdDict[o[u'uuid']] = s[u'value'][len(u):]
                            break
                # continue
                offset += maxHits
                searchPage = urllib2.urlopen(searchurl % (q, offset, maxHits))
                searchData = searchPage.read()
                overviewPage = json.loads(searchData)

        # get the record for each of these entries
        for kulturnavId, wikidataId in wdDict.iteritems():
            # jsonData = json.load(urllib2.urlopen(queryurl % kulturnavId))
            recordPage = urllib2.urlopen(queryurl % kulturnavId)
            recordData = recordPage.read()
            jsonData = json.loads(recordData)
            if jsonData.get(u'@graph'):
                yield jsonData
            else:
                print jsonData

    @classmethod
    def main(cls, cutoff=None, maxHits=250):
        kulturnavGenerator = cls.getKulturnavGenerator(maxHits=maxHits)

        kulturnavBot = cls(kulturnavGenerator)
        kulturnavBot.run(cutoff=cutoff)

    @staticmethod
    def foobar(item):
        if isinstance(item, list):
            pywikibot.output(FOO_BAR)
            return True
        return False

if __name__ == "__main__":
    usage = u'Usage:\tpython kulturnavBot.py cutoff\n' \
            u'\twhere cutoff is an optional integer'
    import sys
    argv = sys.argv[1:]
    if len(argv) == 0:
        KulturnavBot.main()
    elif len(argv) == 1:
        KulturnavBot.main(cutoff=int(argv[0]))
    else:
        print usage
