#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about Maritime objects in KulturNav.

usage:
    python kulturnavSMM.py [OPTIONS]

Author: Lokal_Profil
License: MIT

Options (required):
-dataset:STR       the dataset to work on

&params;
"""
import pywikibot
from kulturnavBot import parameter_help
from kulturnavBot import KulturnavBot
from kulturnavBot import Rule
from WikidataStuff import WikidataStuff as WD
from kulturnavBotTemplates import Person
import helpers
docuReplacements = {
    '&params;': parameter_help
}


class KulturnavBotSMM(KulturnavBot):
    """Bot to enrich/create info on Wikidata for SMM naval objects."""

    # KulturNav based
    EDIT_SUMMARY = 'KulturnavBot(SMM)'
    DATASETS = {
        u'Fartyg': {
            'id': 0,
            'fullName': u'Fartyg',
            'DATASET_ID': '9a816089-2156-42ce-a63a-e2c835b20688',
            'ENTITY_TYPE': 'NavalVessel',
            'DATASET_Q': '20734454'},
        u'Fartygstyper': {
            'id': 1,
            'fullName': u'Fartygstyper',
            'DATASET_ID': 'c43d8eba-030b-4542-b1ac-6a31a0ba6d00',
            'ENTITY_TYPE': 'Concept',
            'MAP_TAG': 'concept.exactMatch_s',
            'DATASET_Q': '20103697'},
        u'Namngivna': {
            'id': 2,
            'fullName': u'Namngivna fartygstyper',
            'DATASET_ID': '51f2bd1f-7720-4f03-8d95-c22a85d26bbb',
            'ENTITY_TYPE': 'Concept',
            'MAP_TAG': 'concept.exactMatch_s',
            'DATASET_Q': '20742915'},
        u'Personer': {
            'id': 3,
            'fullName': u'Personer verksamma inom fartygs- och båtbyggeri',
            'DATASET_ID': 'c6a7e732-650f-4fdb-a34c-366088f1ff0e',
            'ENTITY_TYPE': 'Person',
            'DATASET_Q': '20669482'},
        u'Serietillverkade': {
            'id': 4,
            'fullName': u'Serietillverkade fartyg',
            'DATASET_ID': '6a98b348-8c90-4ccc-9da7-42351bd4feb7',
            'ENTITY_TYPE': 'NavalVesselDesign',
            'DATASET_Q': '20742975'},
        u'Klasser': {
            'id': 5,
            'fullName': u'Svenska marinens klasser för örlogsfartyg',
            'DATASET_ID': 'fb4faa4b-984a-404b-bdf7-9c24a298591e',
            'ENTITY_TYPE': 'NavalVesselDesign',
            'DATASET_Q': '20742782'},
        u'Varv': {
            'id': 6,
            'fullName': u'Varv',
            'DATASET_ID': 'b0fc1427-a9ab-4239-910a-cd02c02c4a76',
            'ENTITY_TYPE': 'Organization',
            'DATASET_Q': '20669386'}
    }
    MAP_TAG = 'entity.sameAs_s'

    DATASET = None  # set by setDataset()
    GROUP_OF_PEOPLE_Q = '16334295'
    HUMAN_Q = '5'
    SHIPYARD_Q = '190928'
    SHIPCLASS_Q = '559026'
    SUBMARINECLASS_Q = '1428357'
    BOATTYPE_Q = '16103215'
    SUBMARINETYPE_K = 'd7286bae-9e1f-4048-94b5-f70017d139f8'
    SHIPTYPE_Q = '2235308'
    SWENAVY_Q = '1141396'
    COMPANY_Q = '783794'
    ORGANISATION_Q = '43229'
    IKNO_K = u'http://kulturnav.org/2c8a7e85-5b0c-4ceb-b56f-a229b6a71d2a'
    classList = None
    typeList = None
    allShipTypes = None  # any item in the ship type tree

    def run(self):
        """Start the bot."""
        # switch run method based on DATASET
        if self.DATASET == 'Personer':
            self.runPerson()
        elif self.DATASET == 'Varv':
            self.runVarv()
        elif self.DATASET == 'Fartyg':
            self.classList = self.wd.wdqLookup(
                u'CLAIM[1248]{CLAIM[972:%s]}' %
                self.DATASETS[u'Klasser']['DATASET_Q'])
            self.typeList = self.wd.wdqLookup(
                u'CLAIM[1248]{'
                u'CLAIM[972:%s] OR CLAIM[972:%s] OR CLAIM[972:%s]}' % (
                    self.DATASETS[u'Fartygstyper']['DATASET_Q'],
                    self.DATASETS[u'Namngivna']['DATASET_Q'],
                    self.DATASETS[u'Serietillverkade']['DATASET_Q']))
            self.allShipTypes = self.wd.wdqLookup(
                u'CLAIM[31:%s]' % self.SHIPTYPE_Q)
            self.allShipTypes += self.wd.wdqLookup(
                u'CLAIM[31:%s]' % self.BOATTYPE_Q)
            self.runFartyg()
        elif self.DATASET == 'Klasser':
            self.runKlasser()
        elif self.DATASET == 'Fartygstyper':
            self.runFartygstyper()
        elif self.DATASET == 'Namngivna':
            self.runNamngivna()
        elif self.DATASET == 'Serietillverkade':
            self.runSerietillverkade()
        else:
            raise NotImplementedError("Please implement this dataset: %s"
                                      % self.DATASET)

    def runPerson(self):
        """Start a bot for adding info on people."""
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

            # P106 occupation - fieldOfActivityOfThePerson
            return protoclaims

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=Person.person_test,
                       label=u'name',
                       shuffle=True)

    def runVarv(self):
        """Start a bot for adding info on shipyards."""
        rules = {
            u'name': None,
            u'agent.ownership.owner': None,
            u'establishment.date': Rule(
                keys='association.establishment.association',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.time'),
            u'termination.date': Rule(
                keys='association.termination.association',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.time'),
            u'location': Rule(
                keys='agent.activity.activity',
                values={'@type': 'dbpedia-owl:Event'},
                target='P7_took_place_at',
                viaId='location')
        }

        def claims(self, values):
            """Add protoclaims.

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            protoclaims = {
                # instance of
                u'P31': WD.Statement(
                    self.wd.QtoItemPage(u'Q%s' % self.SHIPYARD_Q))
            }

            # handle values
            if values[u'establishment.date']:
                protoclaims[u'P571'] = WD.Statement(
                    self.dbDate(values[u'establishment.date']))
            if values[u'termination.date']:
                protoclaims[u'P576'] = WD.Statement(
                    self.dbDate(values[u'termination.date']))
            if values[u'agent.ownership.owner']:
                protoclaims[u'P127'] = WD.Statement(
                    self.kulturnav2Wikidata(
                        values[u'agent.ownership.owner']))
            self.set_location(values, protoclaims)

            return protoclaims

        def test(self, hit_item):
            """Test that this isn't something other than a shipyard.

            Fail if has instance claims and none of them are
            shipyard/company/organisation

            @parm hit_item: item to check
            @type hit_item: pywikibot.ItemPage
            @return: if test passed
            @rtype: bool
            """
            return self.withClaimTest(hit_item,
                                      self.IS_A_P,
                                      [self.SHIPYARD_Q,
                                       self.COMPANY_Q,
                                       self.ORGANISATION_Q],
                                      u'shipyard')

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=test,
                       label=u'name',
                       shuffle=False)

    def runFartyg(self):
        """Start a bot for adding info on ships."""
        rules = {
            u'entity.name': Rule(  # force to look in top level
                keys='inDataset',
                values=None,
                target='entity.name'),
            u'altLabel': None,
            u'navalVessel.signalLetters': None,
            u'entity.code': None,
            u'built.date': Rule(
                keys='navalVessel.built.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.timespan',
                viaId='startDate'),
            u'built.location': Rule(
                keys='navalVessel.built.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='P7_took_place_at',
                viaId='location'),
            u'built.shipyard': Rule(
                keys='navalVessel.built.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='navalVessel.built.shipyard'),
            u'launched.date': Rule(
                keys='navalVessel.launched.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.time'),
            u'launched.location': Rule(
                keys='navalVessel.launched.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='P7_took_place_at',
                viaId='location'),
            u'launched.shipyard': Rule(
                keys='navalVessel.launched.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='navalVessel.launched.shipyard'),
            u'delivered.date': Rule(
                keys='navalVessel.delivered.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.time'),
            u'decommissioned.date': Rule(
                keys='navalVessel.decommissioned.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.time'),
            u'navalVessel.type': None,
            u'navalVessel.otherType': None,
            u'homePort': Rule(
                keys='navalVessel.homePort.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='P7_took_place_at',
                viaId='location'),
            u'homePort.start': Rule(
                keys='navalVessel.homePort.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.timespan',
                viaId='startDate'),
            u'homePort.end': Rule(
                keys='navalVessel.homePort.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.timespan',
                viaId='endDate'),
            u'navalVessel.isSubRecord': None,
            u'navalVessel.hasSubRecord': None,
            u'registration.number': Rule(
                keys=None,
                values={},
                target='navalVessel.registration',
                viaId='registration.number'),
            u'registration.type': Rule(
                keys=None,
                values={},
                target='navalVessel.registration',
                viaId='registration.register'),
            u'constructor': Rule(
                keys='navalVessel.constructed.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='navalVessel.constructed.constructedBy'),
            u'constructor.start': Rule(
                keys='navalVessel.constructed.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.timespan',
                viaId='startDate'),
            u'constructor.end': Rule(
                keys='navalVessel.constructed.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.timespan',
                viaId='endDate')
            # navalVessel.measurement
        }

        def claims(self, values):
            """Add protoclaims.

            @todo: implement:
                u'delivered.date'
                u'navalVessel.isSubRecord'
                u'navalVessel.hasSubRecord'

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            # handle altNames together with names
            values[u'entity.name'] = KulturnavBotSMM.prep_names(values)
            # convert from ALL-CAPS
            for i, v in enumerate(values[u'entity.name']):
                values[u'entity.name'][i][u'@value'] = \
                    v[u'@value'].capitalize()

            # bundle type and otherType
            values[u'navalVessel.type'] = KulturnavBotSMM.prep_types(values)

            # check that we can always safely ignore entity.code
            if values[u'navalVessel.signalLetters'] != values[u'entity.code']:
                pywikibot.output(u'signalLetters!=code for %s: %s <> %s' %
                                 (values[u'identifier'],
                                  values[u'navalVessel.signalLetters'],
                                  values[u'entity.code']))
                exit(1)

            protoclaims = {}

            # P31/P289 - ship type/class
            if values[u'navalVessel.type']:
                shipClass = []
                shipType = []
                for val in values[u'navalVessel.type']:
                    item = self.kulturnav2Wikidata(val)
                    if item:
                        q = int(item.title()[1:])
                        if q in self.classList:
                            shipClass.append(WD.Statement(item))
                        elif q in self.typeList:
                            shipType.append(WD.Statement(item))
                        else:
                            pywikibot.output(u'Q%d not matched as either ship'
                                             u'type or ship class' % q)
                if shipClass:
                    protoclaims[u'P289'] = shipClass
                if shipType:
                    protoclaims[u'P31'] = shipType

            # P879 - registration number
            self.set_registration_no(values, protoclaims)

            # P504 - homeport
            if values[u'homePort']:
                protoclaims[u'P504'] = self.addStartEndStatement(
                    self.kulturnav2Wikidata(values[u'homePort']),
                    values[u'homePort.start'],
                    values[u'homePort.end'])

            # P2317 - call sign
            if values[u'navalVessel.signalLetters']:
                protoclaims[u'P2317'] = WD.Statement(
                    values[u'navalVessel.signalLetters'])

            # P176 - Manufacturer (Shipyard)
            self.set_shipyard(values, protoclaims)

            # P287 - Designer (Constructor)
            self.set_constructor(values, protoclaims)

            # P793 - Events
            # events are only added IFF they have an associated date
            # @todo: commissioned: Q14475832
            events = []

            # built: Q474200
            event = WD.Statement(self.wd.QtoItemPage('Q474200'))
            if self.set_date_qualifier(values, 'built', event,
                                       prop=helpers.END_P):
                self.set_location_qualifier(values, 'built', event)
                # u'built.shipyard'
                events.append(event)

            # launched: Q596643
            event = WD.Statement(self.wd.QtoItemPage('Q596643'))
            if self.set_date_qualifier(values, 'launched', event):
                # u'launched.shipyard'
                events.append(event)

            # decommissioned: Q7497952
            event = WD.Statement(self.wd.QtoItemPage('Q7497952'))
            if self.set_date_qualifier(values, 'decommissioned', event):
                events.append(event)

            # set all events
            if events:
                protoclaims[u'P793'] = events

            return protoclaims

        def test(self, hit_item):
            """Test if the item is a type of ship/boat.

            Is there any way of testing that it is a ship... of some type?
            Possibly if any of P31 is in wdqList for claim[31:2235308].

            @parm hit_item: item to check
            @type hit_item: pywikibot.ItemPage
            @return: if test passed
            @rtype: bool
            """
            P = u'P31'
            if P not in hit_item.claims.keys():
                return True
            claims = []
            for claim in hit_item.claims[P]:
                # add resolved Qno of each claim
                target = self.wd.bypassRedirect(claim.getTarget())
                claims.append(int(target.title()[1:]))
            # check if any of the claims are recognised shipTypes
            if any(x in claims for x in self.allShipTypes):
                return True
            pywikibot.output(u'%s is identified as something other than '
                             u'a ship/boat type. Check!' % hit_item.title())
            return False

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=test,
                       label=u'entity.name',
                       shuffle=False)

    def runKlasser(self):
        """Start a bot for adding info on ship classes."""
        rules = {
            u'entity.name': Rule(  # force to look in top level
                keys='inDataset',
                values=None,
                target='entity.name'),
            u'navalVessel.type': None,  # a type or another class
            u'navalVessel.otherType': None,
            u'altLabel': None,
            u'constructor': Rule(
                keys='navalVessel.constructed.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='navalVessel.constructed.constructedBy'),
            u'constructor.start': Rule(
                keys='navalVessel.constructed.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.timespan',
                viaId='startDate'),
            u'constructor.end': Rule(
                keys='navalVessel.constructed.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.timespan',
                viaId='endDate')
            # navalVessle.measurement
        }

        def claims(self, values):
            """Add protoclaims.

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            # handle altNames together with names
            values[u'entity.name'] = KulturnavBotSMM.prep_names(values)

            # bundle type and otherType
            values[u'navalVessel.type'] = KulturnavBotSMM.prep_types(values)

            protoclaims = {
                # operator, SwedishNavy
                u'P137': WD.Statement(
                    self.wd.QtoItemPage(self.SWENAVY_Q))
            }

            # P31 - instance of
            # ship class unless a submarine
            class_Q = u'Q%s' % self.SHIPCLASS_Q
            if values[u'navalVessel.type'] and \
                    any(x.endswith(self.SUBMARINETYPE_K)
                        for x in values[u'navalVessel.type']):
                class_Q = u'Q%s' % self.SUBMARINECLASS_Q
            protoclaims[u'P31'] = WD.Statement(
                self.wd.QtoItemPage(class_Q))

            # P279 - subgroup
            self.set_subgroup(values, protoclaims)

            # P287 - Designer (Constructor)
            self.set_constructor(values, protoclaims)

            return protoclaims

        def test(self, hit_item):
            """Fail if instance claims and none of them are ship class.

            @parm hit_item: item to check
            @type hit_item: pywikibot.ItemPage
            @return: if test passed
            @rtype: bool
            """
            return self.withClaimTest(hit_item,
                                      self.IS_A_P,
                                      [self.SHIPCLASS_Q,
                                       self.SHIPTYPE_Q,
                                       self.SUBMARINECLASS_Q],
                                      u'ship class or type')

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=test,
                       label=u'entity.name',
                       shuffle=False)

    def runFartygstyper(self):
        """Start a bot for adding info on ship types.

        @todo: if a boat_type then it should be possible to
               add everything except P31
        """
        rules = {
            u'prefLabel': None,
            u'altLabel': None,
            u'broader': None
        }

        def claims(self, values):
            """Add protoclaims.

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            # handle prefLabel together with altLabel
            values[u'prefLabel'] = KulturnavBotSMM.prepare_labels(values)

            protoclaims = {}
            # P31 - instance of
            self.set_is_ship(protoclaims)

            # P279 - subgroup self.kulturnav2Wikidata(broader)
            if values[u'broader']:
                protoclaims[u'P279'] = WD.Statement(
                    self.kulturnav2Wikidata(
                        values[u'broader']))
            return protoclaims

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=self.test_shiptype,
                       label=u'prefLabel',
                       shuffle=False)

    def runNamngivna(self):
        """Start a bot for adding info on named ship models."""
        rules = {
            u'prefLabel': None,
            u'altLabel': None,
            u'navalVessel.type': None,
            u'navalVessel.otherType': None
        }

        def claims(self, values):
            """Add protoclaims.

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            # handle prefLabel together with altLabel
            values[u'prefLabel'] = KulturnavBotSMM.prepare_labels(values)

            # bundle type and otherType
            values[u'navalVessel.type'] = KulturnavBotSMM.prepare_type(values)

            protoclaims = {}
            # P31 - instance of
            self.set_is_ship(protoclaims)

            # P279 - subgroup
            self.set_subgroup(values, protoclaims)

            return protoclaims

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=self.test_shiptype,
                       label=u'prefLabel',
                       shuffle=False)

    def runSerietillverkade(self):
        """Start a bot for adding info on serially produced ships."""
        rules = {
            u'entity.name': Rule(  # force to look in top level
                keys='inDataset',
                values=None,
                target='entity.name'),
            u'altLabel': None,
            u'navalVessel.type': None,
            u'navalVessel.otherType': None,
            u'constructor': Rule(
                keys='navalVessel.constructed.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='navalVessel.constructed.constructedBy'),
            u'constructor.start': Rule(
                keys='navalVessel.constructed.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.timespan',
                viaId='startDate'),
            u'constructor.end': Rule(
                keys='navalVessel.constructed.navalVessel',
                values={'@type': 'dbpedia-owl:Event'},
                target='event.timespan',
                viaId='endDate')
            # navalVessel.measurement
        }

        def claims(self, values):
            """Add protoclaims.

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            # handle altNames together with names
            values[u'entity.name'] = KulturnavBotSMM.prep_names(values)

            # bundle type and otherType
            values[u'navalVessel.type'] = KulturnavBotSMM.prep_types(values)

            protoclaims = {}
            # P31 - instance of
            self.set_is_ship(protoclaims)

            # P279 - subgroup
            self.set_subgroup(values, protoclaims)

            # P287 - Designer (Constructor)
            self.set_constructor(values, protoclaims)

            return protoclaims

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=self.test_shiptype,
                       label=u'entity.name',
                       shuffle=False)

    def test_shiptype(self, hit_item):
        """Fail if there are instance claims and none of them are ship type.

        @parm hit_item: item to check
        @type hit_item: pywikibot.ItemPage
        @return: if test passed
        @rtype: bool
        """
        return self.withClaimTest(hit_item,
                                  self.IS_A_P,
                                  self.SHIPTYPE_Q,
                                  u'ship type')

    def set_shipyard(self, values, protoclaims):
        """Identify Manufacturer/Shipyard (P176) and add to claims.

        Adds the claim to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        if values[u'built.shipyard'] or values[u'launched.shipyard']:
            shipyard = helpers.bundleValues(
                [values[u'built.shipyard'],
                 values[u'launched.shipyard']])
            shipyard = list(set(shipyard))
            if len(shipyard) > 1:
                pywikibot.output(u'Found multiple shipyards, not sure how'
                                 u'to proceed: %s' % values[u'identifier'])
            else:
                protoclaims[u'P176'] = WD.Statement(
                    self.kulturnav2Wikidata(
                        shipyard[0]))

    def set_registration_no(self, values, protoclaims):
        """Identify registration number (P879) and add to claims.

        Adds the claim to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        if values[u'registration.number']:
            # there can be multiple values
            values[u'registration.number'] = helpers.listify(
                values[u'registration.number'])
            values[u'registration.type'] = helpers.listify(
                values[u'registration.type'])

            # only one type is currently mapped
            claim = []
            for i, v in enumerate(values[u'registration.number']):
                if values[u'registration.type'][i] == self.IKNO_K:
                    claim.append(WD.Statement(v))
            if claim:
                protoclaims[u'P879'] = claim

    def set_subgroup(self, values, protoclaims):
        """Identify subgroup (P279) and add to claims.

        Adds the claim to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        if values[u'navalVessel.type']:
            claims = []
            for t in values[u'navalVessel.type']:
                item = self.kulturnav2Wikidata(t)
                if item:
                    claims.append(WD.Statement(item))
            if claims:
                protoclaims[u'P279'] = claims

    def set_constructor(self, values, protoclaims):
        """Identify constructor(s)/designers (P287) and add to claims.

        Adds the claim to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        if values[u'constructor']:
            values[u'constructor'] = self.listify(values[u'constructor'])
            claims = []
            for val in values[u'constructor']:
                claim = WD.Statement(self.kulturnav2Wikidata(val))
                claims.append(
                    helpers.add_start_end_qualifiers(
                        claim,
                        values[u'constructor.start'],
                        values[u'constructor.end']))
            if claims:
                protoclaims[u'P287'] = claims

    def set_is_ship(self, protoclaims):
        """Set instance_of (P31) to Ship/Q2235308.

        Adds the claim, with the suitable property, to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        protoclaims[u'P31'] = WD.Statement(
            self.wd.QtoItemPage(u'Q%s' % self.SHIPTYPE_Q))

    def set_location(self, values, protoclaims):
        """Identify a location and its type then add to claims.

        Adds the claim, with the suitable property, to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        if values[u'location']:
            location_q = self.location2Wikidata(values[u'location'])
            prop = self.getLocationProperty(location_q)
            if prop:
                protoclaims[prop] = WD.Statement(
                    self.location2Wikidata(values[u'location']))

    def set_location_qualifier(self, values, key, statement):
        """Add a location (P279) qualifier to a statement.

        @param values: the values extracted using the rules
        @type values: dict
        @param key: the key to which the location is associated
            e.g. built for built.location
        @type key: str
        @param statement: statment to add qualifier to
        @type statement: WD.Statement
        @return: if qualifier was found
        @rtype: bool
        """
        location_key = u'%s.location' % key
        if not values[location_key]:
            return False
        statement.addQualifier(
            WD.Qualifier(
                P=self.PLACE_P,
                itis=self.location2Wikidata(values[location_key])))
        return True

    def set_date_qualifier(self, values, key, statement, prop=None):
        """Add a date qualifier to a statement.

        @param values: the values extracted using the rules
        @type values: dict
        @param key: the key to which the location is associated
            e.g. built for built.location
        @type key: str
        @param statement: statment to add qualifier to
        @type statement: WD.Statement
        @param prop: the property to use, defaults to self.TIME_P/P585
        @type prop: str
        @return: if qualifier was found
        @rtype: bool
        """
        prop = prop or self.TIME_P
        date_key = u'%s.date' % key
        if not values[date_key]:
            return False
        statement.addQualifier(
            WD.Qualifier(
                P=prop,
                itis=self.dbDate(values[date_key])))
        return True

    @staticmethod
    def prepare_labels(values):
        """Combine prefLabel with altLabel and trim any comments.

        @param values: the values extracted using the rules
        @type values: dict
        @return: the combined list of scrubbed labels
        @rtype: list
        """
        # handle prefLabel together with altLabel
        pref_label = helpers.bundle_values(
            [values[u'prefLabel'],
             values[u'altLabel']])

        # remove comments from lables
        for i, v in enumerate(pref_label):
            if '(' in v['@value']:
                val = v['@value'].split('(')[0].strip()
                pref_label[i]['@value'] = val

        return pref_label

    def prep_names(values):
        """Handle altLabel together with entity.name.

        @param values: the values extracted using the rules
        @type values: dict
        @return: the combined list of names
        @rtype: list
        """
        # handle altNames together with names
        return helpers.bundleValues(
            [values[u'entity.name'],
             values[u'altLabel']])

    def prep_types(values):
        """Handle otherType together with type.

        @param values: the values extracted using the rules
        @type values: dict
        @return: the combined list of types
        @rtype: list
        """
        return helpers.bundleValues(
            [values[u'navalVessel.type'],
             values[u'navalVessel.otherType']])

    @classmethod
    def get_dataset_variables(cls, *args):
        """Extract the matching dataset from the -dataset arg.

        Ideally this would be called after pywikibot variables have been
        dealt with.

        TODO: Ideally this would be handled differently e.g. by unhandled
        args in kulturnavBot.main being sent to an overloaded method. This
        would however require set_variables to be handled differently as well.

        @return: The key for the matching entry in DATASETS
        @rtype: str
        """
        if not args:
            args = pywikibot.argvu[1:]

        # allow dataset to be specified through id
        num_pairs = {}
        for k, v in cls.DATASETS.iteritems():
            num_pairs[str(v['id'])] = k

        for arg in args:
            option, sep, value = arg.partition(':')
            if option == '-dataset':
                if value in cls.DATASETS.keys():
                    return value
                elif value in num_pairs.keys():
                    return num_pairs[value]

        # if nothing found
        txt = u''
        for k, v in num_pairs.iteritems():
            txt += u'\n%s %s' % (k, v)
        pywikibot.output(u'No valid -dataset argument was found. This '
                         u'must be given by either number or name.\n'
                         'Available datasets are: %s' % txt)
        exit(1)

    @classmethod
    def main(cls, *args):
        """Start the bot from the command line."""
        # pick one dataset from DATASETS
        cls.DATASET = cls.get_dataset_variables(*args)
        variables = cls.DATASETS[cls.DATASET]

        # override variables and start bot
        cls.set_variables(
            dataset_q=variables.get('DATASET_Q'),
            dataset_id=variables.get('DATASET_ID'),
            entity_type=variables.get('ENTITY_TYPE'),
            map_tag=variables.get('MAP_TAG')
        )
        super(KulturnavBotSMM, cls).main(*args)


if __name__ == "__main__":
    KulturnavBotSMM.main()
