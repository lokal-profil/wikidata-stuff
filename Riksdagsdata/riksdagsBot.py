# -*- coding: utf-8 -*-
"""Bot to import and sourced statements about people in data.riksdag.se.

Bot to import and sourced statements about people also present in
the Riksdag open data on parliment members
(http://data.riksdagen.se/Data/Ledamoter/).

usage:
    python riksdagsBot.py [OPTIONS]

Author: Lokal_Profil
License: MIT

Options (may be omitted):
  -cutoff:INT       number of entries to process before terminating
  -delay:INT        seconds to delay between each riksdag request
                    (default 0)

TODO: note that comparisons need to be done so that it works for
      e.g. Q2740012 i.e. compare only on value (+ any qualifiers
           present in both). Then add any new and keep any old. This
           needs to happen in WD though.

See https://github.com/lokal-profil/wikidata-stuff/issues for TODOs
"""
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

# import json
import pywikibot
from WikidataStuff import WikidataStuff as WD
import helpers

STATED_IN_P = 'P248'
RIKSDAG_ID_P = 'P1214'
ORDINAL_P = 'P1545'
POSITION_P = 'P39'
GENDER_P = 'P21'
PARTY_P = 'P102'
LAST_NAME_P = 'P734'
FIRST_NAME_P = 'P735'
DEATH_DATE_P = 'P570'
BIRTH_DATE_P = 'P569'
OF_P = 'P642'


