#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and sourced statements about entities also present in
KulturNav (https://www.wikidata.org/wiki/Q16323066).

Author: Lokal_Profil
License: MIT

See https://github.com/lokal-profil/wikidata-stuff/issues for TODOs

usage:
    python kulturnavBot.py [OPTIONS]

&params;
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

parameter_help = u"""\
Basic KulturNavBot options (may be omitted):
-cutoff:INT        number of entries to process before terminating
-max_hits:INT      number of items to request at a time from Kulturnav
                    (default 250)
-delay:INT         seconds to delay between each kulturnav request
                    (default 0)
-any_item          if present it does not filter kulturnav results on wikidata
-wdq_cache:INT     set the cache age (in seconds) for wdq queries
                    (default 0)

Can also handle any pywikibot options. Most importantly:
-simulate          don't write to database
-help              output all available options
"""
docuReplacements = {'&params;': parameter_help}


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

    def __init__(self, dictGenerator, cache_max_age, verbose=False):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.
        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()
        self.cutoff = None
        self.verbose = verbose
        self.require_wikidata = True

        # trigger wdq query
        self.itemIds = helpers.fill_cache(self.KULTURNAV_ID_P,
                                          cache_max_age=cache_max_age)

        # set up WikidataStuff instance
        self.wd = WD(self.repo)

        # load lists
        self.COUNTRIES = self.wd.wdqLookup(u'TREE[6256][][31]',
                                           cache_max_age)
        self.ADMIN_UNITS = self.wd.wdqLookup(u'TREE[15284][][31]',
                                             cache_max_age)

    @classmethod
    def set_variables(cls, dataset_q=None, dataset_id=None, entity_type=None,
                      map_tag=None, edit_summary=None):
        """Override any class variables.

        Used when command line arguments affect which type of run to do.

        @param dataset_q: the Q-id of the dataset
        @type dataset_q: str
        @param dataset_id: the uuid of the dataset
        @type dataset_id: str
        @param entity_type: the entity type to provide for the search API
        @type entity_type: str
        @param map_tag: the map_tag to use in the search API to find wikidata
            matches
        @type map_tag: str
        @param edit_summary: the edit_summary to use
        @type edit_summary: str
        """
        cls.DATASET_Q = dataset_q or cls.DATASET_Q
        cls.DATASET_ID = dataset_id or cls.DATASET_ID
        cls.ENTITY_TYPE = entity_type or cls.ENTITY_TYPE
        cls.MAP_TAG = map_tag or cls.MAP_TAG
        cls.EDIT_SUMMARY = edit_summary or cls.EDIT_SUMMARY

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
                u'getty_aat': None,
                u'ulan': None
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
                        itis=self.wd.QtoItemPage(self.DATASET_Q)),
                    force=True)

            # authority control protoclaims
            if values[u'libris-id']:
                protoclaims[u'P906'] = WD.Statement(values[u'libris-id'])
            if values[u'viaf-id']:
                protoclaims[u'P214'] = WD.Statement(values[u'viaf-id'])
            if values[u'getty_aat']:
                protoclaims[u'P1014'] = WD.Statement(values[u'getty_aat'])
            if values[u'ulan']:
                protoclaims[u'P245'] = WD.Statement(values[u'ulan'])

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
                date = helpers.iso_to_WbTime(values[u'modified'])
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
            elif u'getty_aat' in values.keys() and \
                    u'vocab.getty.edu/aat/' in sa:
                values[u'getty_aat'] = sa.split('/')[-1]
            elif u'ulan' in values.keys() and \
                    u'vocab.getty.edu/ulan/' in sa:
                values[u'ulan'] = sa.split('/')[-1]

        # only look at seeAlso if we found no Wikidata link and require one
        if self.require_wikidata and \
                (not values[u'wikidata'] and values[u'seeAlso']):
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
        testItem = self.wd.QtoItemPage(Q)
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
            testItems.append(self.wd.QtoItemPage(q))
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
                self.itemIds.get(values[u'identifier'])

            if not values[u'wikidata'] and not self.require_wikidata:
                # i.e. uuid has been supplied manually and exists on wikidata
                pass
            elif values[u'wikidata'] != hitItemTitle:
                # this may be caused by either being a redirect
                wd = self.wd.QtoItemPage(values[u'wikidata'])
                wi = self.wd.QtoItemPage(hitItemTitle)
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
            self.wd.QtoItemPage(hitItemTitle))
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
                if namelist:
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
        param ref: WD.Reference
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
                            hitItem = self.wd.QtoItemPage(hitItem.title())
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
            return self.wd.QtoItemPage(qNo)

    def dbDate(self, item):
        """
        Deprecated in favour of helpers.iso_to_WbTime
        """
        print 'call to deprecated KulturnavBot.dbDate()'
        return helpers.iso_to_WbTime(item)

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
                self.wd.QtoItemPage(known[item]))

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
                return self.wd.QtoItemPage(qNo)

        # retrieve various sources
        geoSources = self.getGeoSources(uuid)
        kulturarvsdata = self.extractKulturarvsdataLocation(geoSources)
        if kulturarvsdata:
            self.locations[uuid] = kulturarvsdata
            qNo = u'Q%d' % self.locations[uuid]
            return self.wd.QtoItemPage(qNo)

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
                return self.wd.QtoItemPage(qNo)
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
            return self.wd.QtoItemPage(qNo)
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
        Deprecated in favour of helpers.bundle_values
        """
        print 'call to deprecated KulturnavBot.bundleValues()'
        return helpers.bundle_values(values)

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
            source_test=self.wd.make_simple_claim(
                self.STATED_IN_P,
                self.wd.QtoItemPage(self.DATASET_Q)),
            source_notest=self.wd.make_simple_claim(
                self.PUBLICATION_P,
                date))
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
                item = self.wd.QtoItemPage(item.title())
                item.exists()
            return

        # for a single entry
        self.wd.addLabelOrAlias(nameObj['@language'], nameObj['@value'],
                                item, prefix=self.EDIT_SUMMARY,
                                caseSensitive=caseSensitive)

    @staticmethod
    def get_kulturnav_generator(uuids, delay=0):
        """Generate KulturNav items from a list of uuids.

        @param uuids: uuids to request items for
        @type uuids: list of str
        @param delay: delay in seconds between each kulturnav request
        @type delay: int
        @yield: dict
        """
        for uuid in uuids:
            time.sleep(delay)
            try:
                json_data = KulturnavBot.get_single_entry(uuid)
            except pywikibot.Error, e:
                pywikibot.output(e)
            else:
                yield json_data

    @classmethod
    def get_search_results(cls, max_hits=250, require_wikidata=True):
        """Make a KulturNav search for all items of a given type in a dataset.

        @param max_hits: the maximum number of results to request at once
        @type max_hits: int
        @param require_wikidata: whether to filter results on having a wikidata
            url in sameAs
        @type require_wikidata: bool
        @return: the resulting uuids
        @rtype: list of str
        """
        search_url = 'http://kulturnav.org/api/search/' + \
                     'entityType:' + cls.ENTITY_TYPE + ',' + \
                     'entity.dataset_r:' + cls.DATASET_ID
        q = None  # the map_tag query

        # only filter on MAP_TAG if filtering on wikidata
        if require_wikidata:
            search_url += ',' + cls.MAP_TAG + ':%s/%d/%d'
            q = '*%2F%2Fwww.wikidata.org%2Fentity%2FQ*'
        else:
            search_url += '/%d/%d'

        # start search
        results = []
        offset = 0
        overview_page = KulturnavBot.get_single_search_results(
            search_url, q, offset, max_hits)
        while overview_page:
            for item in overview_page:
                uuid = item[u'uuid']
                if not require_wikidata or \
                        KulturnavBot.has_wikidata_in_sameas(item, cls.MAP_TAG):
                    results.append(uuid)

            # continue
            offset += max_hits
            overview_page = KulturnavBot.get_single_search_results(
                search_url, q, offset, max_hits)

        # some feedback
        pywikibot.output(u'Found %d matching entries in Kulturnav'
                         % len(results))
        return results

    @staticmethod
    def has_wikidata_in_sameas(item, map_tag):
        """Check if a wikidata url is present in the sameAs property.

        @param item: the search item to check
        @type item: dict
        @param map_tag: the tag to use (concepts don't use sameAs)
        @type map_tag: str
        @rtype: bool
        """
        # The patterns used if we filter on wikidata
        patterns = (u'http://www.wikidata.org/entity/',
                    u'https://www.wikidata.org/entity/')

        same_as = item[u'properties'][map_tag[:map_tag.rfind('_')]]
        for s in same_as:
            if s[u'value'].startswith(patterns):
                return True
        return False

    @staticmethod
    def get_single_search_results(search_url, q, offset, max_hits):
        """Retrieve the results from a single API search.

        @param search_url: basic url from whih to build search
        @type search_url: str
        @param q: the map_tag query, if any
        @type q: str or None
        @param offset: the offset in search results
        @type offset: int
        @param max_hits: the maximum number of results to request at once
        @type max_hits: int
        @return: the search result object
        @rtype: dict
        """
        actual_url = ''
        if q is None:
            actual_url = search_url % (offset, max_hits)
        else:
            actual_url = search_url % (q, offset, max_hits)

        search_page = urllib2.urlopen(actual_url)
        return json.loads(search_page.read())

    @staticmethod
    def get_single_entry(uuid):
        """Retrieve the data on a single kulturnav entry.

        Raises an pywikibot.Error if:
        * @graph is not a key in the json response
        * a non-json response is received

        @param uuid: the uuid for the target item
        @type uuid: str
        @return: the entry object
        @rtype: dict
        @raise: pywikibot.Error
        """
        query_url = 'http://kulturnav.org/%s?format=application/ld%%2Bjson'
        item_url = query_url % uuid
        try:
            record_page = urllib2.urlopen(item_url)
            json_data = json.loads(record_page.read())
        except ValueError, e:
            raise pywikibot.Error('Error loading KulturNav item at '
                                  '%s with error %s' % (item_url, e))
        if json_data.get(u'@graph'):
            return json_data
        else:
            raise pywikibot.Error('No @graph in KulturNav reply at '
                                  '%s\n data: %s' % (item_url, json_data))

    @classmethod
    def main(cls, *args):
        """Start the bot from the command line."""
        options = cls.handle_args(args)

        search_results = cls.get_search_results(
            max_hits=options['max_hits'],
            require_wikidata=options['require_wikidata'])
        kulturnav_generator = cls.get_kulturnav_generator(
            search_results, delay=options['delay'])

        kulturnav_bot = cls(kulturnav_generator, options['cache_max_age'])
        kulturnav_bot.cutoff = options['cutoff']
        kulturnav_bot.require_wikidata = options['require_wikidata']
        kulturnav_bot.run()

    @classmethod
    def run_from_list(cls, uuids, *args):
        """Start the bot with a list of uuids."""
        options = cls.handle_args(args)

        kulturnav_generator = cls.get_kulturnav_generator(
            uuids, delay=options['delay'])
        kulturnav_bot = cls(kulturnav_generator, options['cache_max_age'])
        kulturnav_bot.cutoff = options['cutoff']
        kulturnav_bot.require_wikidata = False
        kulturnav_bot.run()

    @staticmethod
    def handle_args(args):
        """Parse and load all of the basic arguments.

        Also passes any needed arguments on to pywikibot and sets any defaults.

        @param args: arguments to be handled
        @type args: list of strings
        @return: list of options
        @rtype: dict
        """
        options = {
            'cutoff': None,
            'max_hits': 250,
            'delay': 0,
            'require_wikidata': True,
            'cache_max_age': 0,
            }

        for arg in pywikibot.handle_args(args):
            option, sep, value = arg.partition(':')
            if option == '-cutoff':
                options['cutoff'] = int(value)
            elif option == '-max_hits':
                options['max_hits'] = int(value)
            elif option == '-delay':
                options['delay'] = int(value)
            elif option == '-any_item':
                options['require_wikidata'] = False
            elif option == '-wdq_cache':
                options['cache_max_age'] = int(value)

        return options

    @staticmethod
    def foobar(item):
        if isinstance(item, list):
            pywikibot.output(FOO_BAR)
            return True
        return False

if __name__ == "__main__":
    KulturnavBot.main()
