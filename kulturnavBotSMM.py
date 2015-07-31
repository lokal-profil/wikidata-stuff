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
from WikidataStuff import WikidataStuff as WD

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
        'DATASET_Q': '20669482'},
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
        'DATASET_Q': '20742782'},
    u'Varv': {
        'id': 6,
        'fullName': u'Varv',
        'DATASET_ID': 'b0fc1427-a9ab-4239-910a-cd02c02c4a76',
        'ENTITY_TYPE': 'Organization',
        'DATASET_Q': '20669386'}
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
    SHIPCLASS_Q = '559026'
    SHIPTYPE_Q = '2235308'
    SWENAVY_Q = '1141396'
    COMPANY_Q = '783794'
    IKNO_K = u'http://kulturnav.org/2c8a7e85-5b0c-4ceb-b56f-a229b6a71d2a'

    def run(self):
        """
        Starts the robot
        """
        # switch run method based on DATASET
        if self.DATASET == 'Personer':
            self.runPerson()
        elif self.DATASET == 'Varv':
            self.runVarv()
        elif self.DATASET == 'Fartyg':
            # make list of allowed ship types for testing
            # make list of added Klasser for Klass-matching
            self.runFartyg()
        elif self.DATASET == 'Klasser':
            self.runKlasser()
        elif self.DATASET == 'Fartygstyper':
            self.runFartygstyper()
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
            u'name': None,
            u'person.nationality': None
        }

        def personClaims(self, values):
            protoclaims = {
                # instance of
                u'P31': WD.Statement(pywikibot.ItemPage(
                    self.repo,
                    u'Q%s' % self.HUMAN_Q))
                }
            # P106 occupation - fieldOfActivityOfThePerson

            # if values[u'deathPlace']:
            #    protoclaims[u'P20'] = WD.Statement(
            #        self.dbpedia2Wikidata(values[u'deathPlace']))
            if values[u'deathDate']:
                protoclaims[u'P570'] = WD.Statement(
                    self.dbDate(values[u'deathDate']))
            # if values[u'birthPlace']:
            #    protoclaims[u'P19'] = WD.Statement(
            #        self.dbpedia2Wikidata(values[u'birthPlace']))
            if values[u'birthDate']:
                protoclaims[u'P569'] = WD.Statement(
                    self.dbDate(values[u'birthDate']))
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

        # pass settings on to runLayout()
        self.runLayout(datasetRules=personRules,
                       datasetProtoclaims=personClaims,
                       datasetSanityTest=personTest,
                       label=u'name',
                       shuffle=True)

    def runVarv(self):
        """
        TODO:
            Make a protoclaim using location
        """
        varvRules = {
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

        def varvClaims(self, values):
            protoclaims = {
                # instance of
                u'P31': WD.Statement(pywikibot.ItemPage(
                    self.repo,
                    u'Q%s' % self.SHIPYARD_Q))
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
            if values[u'location']:
                location_Q = self.location2Wikidata(values[u'location'])
                prop = self.getLocationProperty(location_Q)
                if prop:
                    protoclaims[prop] = WD.Statement(
                        self.location2Wikidata(values[u'location']))

            return protoclaims

        def varvTest(self, hitItem):
            """
            Fail if has instance claims and none of them are shipyard
            @todo: relax so that e.g. COMPANY_Q is allowed
            return bool
            """
            return self.withClaimTest(hitItem,
                                      self.IS_A_P,
                                      self.SHIPYARD_Q,
                                      u'shipyard')

        # pass settings on to runLayout()
        self.runLayout(datasetRules=varvRules,
                       datasetProtoclaims=varvClaims,
                       datasetSanityTest=varvTest,
                       label=u'name',
                       shuffle=False)

    def runFartyg(self):
        """
        TODO:
            Match value to protoclaims
            Find sanityTest
        """

        fartygRules = {
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
            u'navalVessel.otherType': None,  # can have multiple values
            u'homePort.location': Rule(
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
                target='navalVessel.constructed.constructedBy')
            # navalVessel.measurement
        }

        def fartygClaims(self, values):
            """
            To implement:
                u'navalVessel.signalLetters': possibly P432
                u'delivered.date'
                u'navalVessel.type':
                u'navalVessel.otherType'
                u'navalVessel.isSubRecord'
                u'navalVessel.hasSubRecord'
                u'constructor'

                Probably combine type and otherType then select property
                    depending on wdq lookup
                Fartygsklass:P289 - Sökarklass
                Instans av:P31 - Minläggare
            """
            # P31 fartygstyp -- otherType (om målobjektet är i Svenska marinens klasser för örlogsfartyg)
            # P289 fartygsklass -- otherType (om målobjektet är i Fartygstyper)
            #   Se till att den inte hänger sig på bestämningsord på klass (ex lead ship)
            # ??? -- type (Örlogsskepp ? passar inte riktigt in... tror jag)
            #

            # handle altNames together with names
            values[u'entity.name'] = self.bundleValues(
                [values[u'entity.name'],
                 values[u'altLabel']])
            # convert from ALL-CAPS
            for i in range(0, len(values[u'entity.name'])):
                n = values[u'entity.name'][i][u'@value']
                values[u'entity.name'][i][u'@value'] = n.capitalize()

            # check that we can always safely ignore entity.code
            if values[u'navalVessel.signalLetters'] != values[u'entity.code']:
                pywikibot.output(u'signalLetters!=code for %s: %s <> %s' %
                                 (values[u'identifier'],
                                  values[u'navalVessel.signalLetters'],
                                  values[u'entity.code']))
                exit(1)

            protoclaims = {}

            # handle values
            if values[u'registration.number']:
                # there can be multiple values
                values[u'registration.number'] = self.listify(
                    values[u'registration.number'])
                values[u'registration.type'] = self.listify(
                    values[u'registration.type'])

                # only one type is currently mapped
                claim = []
                for i in range(0, len(values[u'registration.number'])):
                    if values[u'registration.type'][i] == self.IKNO_K:
                        claim.append(
                            WD.Statement(
                                values[u'registration.number'][i]))
                if len(claim) > 0:
                    protoclaims[u'P879'] = claim

            # P504 - homeport
            if values[u'homePort.location']:
                place = self.location2Wikidata(values[u'homePort.location'])
                qual = []
                if values[u'homePort.start']:
                    qual.append(
                        WD.Qualifier(
                            P=self.START_P,
                            itis=self.dbDate(values[u'homePort.start'])))
                if values[u'homePort.end']:
                    qual.append(
                        WD.Qualifier(
                            P=self.END_P,
                            itis=self.dbDate(values[u'homePort.end'])))
                if place:
                    protoclaims[u'P504'] = WD.Statement(place)
                    for q in qual:
                        protoclaims[u'P504'].addQualifier(q)

            # P1071 - Shipyard
            if values[u'built.shipyard'] or values[u'launched.shipyard']:
                print values[u'built.shipyard'], values[u'launched.shipyard']
                shipyard = []
                if values[u'built.shipyard']:
                    shipyard.append(values[u'built.shipyard'])
                if values[u'launched.shipyard']:
                    shipyard.append(values[u'launched.shipyard'])
                shipyard = list(set(shipyard))
                if len(shipyard) > 1:
                    pywikibot.output(u'Found multiple shipyards, not sure how'
                                     u'to proceed: %s' % values[u'identifier'])
                else:
                    protoclaims[u'P1071'] = WD.Statement(
                        self.kulturnav2Wikidata(
                            shipyard[0]))

            # P793 - Events
            #   built: Q474200
            #   launched: Q596643
            #   commissioned: Q14475832
            #   decommissioned: Q7497952
            events = []
            if values[u'built.date']:
                event = WD.Statement(
                    pywikibot.ItemPage(self.repo, 'Q474200')
                    ).addQualifier(
                        WD.Qualifier(
                            P=self.END_P,
                            itis=self.dbDate(values[u'built.date'])))
                if values[u'built.location']:
                    event.addQualifier(
                        WD.Qualifier(
                            P=self.PLACE_P,
                            itis=self.location2Wikidata(
                                values[u'built.location'])))
                # u'built.shipyard'
                events.append(event)
            if values[u'launched.date']:
                event = WD.Statement(
                    pywikibot.ItemPage(self.repo, 'Q596643')
                    ).addQualifier(
                        WD.Qualifier(
                            P=self.TIME_P,
                            itis=self.dbDate(values[u'launched.date'])))
                if values[u'launched.location']:
                    event.addQualifier(
                        WD.Qualifier(
                            P=self.PLACE_P,
                            itis=self.location2Wikidata(
                                values[u'launched.location'])))
                # u'launched.shipyard'
                events.append(event)
            if values[u'delivered.date']:
                pass
            if values[u'decommissioned.date']:
                event = WD.Statement(
                    pywikibot.ItemPage(self.repo, 'Q7497952')
                    ).addQualifier(
                        WD.Qualifier(
                            P=self.TIME_P,
                            itis=self.dbDate(values[u'decommissioned.date'])))
                events.append(event)
            if len(events) > 0:
                protoclaims[u'P793'] = events

            return protoclaims

        def fartygTest(self, hitItem):
            """
            is there any way of testing that it is a ship... of some type?
            Possibly if any of P31 is in wdqList for claim[31:2235308]
            """
            pass

            # return True|False

        # pass settings on to runLayout()
        self.runLayout(datasetRules=fartygRules,
                       datasetProtoclaims=fartygClaims,
                       datasetSanityTest=fartygTest,
                       label=u'entity.name',
                       shuffle=False)

    def runKlasser(self):
        rules = {
            u'entity.name': Rule(  # force to look in top level
                keys='inDataset',
                values=None,
                target='entity.name'),
            u'navalVessel.type': None,  # a type or another class
            u'navalVessel.otherType': None,
            u'altLabel': None
            # navalVessle.measurement
        }

        def claims(self, values):
            # handle altNames together with names
            values[u'entity.name'] = self.bundleValues(
                [values[u'entity.name'],
                 values[u'altLabel']])

            protoclaims = {
                # instance of
                u'P31': WD.Statement(pywikibot.ItemPage(
                    self.repo,
                    u'Q%s' % self.SHIPCLASS_Q)),
                # operator, SwedishNavy
                u'P137': WD.Statement(pywikibot.ItemPage(
                    self.repo,
                    u'Q%s' % self.SWENAVY_Q))
            }

            # bundle type and otherType
            values[u'navalVessel.type'] = self.bundleValues(
                [values[u'navalVessel.type'],
                 values[u'navalVessel.otherType']])

            # P279 - subgroup
            if values[u'navalVessel.type']:
                claims = []
                for t in values[u'navalVessel.type']:
                    item = self.kulturnav2Wikidata(t)
                    if item:
                        claims.append(WD.Statement(item))
                if len(claims) > 0:
                    protoclaims[u'P279'] = claims

            return protoclaims

        def test(self, hitItem):
            """
            Fail if has instance claims and none of them are ship class
            """
            return self.withClaimTest(hitItem,
                                      self.IS_A_P,
                                      self.SHIPCLASS_Q,
                                      u'ship class')

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=test,
                       label=u'entity.name',
                       shuffle=False)

    def runFartygstyper(self):
        rules = {
            u'prefLabel': None,
            u'altLabel': None,
            u'broader': None
        }

        def claims(self, values):
            # handle prefLabel together with altLabel
            values[u'prefLabel'] = self.bundleValues(
                [values[u'prefLabel'],
                 values[u'altLabel']])

            protoclaims = {
                # instance of
                u'P31': WD.Statement(pywikibot.ItemPage(
                    self.repo,
                    u'Q%s' % self.SHIPTYPE_Q))
            }

            # P279 - subgroup self.kulturnav2Wikidata(broader)
            if values[u'broader']:
                protoclaims[u'P279'] = WD.Statement(
                    self.kulturnav2Wikidata(
                        values[u'broader']))
            return protoclaims

        def test(self, hitItem):
            """
            Fail if has instance claims and none of them are ship type
            """
            return self.withClaimTest(hitItem,
                                      self.IS_A_P,
                                      self.SHIPTYPE_Q,
                                      u'ship type')

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=test,
                       label=u'prefLabel',
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