class RiksdagsBot(object):
    """Bot to enrich and add information on Wikidata based on Riksdag info."""

    EDIT_SUMMARY = 'RiksdagsBot'
    FUTURE_YEAR = 2016  # dates in this year or later are the future
    names = {  # a dict of found first/last_name_Q lookups
        u'lastName': {},
        u'firstName': {}}
    current_id = ''  # for debugging

    def __init__(self, dictGenerator, verbose=False):
        """Instantiate a RiksdagsBot object.

        param dictGenerator: A generator that yields Dict objects.
        param verbose: If Bot should operate in Verbose mode, default=False
        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()
        self.cutoff = None
        self.verbose = verbose

        # load mappings
        self.mappings = helpers.load_json_file('mappings.json')

        # trigger wdq query
        self.itemIds = helpers.fill_cache(RIKSDAG_ID_P)

        # set up WikidataStuff object
        self.wd = WD(self.repo)

    def run(self):
        """Start the bot."""
        # run over all matches (up to cutoff)
        # for each fetch the riksdagsdata json
        # load the data then data = data['personlista']['person']
        # send the data for processing and recieve claims
        # store the updates and continue with next
        raise NotImplementedError("Please Implement this method")

    def extractStatements(self, riksdagdata):
        """Extract possible statements from the riksdag data.

        param riksdagsdata: a dict
        return dict of properties and statments
        """
        riksdagId = riksdagdata['intressent_id']
        self.current_id = riksdagId

        # Handle statments
        protoclaims = {}
        protoclaims[GENDER_P] = self.matchGender(riksdagdata['kon'])
        protoclaims[PARTY_P] = self.matchParty(riksdagdata['parti'])
        protoclaims[LAST_NAME_P] = self.matchName(
            riksdagdata['efternamn'], 'lastName')
        protoclaims[FIRST_NAME_P] = self.matchName(
            riksdagdata['tilltalsnamn'], 'firstName')
        protoclaims[BIRTH_DATE_P] = self.matchBirth(riksdagdata['fodd_ar'])
        protoclaims[DEATH_DATE_P] = self.matchDeath(riksdagdata['status'])

        # position data is inconsistent as single entries are sometimes
        # not in a list. hence the listify
        protoclaims[POSITION_P] = self.handlePositions(
            helpers.listify(riksdagdata['personuppdrag']['uppdrag']))
        # valkrets
        # personuppgifter

        # Handle aliases
        # Note that this gives a mistake in names such as "A von B" since
        # the "von" is not part of the sort key.
        fullName = helpers.reorder_names(riksdagdata['sorteringsnamn'])
        iortAlias = self.makeIortAlias(riksdagdata['iort'], fullName)
        names = set(fullName)
        if iortAlias:
            names.add(iortAlias)
        names = list(names)

        return protoclaims, names

    def matchName(self, value, nameType):
        """Match value of name against its wikidata entity.

        param value: str|unicode
        param nameType: str|unicode
        return: WD.Statement|None
        """
        item = helpers.match_name(value, nameType, self.wd)
        if item:
            return WD.Statement(item)
        return None

    def matchGender(self, value):
        """Match value of gender against known mappings.

        param value: str|unicode
        return: WD.Statement|None
        """
        if value in self.mappings['kon']['Q'].keys():
            item = self.wd.QtoItemPage(self.mappings['kon']['Q'][value])
            return WD.Statement(item)
        return None

    def matchParty(self, value):
        """Match value of political party against known mappings.

        param value: str|unicode
        return: WD.Statement|None
        """
        if value in self.mappings['parti']['Q'].keys():
            item = self.wd.QtoItemPage(self.mappings['parti']['Q'][value])
            return WD.Statement(item)
        elif value in self.mappings['parti']['skip'].keys() or value is None:
            return None
        else:
            pywikibot.output(u'Encountered an unknown political party: %s (%s)'
                             % (value, self.current_id))
            return None

    def matchBirth(self, value):
        """Convert value of birth to statement.

        param value: str|unicode
        return: WD.Statement|None
        """
        if value is None or len(value.strip()) == 0:
            return None
        return WD.Statement(helpers.ISO_to_WbTime(value))

    def matchDeath(self, value):
        """Extract death date from status.

        param value: str|unicode
        return: WD.Statement|None
        """
        if value and value.startswith('Avliden'):
            value = value[len('Avliden'):].strip()
            return WD.Statement(helpers.ISO_to_WbTime(value))
        return None

    def makeIortAlias(self, iort, name):
        """Use iort info to create an alias.

        param iort: str|unicode|None
        param name: str|unicode
        return: WD.Statement|None
        """
        if iort is None or len(iort.strip()) == 0:
            return None
        elif name is None or len(name.strip()) == 0:
            return None

        alias = u'%s i %s' % (name, iort)
        return alias

    def handlePositions(self, uppdragList):
        """Construct qualified statements for help positions.

        param uppdragList: list of uppdrag dicts
        return: list of position statements
        """
        uppdragStatements = []
        for uppdrag in uppdragList:
            if uppdrag['typ'] == u'kammaruppdrag':
                uppdragStatements.append(self.handleChamberPosition(uppdrag))
            elif uppdrag['typ'] == u'partiuppdrag':
                uppdragStatements.append(self.handlePartyPosition(uppdrag))
            elif uppdrag['typ'] == u'Departement':
                uppdragStatements.append(self.handleMinistryPosition(uppdrag))
            elif uppdrag['typ'] == u'uppdrag':
                uppdragStatements.append(self.handleCommitteePosition(uppdrag))
            elif uppdrag['typ'] == u'talmansuppdrag':
                uppdragStatements.append(self.handleSpeakerPosition(uppdrag))
            elif uppdrag['typ'] in (u'Riksdagsorgan', u'Europaparlamentet'):
                # consider getting stadsråd-departement from Riksdagsorgan
                # Europaparlamentet is likely very different
                pass
            else:
                pywikibot.output('uppdrag-typ-roll: %s-%s-%s (%s)' %
                                 (uppdrag['typ'], uppdrag['roll_kod'],
                                  uppdrag['uppgift'], self.current_id))
                pass

        return uppdragStatements

    def handleChamberPosition(self, uppdrag):
        """Process positions as member of Parliament.

        param uppdrag: dict
        return WD.Statment|None
        """
        # only considered some positions
        roleMap = 'kammar_roll'
        roleCode = uppdrag['roll_kod']
        if roleCode not in self.mappings[roleMap]['Q'].keys():
            if roleCode not in self.mappings[roleMap]['skip'].keys():
                pywikibot.output('Unknown role: %s (%s-%s)' %
                                 (roleCode, uppdrag['typ'],
                                  self.current_id))
            return None

        # only keep certain statuses
        if uppdrag['status'] not in self.mappings['kammar_status']['keep']:
            if uppdrag['status'] not in self.mappings['kammar_status']['skip']:
                pywikibot.output(u'Unknown status: %s (%s-%s)' %
                                 (uppdrag['status'], uppdrag['typ'],
                                  self.current_id))
            return None

        # expect uppgift = None but keep a note of any new ones
        badComments = self.mappings['kammar_uppgift']['skip']
        if uppdrag['uppgift'] is not None:
            if uppdrag['uppgift'] not in badComments:
                pywikibot.output(u'Non-None uppgift: %s (%s-%s)' %
                                 (uppdrag['uppgift'], uppdrag['typ'],
                                  self.current_id))
            return None

        # create statement based on role
        qNo = self.mappings[roleMap]['Q'][roleCode]
        statement = WD.Statement(self.wd.QtoItemPage(qNo))

        # add standard qualifiers
        helpers.add_start_end_qualifiers(
            statement, uppdrag['from'], self.notFuture(uppdrag['tom']))
        self.addOrdinal(uppdrag['ordningsnummer'], statement)

        return statement

    def handlePartyPosition(self, uppdrag):
        """Process positions within a party.

        param uppdrag: dict
        return WD.Statment|None
        """
        return self.unifiedPositionHandler(uppdrag, 'parti_roll', 'parti')

    def handleMinistryPosition(self, uppdrag):
        """Process positions within a Ministry.

        Skips adding the ministry since this is normally implicit in the
        title. This is not the case for some of the skipped roles.

        param uppdrag: dict
        return WD.Statment|None
        """
        return self.unifiedPositionHandler(uppdrag, 'departement_roll', None)

    def handleCommitteePosition(self, uppdrag):
        """Process positions within a Committee of the Riksdag.

        param uppdrag: dict
        return WD.Statment|None
        """
        return self.unifiedPositionHandler(uppdrag, 'utskott_roll', 'utskott')

    def handleSpeakerPosition(self, uppdrag):
        """Process positions as Speaker of the Riksdag.

        param uppdrag: dict
        return WD.Statment|None
        """
        return self.unifiedPositionHandler(uppdrag, 'talman_roll', None)

    def unifiedPositionHandler(self, uppdrag, roleMap, entityMap):
        """Process position based on known mappings.

        Process positions within a Committee of the Riksdag or a party.

        param uppdrag: dict
        param roleMap: str, key within mappings.json
        param entityMap: str|None, key within mappings.json, skip if None
        return WD.Statment|None
        """
        # only considered some positions
        roleCode = uppdrag['roll_kod']
        if roleCode not in self.mappings[roleMap]['Q'].keys():
            if roleCode not in self.mappings[roleMap]['skip'].keys():
                pywikibot.output('Unknown role: %s (%s-%s)' %
                                 (roleCode, uppdrag['typ'],
                                  self.current_id))
            return None

        # expect status = None
        if uppdrag['status'] is not None:
            pywikibot.output('Non-none status: %s (%s-%s)' %
                             (uppdrag['status'], uppdrag['typ'],
                              self.current_id))
            return None

        # create statement based on role
        qNo = self.mappings[roleMap]['Q'][roleCode]
        statement = WD.Statement(self.wd.QtoItemPage(qNo))

        # identify entity
        if entityMap:
            entityCode = uppdrag['organ_kod'].upper()
            if entityCode in self.mappings[entityMap]['Q'].keys():
                qNo = self.mappings[entityMap]['Q'][entityCode]
                qual = WD.Qualifier(
                    P=OF_P,
                    itis=self.wd.QtoItemPage(qNo))
                statement.addQualifier(qual)
            else:
                pywikibot.output('Unknown entity: %s-%s (%s-%s)' %
                                 (entityCode, uppdrag['uppgift'],
                                  uppdrag['typ'], self.current_id))

        # add standard qualifiers
        helpers.add_start_end_qualifiers(
            statement, uppdrag['from'], self.notFuture(uppdrag['tom']))
        self.addOrdinal(uppdrag['ordningsnummer'], statement)

        return statement

    def notFuture(self, date):
        """Check that a date is not in the future.

        Checks if a date is in the future. If so returns none, else
        returns the string.
        TODO: Remake this using current date and comparing down to day

        param date: ISO date string
        return: str|None
        """
        if helpers.is_int(date[:4]):
            if int(date[:4]) < self.FUTURE_YEAR:
                return date
        return None

    def addOrdinal(self, value, statement):
        """Add an ordinal qualifier.

        Adds the ordinal as a qualifier if it is non-zero

        param value: ordinal
        param statment: statment to add qualifer to
        """
        if value != '0':
            qual = WD.Qualifier(
                P=ORDINAL_P,
                itis=int(value))
            statement.addQualifier(qual)

    def testRun(self):
        """Run a test with hardcoded local files."""
        dataFiles = (
            # u'0574555227504.json',
            # u'0787533297400.json',  # a death
            # u'0643844865712.json',  # a von, ersättare, utskott
            # u'0108961111006.json',  # an iort
            # u'0284192765516.json',  # many different positions/roles
            # various issues (same position double ministries), one day
            # positions, overlaps etc.
            u'0956595590924.json',
        )
        for dataFile in dataFiles:
            data = helpers.load_json_file(dataFile)
            data = data['personlista']['person']
            self.extractStatements(data)

    def testRun2(self):
        """Run a test with a folder of local files."""
        dataFiles = helpers.find_files(u'persons', ('.json',), False)
        print len(dataFiles)
        for dataFile in dataFiles:
            data = helpers.load_json_file(dataFile)
            try:
                data = data['person']
                self.extractStatements(data)
            except KeyError:
                pywikibot.output("%s contains no data" % dataFile)

if __name__ == "__main__":
    # Only valid during testing
    rB = RiksdagsBot(None, verbose=True)
    rB.testRun()
