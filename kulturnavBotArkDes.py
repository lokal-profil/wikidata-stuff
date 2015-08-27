#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about Architects in KulturNav.

usage:
    python kulturnavBotArkDes.py [OPTIONS]

Author: Lokal_Profil
License: MIT

Options (may be omitted):
  -cutoff:INT       number of entries to process before terminating
  -maxHits:INT      number of items to request at a time from Kulturnav
                    (default 250)
"""
import pywikibot
from kulturnavBot import KulturnavBot
from kulturnavBot import Rule
from WikidataStuff import WikidataStuff as WD

# KulturNav based
EDIT_SUMMARY = 'KulturnavBot(ArkDes)'
DATASET_ID = '2b7670e1-b44e-4064-817d-27834b03067c'
ENTITY_TYPE = 'Person'
MAP_TAG = 'entity.sameAs_s'
DATASET_Q = '17373699'


class KulturnavBotArkDes(KulturnavBot):
    """
    A bot to enrich and create information on Wikidata based on KulturNav info
    """
    ARCHITECT_Q = '42973'
    GROUP_OF_PEOPLE_Q = '16334295'
    HUMAN_Q = '5'

    def run(self, cutoff=None):
        """
        Starts the robot
        """
        rules = {
            u'deathDate': None,
            u'deathPlace': None,
            u'deathPlace_P7': Rule(
                keys='deathDate',
                values={'@type': 'cidoc-crm:E69_Death'},
                target='P7_took_place_at',
                viaId='location'),
            u'birthDate': None,
            u'birthPlace': None,
            u'birthPlace_P7': Rule(
                keys='birthDate',
                values={'@type': 'cidoc-crm:E67_Birth'},
                target='P7_took_place_at',
                viaId='location'),
            u'firstName': None,
            u'gender': None,
            u'lastName': None,
            u'name': None,
            u'person.nationality': None
        }

        def claims(self, values):
            protoclaims = {
                # instance of
                u'P31': WD.Statement(pywikibot.ItemPage(
                    self.repo,
                    u'Q%s' % self.HUMAN_Q)),
                # occupation
                u'P106': WD.Statement(pywikibot.ItemPage(
                    self.repo,
                    u'Q%s' % self.ARCHITECT_Q))
                }
            # P106 occupation - fieldOfActivityOfThePerson

            if values[u'deathDate']:
                protoclaims[u'P570'] = WD.Statement(
                    self.dbDate(values[u'deathDate']))
            if values[u'deathPlace']:
                protoclaims[u'P20'] = WD.Statement(
                    self.dbpedia2Wikidata(values[u'deathPlace']))
            elif values[u'deathPlace_P7']:
                protoclaims[u'P20'] = WD.Statement(
                    self.location2Wikidata(values[u'deathPlace_P7']))
            if values[u'birthDate']:
                protoclaims[u'P569'] = WD.Statement(
                    self.dbDate(values[u'birthDate']))
            if values[u'birthPlace']:
                protoclaims[u'P19'] = WD.Statement(
                    self.dbpedia2Wikidata(values[u'birthPlace']))
            elif values[u'birthPlace_P7']:
                protoclaims[u'P19'] = WD.Statement(
                    self.location2Wikidata(values[u'birthPlace_P7']))
            if values[u'gender']:
                # dbGender returns a WD.Statement
                protoclaims[u'P21'] = self.dbGender(values[u'gender'])
            if values[u'firstName']:
                protoclaims[u'P735'] = WD.Statement(
                    self.dbName(values[u'firstName'],
                                u'firstName'))
            if values[u'lastName']:
                protoclaims[u'P734'] = WD.Statement(
                    self.dbName(values[u'lastName'],
                                u'lastName'))
            if values[u'person.nationality']:
                protoclaims[u'P27'] = WD.Statement(
                    self.location2Wikidata(
                        values[u'person.nationality']))

            return protoclaims

        def personTest(self, hitItem):
            """
            Fail if contains an is instance of group of people claim
            """
            return self.withoutClaimTest(hitItem,
                                         self.IS_A_P,
                                         self.GROUP_OF_PEOPLE_Q,
                                         u'group of people')

        # pass settingson to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=personTest,
                       label=u'name',
                       shuffle=True)

    @classmethod
    def main(cls, *args):
        cls.setVariables(
            dataset_q=DATASET_Q,
            dataset_id=DATASET_ID,
            entity_type=ENTITY_TYPE,
            map_tag=MAP_TAG,
            edit_summary=EDIT_SUMMARY
        )
        super(KulturnavBotArkDes, cls).main(*args)


if __name__ == "__main__":
    KulturnavBotArkDes.main()
