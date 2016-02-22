#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Contains templates which can be used for actual kulturnavBots.

Author: Lokal_Profil
License: MIT

"""
import helpers
from kulturnavBot import Rule
from WikidataStuff import WikidataStuff as WD


class Person(object):
    """The basic buildingblocks for a kulturnavBot looking at people."""

    @staticmethod
    def get_rules():
        """Retrieve the basic rules for a person.

        @return: the rules
        @rtype: dict of Rule/None
        """
        # Removed years due to 1970 bug
        rules = {
            # u'deathDate': None,
            u'deathPlace': None,
            u'deathPlace_P7': Rule(
                keys='deathDate',
                values={'@type': 'cidoc-crm:E69_Death'},
                target='P7_took_place_at',
                viaId='location'),
            # u'birthDate': None,
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
        return rules

    @staticmethod
    def get_claims(bot, values):
        """Retrieve the basic claims for a person.

        @param bot: the instance of the bot calling upon the template
        @param bot: KulturnavBot
        @param values: the values extracted using the rules
        @type values: dict
        @return: the protoclaims
        @rtype: dict PID-WD.Statement pairs
        """
        protoclaims = {}

        # instance of HUMAN = Q5
        protoclaims[u'P31'] = WD.Statement(
            bot.wd.QtoItemPage(u'Q5'))

        if values.get(u'deathDate'):
            protoclaims[u'P570'] = WD.Statement(
                helpers.iso_to_WbTime(values[u'deathDate']))

        if values.get(u'deathPlace'):
            protoclaims[u'P20'] = WD.Statement(
                bot.dbpedia2Wikidata(values[u'deathPlace']))
        elif values.get(u'deathPlace_P7'):
            protoclaims[u'P20'] = WD.Statement(
                bot.location2Wikidata(values[u'deathPlace_P7']))

        if values.get(u'birthDate'):
            protoclaims[u'P569'] = WD.Statement(
                helpers.iso_to_WbTime(values[u'birthDate']))

        if values.get(u'birthPlace'):
            protoclaims[u'P19'] = WD.Statement(
                bot.dbpedia2Wikidata(values[u'birthPlace']))
        elif values.get(u'birthPlace_P7'):
            protoclaims[u'P19'] = WD.Statement(
                bot.location2Wikidata(values[u'birthPlace_P7']))

        if values.get(u'gender'):
            # dbGender returns a WD.Statement
            protoclaims[u'P21'] = bot.dbGender(values[u'gender'])

        if values.get(u'firstName'):
            protoclaims[u'P735'] = WD.Statement(
                bot.dbName(values[u'firstName'], u'firstName'))

        if values.get(u'lastName'):
            protoclaims[u'P734'] = WD.Statement(
                bot.dbName(values[u'lastName'], u'lastName'))

        if values.get(u'person.nationality'):
            # there can be multiple values
            values[u'person.nationality'] = helpers.listify(
                values[u'person.nationality'])
            claim = []
            for pn in values[u'person.nationality']:
                claim.append(WD.Statement(bot.location2Wikidata(pn)))
            if claim:
                protoclaims[u'P27'] = claim

        return protoclaims

    @staticmethod
    def person_test(bot, hit_item):
        """Fail if target is an instance of "group of people"/Q16334295.

        @param bot: the instance of the bot calling upon the template
        @param bot: KulturnavBot
        @param hit_item: target item to test
        @type hit_item: pywikibot.ItemPage
        @rtype: bool
        """
        return bot.withoutClaimTest(hit_item,
                                    bot.IS_A_P,
                                    'Q16334295',
                                    u'group of people')
