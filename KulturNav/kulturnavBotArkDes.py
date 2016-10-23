#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about Architects in KulturNav.

Author: Lokal_Profil
License: MIT

usage:
    python KulturNav/kulturnavBotArkDes.py [OPTIONS]

&params;
"""
from kulturnavBot import parameter_help
from kulturnavBot import KulturnavBot
from WikidataStuff import WikidataStuff as WD
from kulturnavBotTemplates import Person
docuReplacements = {
    '&params;': parameter_help
}


class KulturnavBotArkDes(KulturnavBot):
    """Bot to enrich/create info on Wikidata for ArkDes architects."""

    # KulturNav based
    EDIT_SUMMARY = 'import using #Kulturnav #ArkDes data'
    DATASET_ID = '2b7670e1-b44e-4064-817d-27834b03067c'
    ENTITY_TYPE = 'Person'
    MAP_TAG = 'entity.sameAs_s'
    DATASET_Q = '17373699'

    def run(self):
        """Start the bot."""
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

            # occupation ARCHITECT = Q42973
            protoclaims['P106'] = WD.Statement(self.wd.QtoItemPage('Q42973'))

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
        super(KulturnavBotArkDes, cls).main(*args)


if __name__ == "__main__":
    KulturnavBotArkDes.main()
