#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about Artists in KulturNav.

Author: Lokal_Profil
License: MIT

usage:
    python kulturnavBotNatMus.py [OPTIONS]

&params;
"""
# @todo:
# run with -any_item to override wikidata
# Add method to initiate bot with a manual list (e.g. mix'n'match)
#
# Claims to add:
# * P106 occupation - fieldOfActivityOfThePerson
# * connected paintings (different source?, or run this from nationalmuseumSE)

from kulturnavBot import parameter_help
from kulturnavBot import KulturnavBot
from WikidataStuff import WikidataStuff as WD
from kulturnavBotTemplates import Person
import helpers
docuReplacements = {
    '&params;': parameter_help
}

# KulturNav based
EDIT_SUMMARY = 'KulturnavBot(NatMus)'
DATASET_ID = 'c6efd155-8433-4c58-adc9-72db80c6ce50'
ENTITY_TYPE = 'Person'
MAP_TAG = 'entity.sameAs_s'
DATASET_Q = '22681075'


class KulturnavBotNatMus(KulturnavBot):
    """Bot to enrich/create info on Wikidata for Nationalmuseum artists."""

    def run(self):
        """Start the bot."""
        # get basic person rules (seeAlso/sameAs etc. included by KulturnavBot)
        rules = Person.get_rules()

        def claims(self, values):
            """Add protoclaims.

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            # get basic person claims
            protoclaims = Person.get_claims(self, values)

            # add claim about natmus_artist_id
            if values[u'seeAlso'] is not None:
                if isinstance(values[u'seeAlso'], (str, unicode)):
                    values[u'seeAlso'] = helpers.listify(values[u'seeAlso'])
                for sa in values[u'seeAlso']:
                    if u'collection.nationalmuseum.se/eMuseumPlus' in sa:
                        object_id = sa.split('objectId=')[-1].split('&')[0]
                        protoclaims['P2538'] = WD.Statement(object_id)
                        break

            return protoclaims

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=Person.person_test,
                       label=u'name',
                       shuffle=True)

    @classmethod
    def main(cls, *args):
        """Start the bot from the command line."""
        cls.setVariables(
            dataset_q=DATASET_Q,
            dataset_id=DATASET_ID,
            entity_type=ENTITY_TYPE,
            map_tag=MAP_TAG,
            edit_summary=EDIT_SUMMARY
        )
        super(KulturnavBotNatMus, cls).main(*args)


if __name__ == "__main__":
    KulturnavBotNatMus.main()
