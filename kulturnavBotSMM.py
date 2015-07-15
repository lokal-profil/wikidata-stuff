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
from kulturnavBot import Rule

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
    SHIPYARD_Q = '190928'

    def run(self):
        """
        Starts the robot
        """
        # switch run method based on DATASET
        if self.DATASET == 'Personer':
            self.runPerson()
        else:
            raise NotImplementedError("Please implement this dataset: %s"
                                      % self.DATASET)

    def runPerson(self):
        personRules = {
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
            if self.wd.hasClaim('P%s' % self.IS_A_P, group_item, hitItem):
                    pywikibot.output(u'%s is matched to a group of people, '
                                     u'FIXIT' % hitItem.title())
                    return False
            else:
                    return True

        # pass settingson to runLayout()
        self.runLayout(datasetRules=personRules,
                       datasetProtoclaims=personClaims,
                       datasetSanityTest=personTest,
                       label=u'name',
                       shuffle=True)

    def runVarv(self):
        """
        TODO:
            Is varv a place or an organisation?
            finish values
                build mechanism for handling subnodes?
            finish claims
                identify VARV_Q
            finish test
        """
        varvRules = {
            u'name': None,
            u'agent.ownedBy': None,
            u'establishment.date': Rule(
                keys=['association.establishment.association', ],
                values={'@type': 'dbpedia-owl:Event'},
                target='event.time'),
            u'termination.date': Rule(
                keys=['association.termination.association', ],
                values={'@type': 'dbpedia-owl:Event'},
                target='event.time'),
            u'location': Rule(
                keys=['agent.activity.activity', ],
                values={'@type': 'dbpedia-owl:Event'},
                target='P7_took_place_at',
                viaId='location')
        }

        def varvClaims(self, values):
            protoclaims = {
                u'P31': pywikibot.ItemPage(  # instance of
                    self.repo,
                    u'Q%s' % self.SHIPYARD_Q)
            }

            # handle values
            return protoclaims

        def varvTest(self, hitItem):
            # check if it is a place/organization?
            # alternatively that it is not the wrong one
            pass

        # pass settingson to runLayout()
        self.runLayout(datasetRules=varvRules,
                       datasetProtoclaims=varvClaims,
                       datasetSanityTest=varvTest,
                       label=u'name',
                       shuffle=False)

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
