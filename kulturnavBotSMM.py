#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about Maritime objects in KulturNav.

usage:
    python kulturnavSMM.py [OPTIONS]

Author: Lokal_Profil
License: MIT

Options (required):
  -dataset:STR      the dataset to work on
Options (may be omitted):
  -cutoff:INT       number of entries to process before terminating
  -maxHits:INT      number of items to request at a time from Kulturnav
                    (default 250)
"""
import pywikibot
from kulturnavBot import KulturnavBot

# KulturNav based
EDIT_SUMMARY = 'KulturnavBot(SMM)'
DATASETS = {
    u'Fartyg': {
        'id': 0,
        'fullName': u'Fartyg',
        'DATASET_ID': '9a816089-2156-42ce-a63a-e2c835b20688',
        'ENTITY_TYPE': 'NavalVessel',
        'DATASET_Q': None},
    u'Fartygstyper': {
        'id': 1,
        'fullName': u'Fartygstyper',
        'DATASET_ID': 'c43d8eba-030b-4542-b1ac-6a31a0ba6d00',
        'ENTITY_TYPE': 'Concept',
        'MAP_TAG': 'concept.exactMatch',
        'DATASET_Q': '20103697'},
    u'Namngivna': {
        'id': 2,
        'fullName': u'Namngivna fartygstyper',
        'DATASET_ID': '51f2bd1f-7720-4f03-8d95-c22a85d26bbb',
        'ENTITY_TYPE': 'NavalVessel',
        'DATASET_Q': None},
    u'Personer': {
        'id': 3,
        'fullName': u'Personer verksamma inom fartygs- och båtbyggeri',
        'DATASET_ID': 'c6a7e732-650f-4fdb-a34c-366088f1ff0e',
        'ENTITY_TYPE': 'Person',
        'DATASET_Q': None},
    u'Serietillverkade': {
        'id': 4,
        'fullName': u'Serietillverkade fartyg',
        'DATASET_ID': '6a98b348-8c90-4ccc-9da7-42351bd4feb7',
        'ENTITY_TYPE': 'NavalVessel',
        'DATASET_Q': None},
    u'Klasser': {
        'id': 5,
        'fullName': u'Svenska marinens klasser för örlogsfartyg',
        'DATASET_ID': 'fb4faa4b-984a-404b-bdf7-9c24a298591e',
        'ENTITY_TYPE': 'NavalVessel',
        'DATASET_Q': None},
    u'Varv': {
        'id': 6,
        'fullName': u'Varv',
        'DATASET_ID': 'b0fc1427-a9ab-4239-910a-cd02c02c4a76',
        'ENTITY_TYPE': 'Organization',
        'DATASET_Q': None}
}
MAP_TAG = 'entity.sameAs_s'


class KulturnavBotSMM(KulturnavBot):
    """
    A bot to enrich and create information on Wikidata based on KulturNav info
    """
    DATASET = None  # set by setDataset()
    GROUP_OF_PEOPLE_Q = '16334295'
    HUMAN_Q = '5'
    cutoff = None

    def run(self, cutoff=None):
        """
        Starts the robot
        param cutoff: if present limits the number of records added in one go
        """
        self.cutoff = cutoff
        # switch run method based on DATASET
        if self.DATASET == 'Personer':
            self.runPerson()
        else:
            raise NotImplementedError("Please implement this dataset: %s"
                                      % self.DATASET)

    def runPerson(self):
        personValues = {
            # u'deathPlace': None,
            u'deathDate': None,
            # u'birthPlace': None,
            u'birthDate': None,
            u'firstName': None,
            u'gender': None,
            u'lastName': None,
            u'name': None
            # u'person.nationality': None
        }

        def personClaims(self, values):
            protoclaims = {
                u'P31': pywikibot.ItemPage(  # instance of
                    self.repo,
                    u'Q%s' % self.HUMAN_Q)
                }
            # P106 occupation
            # P27 nationality

            # if values[u'deathPlace']:
            #    protoclaims[u'P20'] = self.dbpedia2Wikidata(values[u'deathPlace'])
            if values[u'deathDate']:
                protoclaims[u'P570'] = self.dbDate(values[u'deathDate'])
            # if values[u'birthPlace']:
            #    protoclaims[u'P19'] = self.dbpedia2Wikidata(values[u'birthPlace'])
            if values[u'birthDate']:
                protoclaims[u'P569'] = self.dbDate(values[u'birthDate'])
            if values[u'gender']:
                protoclaims[u'P21'] = self.dbGender(values[u'gender'])
            if values[u'firstName']:
                protoclaims[u'P735'] = self.dbName(values[u'firstName'],
                                                   u'firstName')
            if values[u'lastName']:
                protoclaims[u'P734'] = self.dbName(values[u'lastName'],
                                                   u'lastName')
            return protoclaims

        def personTest(self, hitItem):
            group_item = pywikibot.ItemPage(
                self.repo,
                u'Q%s' % self.GROUP_OF_PEOPLE_Q)
            if self.hasClaim('P%s' % self.IS_A_P, group_item, hitItem):
                    pywikibot.output(u'%s is matched to a group of people, '
                                     u'FIXIT' % hitItem.title())
                    return False
            else:
                    return True

        # pass settingson to runLayout()
        self.runLayout(datasetValues=personValues,
                       datasetProtoclaims=personClaims,
                       datasetSanityTest=personTest,
                       shuffle=True)

    def runLayout(self, datasetValues, datasetProtoclaims,
                  datasetSanityTest, shuffle):
        """
        The basic layout of a run. It should be called for a dataset
        specific run which sets the parameters.

        param datasetValues: a dict of additional values to look for
        param datasetProtoclaims: a function for populating protoclaims
        param datasetSanityTest: a function which must return true for
                                 results to be written to Wikidata
        param shuffle: whether name/title/alias is shuffled or not
                       i.e. if name = last, first
        """
        count = 0
        for hit in self.generator:
            # print count, cutoff
            if self.cutoff and count >= self.cutoff:
                break
            # Required values to searching for
            values = {u'identifier': None,
                      u'modified': None,
                      u'seeAlso': None,
                      u'sameAs': None,
                      # not expected
                      u'wikidata': None,
                      u'libris-id': None,
                      u'viaf-id': None}
            values.update(datasetValues)

            # populate values
            if not self.populateValues(values, hit):
                # continue with next hit if problem was encounterd
                continue

            # find the matching wikidata item
            hitItem = self.wikidataMatch(values)

            # convert values to potential claims
            protoclaims = datasetProtoclaims(self, values)

            protoclaims[u'P%s' % self.KULTURNAV_ID_P] = values[u'identifier']
            if values[u'libris-id']:
                protoclaims[u'P906'] = values[u'libris-id']
            if values[u'viaf-id']:
                protoclaims[u'P214'] = values[u'viaf-id']

            # Add information if a match was found
            if hitItem and hitItem.exists():

                # make sure it passes the sanityTest
                if not datasetSanityTest(self, hitItem):
                    continue

                # add name as label/alias
                self.addNames(values[u'name'], hitItem, shuffle=shuffle)

                # get the "last modified" timestamp
                date = self.dbDate(values[u'modified'])

                # add each property (if new) and source it
                self.addProperties(protoclaims, hitItem, date)

            # allow for limited runs
            count += 1

        # done
        pywikibot.output(u'Went over %d entries' % count)

    def populateValues(self, values, hit):
        """
        given a list of values and a kulturnav hit, populate the values
        and check if result is problem free

        return bool problemFree
        """
        problemFree = True
        for entries in hit[u'@graph']:
            for k, v in entries.iteritems():
                if k in values.keys():
                    if values[k] is None:
                        values[k] = v
                    else:
                        pywikibot.output(u'duplicate entries for %s' % k)
                        problemFree = False

        # the minimum which must have been identified
        if values[u'identifier'] is None:
            pywikibot.output(u'Could not isolate the identifier from the '
                             u'KulturNav object! JSON layout must have '
                             u'changed. Crashing!')
            exit(1)

        # dig into sameAs and seeAlso
        # each can be either a list or a str/unicode
        if isinstance(values[u'sameAs'], (str, unicode)):
            values[u'sameAs'] = [values[u'sameAs'], ]
        if values[u'sameAs'] is not None:
            for sa in values[u'sameAs']:
                if u'wikidata' in sa:
                    values[u'wikidata'] = sa.split('/')[-1]
                elif u'libris-id' in values.keys() and \
                        u'libris.kb.se/auth/' in sa:
                    values[u'libris-id'] = sa.split('/')[-1]
                elif u'viaf-id' in values.keys() and \
                        u'viaf.org/viaf/' in sa:
                    values[u'viaf-id'] = sa.split('/')[-1]
        # we only care about seeAlso if we didn't find a Wikidata link
        if values[u'wikidata'] is None:
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
        hitItem = self.bypassRedirect(
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

        param: shuffle bool if name order is last, first then this
               creates a local rearranged copy
        """
        if names:
            if shuffle:
                namelist = []
                if isinstance(names, dict):
                    s = KulturnavBotSMM.shuffleNames(names)
                    if s is not None:
                        namelist.append(s)
                elif isinstance(names, list):
                    for n in names:
                        s = KulturnavBotSMM.shuffleNames(n)
                        if s is not None:
                            namelist.append(s)
                else:
                    pywikibot.output(u'unexpectedly formatted name'
                                     u'object: %s' % names)
                if len(namelist) > 0:
                    self.addLabelOrAlias(namelist, hitItem)
            else:
                self.addLabelOrAlias(names, hitItem)

    def addProperties(self, protoclaims, hitItem, date):
        """
        add each property (if new) and source it
        """
        for pcprop, pcvalue in protoclaims.iteritems():
            if pcvalue:
                if isinstance(pcvalue, unicode) and \
                        pcvalue in (u'somevalue', u'novalue'):
                    # special cases
                    self.addNewSpecialClaim(pcprop, pcvalue,
                                            hitItem, date)
                elif pcprop == u'P%s' % self.KULTURNAV_ID_P:
                    qual = {
                        u'prop': u'P%s' % self.CATALOG_P,
                        u'itis': pywikibot.ItemPage(
                            self.repo,
                            u'Q%s' % self.DATASET_Q),
                        u'force': True}
                    self.addNewClaim(pcprop, pcvalue, hitItem,
                                     date, qual=qual)
                else:
                    self.addNewClaim(pcprop, pcvalue,
                                     hitItem, date)

    @classmethod
    def setDataset(cls, *args):
        """
        Allows other args to be handled by a subclass by overloading this
        function.

        TODO: Ideally this would be handled differently e.g. by unhandled
        args in kulturnavBot.main being sent to an overloaded method. This
        would however require setVariables to be handled differently as well.
        """
        if not args:
            args = pywikibot.argvu[1:]
        name = '-dataset'

        # allow dataset to be specified through id
        numPairs = {}
        for k, v in DATASETS.iteritems():
            numPairs[str(v['id'])] = k

        for arg in args:
            if arg.startswith(name):
                dataset = arg[len(name) + 1:]
                if dataset in DATASETS.keys():
                    cls.DATASET = dataset
                    return
                elif dataset in numPairs.keys():
                    cls.DATASET = numPairs[dataset]
                    return

        # if nothing found
        txt = u''
        for k, v in numPairs.iteritems():
            txt += u'\n%s %s' % (k, v)
        pywikibot.output(u'No valid -dataset argument was found. This '
                         u'must be given by either number or name.\n'
                         'Available datasets are: %s' % txt)
        exit(1)

    @classmethod
    def main(cls, *args):
        # pick one dataset from DATASETS
        cls.setDataset(*args)
        map_tag = MAP_TAG
        if 'MAP_TAG' in DATASETS[cls.DATASET].keys():
            map_tag = DATASETS[cls.DATASET]['MAP_TAG']

        # set variables and start bot
        cls.setVariables(
            dataset_q=DATASETS[cls.DATASET]['DATASET_Q'],
            dataset_id=DATASETS[cls.DATASET]['DATASET_ID'],
            entity_type=DATASETS[cls.DATASET]['ENTITY_TYPE'],
            map_tag=map_tag,
            edit_summary=EDIT_SUMMARY
        )
        super(KulturnavBotSMM, cls).main(*args)


if __name__ == "__main__":
    KulturnavBotSMM.main()
