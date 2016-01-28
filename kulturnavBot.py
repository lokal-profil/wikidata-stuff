#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and sourced statements about entities also present in
KulturNav (https://www.wikidata.org/wiki/Q16323066).

usage:
    python kulturnavBot.py [OPTIONS]

Based on http://git.wikimedia.org/summary/labs%2Ftools%2Fmultichill.git
    /bot/wikidata/rijksmuseum_import.py by Multichill

Author: Lokal_Profil
License: MIT

Options (may be omitted):
  -cutoff:INT       number of entries to process before terminating
  -maxHits:INT      number of items to request at a time from Kulturnav
                    (default 250)
  -delay:INT        seconds to delay between each kulturnav request
                    (default 0)

See https://github.com/lokal-profil/wikidata-stuff/issues for TODOs
"""
import json
import time
import pywikibot
import urllib2
from WikidataStuff import WikidataStuff as WD
import helpers
import re

FOO_BAR = u'A multilingual result (or one with multiple options) was ' \
          u'encountered but I have yet to support that functionality'


class Rule():
    """
    A class for encoding rules used by runLayout()
    """
    def __init__(self, keys, values, target, viaId=None):
        """
        keys: list|string|None of keys which must be present
              (in addition to value/target)
        values: a dict|None of key-value pairs which must be present
        target: the key for which the value is wanted
        viaId: if not None then the value of target should be matched to
               an @id entry where this key should be used
        """
        self.keys = []
        if keys is not None:
            self.keys += helpers.listify(keys)
        self.values = values
        if values is not None:
            self.keys += values.keys()
        self.target = target
        self.keys.append(target)
        self.viaId = viaId

    def __repr__(self):
        """Return a more complete string representation."""
        return u'Rule(%s, %s, %s, %s)' % (
            self.keys, self.values, self.target, self.viaId)


class KulturnavBot(object):
    """
    A bot to enrich and create information on Wikidata based on KulturNav info
    """
    EDIT_SUMMARY = 'KulturnavBot'
    KULTURNAV_ID_P = '1248'
    GEONAMES_ID_P = '1566'
    SWE_KOMMUNKOD_P = '525'
    SWE_COUNTYKOD_P = '507'
    PLACE_P = '276'
    TIME_P = '585'   # date
    DATASET_Q = None
    STATED_IN_P = '248'
    DISAMBIG_Q = '4167410'
    IS_A_P = '31'
    PUBLICATION_P = '577'
    CATALOG_P = '972'
    DATASET_ID = None
    ENTITY_TYPE = None
    MAP_TAG = None
    COUNTRIES = []  # a list of country Q's
    ADMIN_UNITS = []  # a list of municipality+county Q's
    locations = {}  # a dict of uuid to wikidata location matches
    current_uuid = ''  # for debugging

    def __init__(self, dictGenerator, verbose=False):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.
        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()
        self.cutoff = None
        self.verbose = verbose

        # trigger wdq query
        self.itemIds = helpers.fill_cache(self.KULTURNAV_ID_P)

        # set up WikidataStuff instance
        self.wd = WD(self.repo)

        # load lists
        self.COUNTRIES = self.wd.wdqLookup(u'TREE[6256][][31]')
        self.ADMIN_UNITS = self.wd.wdqLookup(u'TREE[15284][][31]')

    @classmethod
    def setVariables(cls, dataset_q, dataset_id, entity_type,
                     map_tag, edit_summary=None):
        cls.DATASET_Q = dataset_q
        cls.DATASET_ID = dataset_id
        cls.ENTITY_TYPE = entity_type
        cls.MAP_TAG = map_tag
        if edit_summary is not None:
            cls.EDIT_SUMMARY = edit_summary

    def run(self):
        """
        Starts the robot
        """
        raise NotImplementedError("Please Implement this method")

    def runLayout(self, datasetRules, datasetProtoclaims,
                  datasetSanityTest, label, shuffle):
        """
        The basic layout of a run. It should be called for a dataset
        specific run which sets the parameters.

        param datasetRules: a dict of additional Rules or values to look for
        param datasetProtoclaims: a function for populating protoclaims
        param datasetSanityTest: a function which must return true for
                                 results to be written to Wikidata
        param label: the key in values to be used for label/alias.
                     set to None to skip addNames()
        param shuffle: whether name/label/alias is shuffled or not
                       i.e. if name = last, first
        """
        count = 0
        for hit in self.generator:
            # print count, self.cutoff
            if self.cutoff and count >= self.cutoff:
                break
            # some type of feedback
            if count % 100 == 0 and count > 0:
                pywikibot.output('%d entries handled...' % count)
            # Required rules/values to search for
            rules = {
                u'identifier': None,
                u'modified': None,
                u'seeAlso': None,
                u'sameAs': None,
                u'exactMatch': None,
                # not expected
                u'wikidata': None,
                u'libris-id': None,
                u'viaf-id': None,
                u'getty-id': None
            }
            rules.update(datasetRules)

            # put together empty dict of values then populate
            values = {}
            for k in rules.keys():
                values[k] = None
            if not self.populateValues(values, rules, hit):
                # continue with next hit if problem was encounterd
                continue

            # find the matching wikidata item
            hitItem = self.wikidataMatch(values)
            self.current_uuid = values['identifier']

            # convert values to potential claims
            protoclaims = datasetProtoclaims(self, values)

            # kulturnav protoclaim incl. qualifier
            protoclaims[u'P%s' % self.KULTURNAV_ID_P] = \
                WD.Statement(values[u'identifier']).addQualifier(
                    WD.Qualifier(
                        P=self.CATALOG_P,
                        itis=pywikibot.ItemPage(
                            self.repo,
                            u'Q%s' % self.DATASET_Q)),
                    force=True)

            # authority control protoclaims
            if values[u'libris-id']:
                protoclaims[u'P906'] = WD.Statement(values[u'libris-id'])
            if values[u'viaf-id']:
                protoclaims[u'P214'] = WD.Statement(values[u'viaf-id'])
            if values[u'getty-id']:
                protoclaims[u'P1014'] = WD.Statement(values[u'getty-id'])

            # output info for testing
            if self.verbose:
                pywikibot.output(values)
                pywikibot.output(protoclaims)
                pywikibot.output(hitItem)

            # Add information if a match was found
            if hitItem and hitItem.exists():
                # if redirect then get target instead

                # make sure it passes the sanityTests
                if not self.sanityTest(hitItem):
                    continue
                if not datasetSanityTest(self, hitItem):
                    continue

                # add name as label/alias
                if label is not None:
                    self.addNames(values[label], hitItem, shuffle=shuffle)

                # get the "last modified" timestamp and construct a Reference
                date = helpers.ISO_to_WbTime(values[u'modified'])
                ref = self.makeRef(date)

                # add each property (if new) and source it
                self.addProperties(protoclaims, hitItem, ref)

            # allow for limited runs
            count += 1

        # done
        pywikibot.output(u'Handled %d entries' % count)

    def populateValues(self, values, rules, hit):
        """
        given a list of values and a kulturnav hit, populate the values
        and check if result is problem free

        param values: dict with keys and every value as None
        param rules: a dict with keys and values either:
            None: the exakt key is present in hit and its value is wanted
            a Rule: acording to the class above
        param hit: a kulturnav entry
        return bool problemFree
        """
        def hasKeys(needles, haystack):
            """
            checks if all the provided keys are present
            param needles: a list of strings
            param haystack: a dict
            return bool
            """
            for n in needles:
                if n not in haystack.keys():
                    return False
            return True

        def hasValues(needles, haystack):
            """
            checks if all the provided keys are present
            param needles: None or a dict of key-value pairs
            param haystack: a dict
            return bool
            """
            if needles is None:
                return True
            for n, v in needles.iteritems():
                if not haystack[n] == v:
                    return False
            return True

        ids = {}
        problemFree = True
        for entries in hit[u'@graph']:
            # populate ids for viaId rules
            if '@id' in entries.keys():
                if entries['@id'] in ids.keys():
                    pywikibot.output('Non-unique viaID key: \n%s\n%s' %
                                     (entries, ids[entries['@id']]))
                ids[entries['@id']] = entries
            # handle rules
            for key, rule in rules.iteritems():
                val = None
                if rule is None:
                    if key in entries.keys():
                        val = entries[key]
                elif hasKeys(rule.keys, entries):
                    if hasValues(rule.values, entries):
                        val = entries[rule.target]

                # test and register found value
                if val is not None:
                    if values[key] is None:
                        values[key] = val
                    else:
                        pywikibot.output(u'duplicate entries for %s' % key)
                        problemFree = False

        # convert values for viaId rules
        for key, rule in rules.iteritems():
            if rule is not None and rule.viaId is not None:
                if values[key] is not None and values[key] in ids.keys():
                    if rule.viaId in ids[values[key]].keys():
                        values[key] = ids[values[key]][rule.viaId]
                    else:
                        values[key] = None
        for key, rule in rules.iteritems():
            if rule is not None and \
                    rule.viaId is not None and \
                    values[key] is not None:
                if isinstance(values[key], list):
                    # for list deal with each at a time and return a list
                    results = []
                    for val in values[key]:
                        if val in ids.keys():
                            results.append(ids[val][rule.viaId])
                    values[key] = results
                elif values[key] in ids.keys():
                    values[key] = ids[values[key]][rule.viaId]

        # the minimum which must have been identified
        if values[u'identifier'] is None:
            pywikibot.output(u'Could not isolate the identifier from the '
                             u'KulturNav object! JSON layout must have '
                             u'changed. Crashing!')
            exit(1)

        # merge sameAs and exactMatch
        match = []
        # each can be None, a list or a str/unicode
        if values[u'sameAs'] is not None:
            if isinstance(values[u'sameAs'], (str, unicode)):
                values[u'sameAs'] = [values[u'sameAs'], ]
            match += values[u'sameAs']
        if values[u'exactMatch'] is not None:
            if isinstance(values[u'exactMatch'], (str, unicode)):
                values[u'exactMatch'] = [values[u'exactMatch'], ]
            match += values[u'exactMatch']

        # dig into sameAs/exactMatch and seeAlso
        for sa in match:
            if u'wikidata' in sa:
                values[u'wikidata'] = sa.split('/')[-1]
            elif u'libris-id' in values.keys() and \
                    u'libris.kb.se/auth/' in sa:
                values[u'libris-id'] = sa.split('/')[-1]
            elif u'viaf-id' in values.keys() and \
                    u'viaf.org/viaf/' in sa:
                values[u'viaf-id'] = sa.split('/')[-1]
            elif u'getty-id' in values.keys() and \
                    u'vocab.getty.edu/aat/' in sa:
                values[u'getty-id'] = sa.split('/')[-1]

        # we only care about seeAlso if we didn't find a Wikidata link
        if values[u'wikidata'] is None and values[u'seeAlso'] is not None:
            if isinstance(values[u'seeAlso'], (str, unicode)):
                values[u'seeAlso'] = [values[u'seeAlso'], ]
            for sa in values[u'seeAlso']:
                if u'wikipedia' in sa:
                    pywikibot.output(u'Found a Wikipedia link but no '
                                     u'Wikidata link: %s %s' %
                                     (sa, values[u'identifier']))
            problemFree = False

        if not problemFree:
            pywikibot.output(u'Found an issue with %s (%s), skipping' %
                             (values['identifier'], values['wikidata']))
        return problemFree

    def addStartEndStatement(self, itis, startVal, endVal):
        """
        Deprecated in favour of helpers.add_start_end_qualifiers
        """
        print 'call to deprecated KulturnavBot.addStartEndStatement()'
        return helpers.add_start_end_qualifiers(itis, startVal, endVal)

    def sanityTest(self, hitItem):
        """
        A generic sanitytest which should be run independent on dataset
        return bool
        """
        return self.withoutClaimTest(hitItem,
                                     self.IS_A_P,
                                     self.DISAMBIG_Q,
                                     u'disambiguation page')

    def withoutClaimTest(self, hitItem, P, Q, descr):
        """
        Base test that an item does not contain a particular claim
        parm hitItem: item to check
        param P: the property to look for
        param Q: the Q claim to look for
        param descr: a descriptive text
        return bool
        """
        P = u'P%s' % P.lstrip('P')
        Q = u'Q%s' % Q.lstrip('Q')
        testItem = pywikibot.ItemPage(self.repo, Q)
        if self.wd.hasClaim(P, testItem, hitItem):
            pywikibot.output(u'%s is matched to %s, '
                             u'FIXIT' % (hitItem.title(), descr))
            return False
        else:
            return True

    def withClaimTest(self, hitItem, P, Q, descr, orNone=True):
        """
        Base test that an item contains a certain claim
        parm hitItem: item to check
        param P: the property to look for
        param Q: (list) of Q claim to look for
        param descr: a descriptive text
        param orNone: if no Claim is also ok
        return bool
        """
        P = u'P%s' % P.lstrip('P')
        Q = helpers.listify(Q)
        testItems = []
        for q in Q:
            q = u'Q%s' % q.lstrip('Q')
            testItems.append(pywikibot.ItemPage(self.repo, q))
        # check claims
        if P in hitItem.claims.keys():
            for testItem in testItems:
                if self.wd.hasClaim(P, testItem, hitItem):
                    return True
            else:
                pywikibot.output(u'%s is identified as something other '
                                 u'than a %s. Check!' %
                                 (hitItem.title(), descr))
                return False
        elif orNone:  # no P claim
            return True

    def wikidataMatch(self, values):
        """
        Finds the matching wikidata item
        checks Wikidata first, then kulturNav

        return ItemPage|None the matching item
        """
        if values[u'identifier'] in self.itemIds:
            hitItemTitle = u'Q%s' % \
                (self.itemIds.get(values[u'identifier']),)
            if values[u'wikidata'] != hitItemTitle:
                # this may be caused by either being a redirect
                wd = pywikibot.ItemPage(self.repo, values[u'wikidata'])
                wi = pywikibot.ItemPage(self.repo, hitItemTitle)
                if wd.isRedirectPage() and wd.getRedirectTarget() == wi:
                    pass
                elif wi.isRedirectPage() and wi.getRedirectTarget() == wd:
                    pass
                else:
                    pywikibot.output(
                        u'Identifier missmatch (skipping): '
                        u'%s, %s, %s' % (values[u'identifier'],
                                         values[u'wikidata'],
                                         hitItemTitle))
                    return None
        elif values[u'wikidata']:
            hitItemTitle = values[u'wikidata']
        else:
            # no match found
            return None

        # create ItemPage, bypassing any redirect
        hitItem = self.wd.bypassRedirect(
            pywikibot.ItemPage(
                self.repo,
                hitItemTitle))
        # in case of redirect
        values[u'wikidata'] = hitItem.title()

        return hitItem

    def addNames(self, names, hitItem, shuffle=False):
        """
        Given a nameObj or a list of such this prepares them for
        addLabelOrAlias()

        param shuffle: bool if name order is last, first then this
                       creates a local rearranged copy
        """
        if names:
            if shuffle:
                namelist = []
                if isinstance(names, dict):
                    s = KulturnavBot.shuffleNames(names)
                    if s is not None:
                        namelist.append(s)
                elif isinstance(names, list):
                    for n in names:
                        s = KulturnavBot.shuffleNames(n)
                        if s is not None:
                            namelist.append(s)
                else:
                    pywikibot.output(u'unexpectedly formatted name'
                                     u'object: %s' % names)
                if len(namelist) > 0:
                    self.addLabelOrAlias(namelist, hitItem)
            else:
                self.addLabelOrAlias(names, hitItem)

    def addProperties(self, protoclaims, hitItem, ref):
        """
        add each property (if new) and source it

        param protoclaims: a dict of claims with a
            key: Prop number
            val: Statement|list of Statments
        param hititem: the target entity
        param ref: Reference
        """
        for pcprop, pcvalue in protoclaims.iteritems():
            if pcvalue:
                if isinstance(pcvalue, list):
                    pcvalue = set(pcvalue)  # eliminate potential duplicates
                    for val in pcvalue:
                        # check if None or a Statement(None)
                        if (val is not None) and (not val.isNone()):
                            self.wd.addNewClaim(pcprop, val, hitItem, ref)
                            # reload item so that next call is aware of changes
                            hitItem = pywikibot.ItemPage(self.repo,
                                                         hitItem.title())
                            hitItem.exists()
                elif not pcvalue.isNone():
                    self.wd.addNewClaim(pcprop, pcvalue, hitItem, ref)

    # KulturNav specific functions
    def dbpedia2Wikidata(self, item):
        """
        Converts a dbpedia reference to the equivalent Wikidata item,
        if present
        param item: dict with @language, @value keys
        return pywikibot.ItemPage|None
        """
        if KulturnavBot.foobar(item):
            return
        if not all(x in item.keys() for x in (u'@value', u'@language')):
            pywikibot.output(u'invalid dbpedia entry: %s' % item)
            exit(1)

        # any site will work, this is just an example
        site = pywikibot.Site(item[u'@language'], 'wikipedia')
        page = pywikibot.Page(site, item[u'@value'])
        if u'wikibase_item' in page.properties() and \
                page.properties()[u'wikibase_item']:
            qNo = page.properties()[u'wikibase_item']
            return pywikibot.ItemPage(self.repo, qNo)

    def dbDate(self, item):
        """
        Deprecated in favour of helpers.ISO_to_WbTime
        """
        print 'call to deprecated KulturnavBot.dbDate()'
        return helpers.ISO_to_WbTime(item)

    def dbGender(self, item):
        """
        Simply matches gender values to Q items
        Note that this returns a Statment unlike most other functions
        param item: string
        return WD.Statement|None
        """
        known = {u'male': u'Q6581097',
                 u'female': u'Q6581072',
                 u'unknown': u'somevalue'}  # a special case
        if item not in known.keys():
            pywikibot.output(u'invalid gender entry: %s' % item)
            return

        if known[item] in (u'somevalue', u'novalue'):
            return WD.Statement(
                known[item],
                special=True)
        else:
            return WD.Statement(
                pywikibot.ItemPage(
                    self.repo,
                    known[item]))

    def dbName(self, nameObj, typ, limit=75):
        """
        A wrapper for helpers.match_name() to send it the relevant part of a
        nameObj

        param nameObj = {'@language': 'xx', '@value': 'xxx'}
        param typ string: lastName/firstName
        param limit int: number of hits before skipping (if not on labs)
        return pywikibot.ItemPage|None
        """
        return helpers.match_name(nameObj['@value'], typ, self.wd, limit=limit)

    def location2Wikidata(self, uuid):
        """
        Given a kulturNav uuid or url this checks if that contains a
        GeoNames url and, if so, connects that to a Wikidata object
        using the GEONAMES_ID_P property (if any).

        NOTE that the WDQ results may be outdated
        return pywikibot.ItemPage|None
        """
        # Check if uuid
        if not self.isUuid(uuid):
            return None
        # Convert url to uuid
        if uuid.startswith(u'http://kulturnav.org'):
            uuid = uuid.split('/')[-1]
        # Check if already stored
        if uuid in self.locations.keys():
            if self.locations[uuid] is None:
                return None
            else:
                qNo = u'Q%d' % self.locations[uuid]
                return pywikibot.ItemPage(self.repo, qNo)

        # retrieve various sources
        geoSources = self.getGeoSources(uuid)
        kulturarvsdata = self.extractKulturarvsdataLocation(geoSources)
        if kulturarvsdata:
            self.locations[uuid] = kulturarvsdata
            qNo = u'Q%d' % self.locations[uuid]
            return pywikibot.ItemPage(self.repo, qNo)

        # retrieve hit through geonames-lookup
        geonames = self.extractGeonames(geoSources)
        if geonames:
            # store as a resolved hit, in case wdq yields nothing
            self.locations[uuid] = None
            wdqQuery = u'STRING[%s:"%s"]' % (self.GEONAMES_ID_P, geonames)
            wdqResult = self.wd.wdqLookup(wdqQuery)
            if wdqResult and len(wdqResult) == 1:
                self.locations[uuid] = wdqResult[0]
                qNo = u'Q%d' % self.locations[uuid]
                return pywikibot.ItemPage(self.repo, qNo)
            # else:
            # go to geonames and find wikidata from there
            # add to self.locations[uuid]
            # add GEONAMES_ID_P to the identified wikidata

        # no (clean) hits
        return None

    def getGeoSources(self, uuid):
        """
        Given a kulturNav uuid return the corresponding properties of
        that target which are likely to contain geosources.

        return list
        """
        # debugging
        if not self.isUuid(uuid):
            return []

        queryurl = 'http://kulturnav.org/api/%s'
        jsonData = json.load(urllib2.urlopen(queryurl % uuid))
        sources = []
        if jsonData.get(u'properties'):
            sameAs = jsonData.get('properties').get('entity.sameAs')
            if sameAs:
                sources += sameAs
            sourceUri = jsonData.get('properties') \
                                .get('superconcept.sourceUri')
            if sourceUri:
                sources += sourceUri
        return sources

    def extractGeonames(self, sources):
        """
        Given a list of extractGeoSources() return any geonames ID.

        return string|None
        """
        needle = 'http://sws.geonames.org/'
        for s in sources:
            if s.get('value') and s.get('value').startswith(needle):
                return s.get('value').split('/')[-1]
        return None

    def extractKulturarvsdataLocation(self, sources):
        """
        Given a list of extractGeoSources() return any kulturarvsdata
        geo authorities.

        return string|None
        """
        needle = u'http://kulturarvsdata.se/resurser/aukt/geo/'
        for s in sources:
            if s.get('value') and s.get('value').startswith(needle):
                s = s.get('value').split('/')[-1]
                if s.startswith('municipality#'):
                    code = s.split('#')[-1]
                    wdqQuery = u'STRING[%s:"%s"]' % (self.SWE_KOMMUNKOD_P,
                                                     code)
                    wdqResult = self.wd.wdqLookup(wdqQuery)
                    if wdqResult and len(wdqResult) == 1:
                        self.ADMIN_UNITS.append(wdqResult[0])
                        return wdqResult[0]
                elif s.startswith('county#'):
                    code = s.split('#')[-1]
                    wdqQuery = u'STRING[%s:"%s"]' % (self.SWE_COUNTYKOD_P,
                                                     code)
                    wdqResult = self.wd.wdqLookup(wdqQuery)
                    if wdqResult and len(wdqResult) == 1:
                        self.ADMIN_UNITS.append(wdqResult[0])
                        return wdqResult[0]
                elif s.startswith('country#'):
                    pass  # handle via geonames instead
                elif s.startswith('parish#'):
                    pass  # no id's in wikidata
                else:
                    pywikibot.output(u'Unhandled KulturarvsdataLocation '
                                     u'prefix: %s' % s)
                    exit(1)
        return None

    def getLocationProperty(self, item, strict=True):
        """
        Given an ItemPage this returns the suitable property which
        should be used to indicate its location.
        P17  - land
        P131 - within administrative unit
        P276 - place

        param item: pywikibot.ItemPage|None
        param strict: bool whether place should be returned if no land
                      or admin_unit hit
        return string|None
        """
        if item is not None:
            q = int(item.title()[1:])
            if q in self.COUNTRIES:
                return u'P17'
            elif q in self.ADMIN_UNITS:
                return u'P131'
            elif not strict:
                return u'P%s' % self.PLACE_P
            elif self.verbose:
                item.exists()
                pywikibot.output(u'Could not set location property for: '
                                 u'%s (%s)' % (item.title(),
                                               item.labels.get('sv')))
        return None

    def kulturnav2Wikidata(self, uuid):
        """
        Given a kulturNav uuid or url this returns the Wikidata entity
        connected to this uuid through the KULTURNAV_ID_P property
        (if any).

        NOTE that the WDQ results may be outdated
        return pywikibot.ItemPage|None
        """
        # debugging
        if not self.isUuid(uuid):
            return None

        # Convert url to uuid
        if uuid.startswith(u'http://kulturnav.org'):
            uuid = uuid.split('/')[-1]

        if uuid in self.itemIds.keys():
            qNo = u'Q%d' % self.itemIds[uuid]
            return pywikibot.ItemPage(self.repo, qNo)
        else:
            return None

    def isUuid(self, uuid):
        """
        tests if a string really is a uuid
        """
        if not isinstance(uuid, (str, unicode)):
            print u'Not an uuid in %s: %s' % (self.current_uuid, uuid)
            return False
        uuid = uuid.split('/')[-1]  # in case of url
        pattern = r'[0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12}'
        m = re.search(pattern, uuid)
        if not m or m.group(0) != uuid:
            print u'Not an uuid in %s: %s' % (self.current_uuid, uuid)
            return False
        return True

    @staticmethod
    def is_int(s):
        """
        Deprecated in favour of helpers.listify
        """
        print 'call to deprecated KulturnavBot.is_int()'
        return helpers.is_int(s)

    @staticmethod
    def listify(value):
        """
        Deprecated in favour of helpers.listify
        """
        print 'call to deprecated KulturnavBot.listify()'
        return helpers.listify(value)

    @staticmethod
    def bundleValues(values):
        """
        Given a list of values (which might or might not be lists)
        merge all into one list
        param values list
        return list|None
        """
        bundle = []
        for v in values:
            if v is not None:
                v = helpers.listify(v)
                bundle += v
        if len(bundle) == 0:
            return None
        else:
            return bundle

    @staticmethod
    def shuffleNames(nameObj):
        """
        A wrapper for helpers.reorder_names() to send it the relevant part of a
        nameObj

        param nameObj = {'@language': 'xx', '@value': 'xxx'}
        return nameObj|None
        """
        name = helpers.reorder_names(nameObj['@value'])
        if name is None:
            return None
        nameObj = nameObj.copy()
        nameObj['@value'] = name
        return nameObj

    def makeRef(self, date):
        """
        Make a correctly formatted ref object for claims
        """
        ref = WD.Reference(
            source_P=self.STATED_IN_P,
            source=pywikibot.ItemPage(self.repo,
                                      u'Q%s' % self.DATASET_Q),
            time_P=self.PUBLICATION_P,
            time=date)
        return ref

    def addLabelOrAlias(self, nameObj, item, caseSensitive=False):
        """
        Adds a name as either a label (if none) or an alias.
        Essentially a filter for the more generic method in WikidatStuff

        param nameObj = {'@language': 'xx', '@value': 'xxx'}
                        or a list of such
        """
        # for a list of entries
        if isinstance(nameObj, list):
            for n in nameObj:
                self.addLabelOrAlias(n, item)
                # reload item so that next call is aware of any changes
                item = pywikibot.ItemPage(self.repo, item.title())
                item.exists()
            return

        # for a single entry
        self.wd.addLabelOrAlias(nameObj['@language'], nameObj['@value'],
                                item, prefix=self.EDIT_SUMMARY,
                                caseSensitive=caseSensitive)

    @classmethod
    def getKulturnavGenerator(cls, maxHits=250, delay=0):
        """
        Generator of the entries at KulturNav based on a search for all items
        of given type in the given dataset which contains Wikidata as a
        given value.
        param maxHits: max hits to request per search
        param delay: delay in seconds between each kulturnav request
        """
        patterns = (u'http://www.wikidata.org/entity/',
                    u'https://www.wikidata.org/entity/')
        q = '*%2F%2Fwww.wikidata.org%2Fentity%2FQ*'
        searchurl = 'http://kulturnav.org/api/search/' + \
                    'entityType:' + cls.ENTITY_TYPE + ',' + \
                    'entity.dataset_r:' + cls.DATASET_ID + ',' + \
                    cls.MAP_TAG + ':%s/%d/%d'
        queryurl = 'http://kulturnav.org/%s?format=application/ld%%2Bjson'

        # get all id's in KulturNav which link to Wikidata
        wdDict = {}

        offset = 0
        # overviewPage = json.load(urllib2.urlopen(searchurl % (q, offset, maxHits)))
        searchPage = urllib2.urlopen(searchurl % (q, offset, maxHits))
        searchData = searchPage.read()
        overviewPage = json.loads(searchData)

        while len(overviewPage) > 0:
            for o in overviewPage:
                sameAs = o[u'properties'][cls.MAP_TAG[:cls.MAP_TAG.rfind('_')]]
                for s in sameAs:
                    if s[u'value'].startswith(patterns):
                        wdDict[o[u'uuid']] = s[u'value'].split('/')[-1]
                        break
            # continue
            offset += maxHits
            searchPage = urllib2.urlopen(searchurl % (q, offset, maxHits))
            searchData = searchPage.read()
            overviewPage = json.loads(searchData)

        # some feedback
        pywikibot.output(u'Found %d matching entries in Kulturnav'
                         % len(wdDict))

        # get the record for each of these entries
        for kulturnavId, wikidataId in wdDict.iteritems():
            # jsonData = json.load(urllib2.urlopen(queryurl % kulturnavId))
            time.sleep(delay)
            recordPage = urllib2.urlopen(queryurl % kulturnavId)
            recordData = recordPage.read()
            jsonData = json.loads(recordData)
            if jsonData.get(u'@graph'):
                yield jsonData
            else:
                print jsonData

    @classmethod
    def main(cls, *args):
        # handle arguments
        cutoff = None
        maxHits = 250
        delay = 0

        def if_arg_value(arg, name):
            if arg.startswith(name):
                yield arg[len(name) + 1:]

        for arg in pywikibot.handle_args(args):
            for v in if_arg_value(arg, '-cutoff'):
                cutoff = int(v)
            for v in if_arg_value(arg, '-maxHits'):
                maxHits = int(v)
            for v in if_arg_value(arg, '-delay'):
                delay = int(v)

        kulturnavGenerator = cls.getKulturnavGenerator(maxHits=maxHits,
                                                       delay=delay)

        kulturnavBot = cls(kulturnavGenerator)
        kulturnavBot.cutoff = cutoff
        kulturnavBot.run()

    @staticmethod
    def foobar(item):
        if isinstance(item, list):
            pywikibot.output(FOO_BAR)
            return True
        return False

if __name__ == "__main__":
    KulturnavBot.main()
