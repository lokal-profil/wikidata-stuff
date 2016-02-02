#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Nationalmuseum (Sweden) to Wikidata.
    by Lokal_Profil

Based on http://git.wikimedia.org/summary/labs%2Ftools%2Fmultichill.git
    /bot/wikidata/rijksmuseum_import.py by Multichill

TODO:
    * Add P1476 (title) with all titles - once pywikibot supports monolingual strings
    * Source P217 (inv. nr) whenever unsourced and corresponds to claim
    * Log whenever P217 (inv. nr) does not correspond to claim
    * Allow the image updates to run without having to hammer the Europeana api
"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.wikidataquery as wdquery
import config as config
import helpers
from WikidataStuff import WikidataStuff as WD
import json
import urllib
import datetime
import codecs
import time

EDIT_SUMMARY = u'NationalmuseumBot'
COMMONS_Q = u'565'
INSTITUTION_Q = u'842858'
INVNO_P = u'217'
COLLECTION_P = u'195'
PAINTING_Q = u'3305213'
ICON_Q = u'132137'
MINIATURE_URL = u'http://partage.vocnet.org/part00814'
MAX_ROWS = 100  # max number of rows per request in Europeana API

# mapping prefixes to subcollections see wikidata:User:Lokal Profil/NatMus
PREFIX_MAP = {
    u'NM': {u'subcol': None, u'place': u'Q%s' % INSTITUTION_Q},
    u'NMB': {u'subcol': None, u'place': u'Q%s' % INSTITUTION_Q},
    u'NMI': {u'subcol': u'Q18573057', u'place': u'Q%s' % INSTITUTION_Q},
    u'NMDrh': {u'subcol': u'Q18572999', u'place': u'Q208559'},  # Drottningholm
    u'NMGrh': {u'subcol': u'Q2817221', u'place': u'Q714783'},  # Gripshiolm/Statens porträttsamling
    u'NMGu': {u'subcol': u'Q18573011', u'place': u'Q1556819'},  # Gustavsberg
    u'NMRbg': {u'subcol': u'Q18573027', u'place': u'Q1934091'},  # Rosersberg
    u'NMStrh': {u'subcol': u'Q18573032', u'place': u'Q1416870'},  # Strömsholm
    u'NMVst': {u'subcol': u'Q18573020', u'place': u'Q1757808'},  # Vadstena
    u'NMHpd': {u'subcol': u'Q18575366', u'place': u'Q1140280'},  # Harpsund
    u'NMKok': {u'subcol': u'Q18575408', u'place': u'Q10547348'},  # Kommerskollegiet
    u'NMLä': {u'subcol': u'Q18575368', u'place': u'Q935973'},  # Läckö slott
    u'NMLeu': {u'subcol': u'Q18575377', u'place': u'Q18575382'},  # Leufsta
    u'NMWg': {u'subcol': u'Q18575402', u'place': u'Q969362'},  # Wenngarn
    u'NMUdl': {u'subcol': u'Q18575405', u'place': u'Q176860'},  # Ulriksdal
    u'NMTiP': {u'subcol': u'Q18573041', u'place': u'Q927844'},  # Tessininstitutet
    # Nynäs slott
    u'NMNn': {u'subcol': u'Q18575372', u'place': u'Q2242752'},
    u'NMNnA': {u'subcol': u'Q18575372', u'place': u'Q2242752'},
    # Dahlgrens samling
    u'NMDs': {u'subcol': u'Q18594010', u'place': u'Q%s' % INSTITUTION_Q},
    u'NMDso': {u'subcol': u'Q18594010', u'place': u'Q%s' % INSTITUTION_Q},
    u'NMDse': {u'subcol': u'Q18594010', u'place': u'Q%s' % INSTITUTION_Q},
    u'NMDsä': {u'subcol': u'Q18594010', u'place': u'Q%s' % INSTITUTION_Q}
}
# prefixes which we know to ignore (this way new prefixes are flagged)
BAD_PREFIX = (u'NMG', u'NMEg', u'NMH', u'NMK', u'NMPlåt', u'NMSk', u'NMAnt',
              u'NMSkAv', u'NMTiS', u'NMTiK', u'NMTiD', u'NMTiG')


class PaintingsBot:
    """
    A bot to enrich informartion, and create items, for paintings on Wikidata.
    """
    def __init__(self, dictGenerator, paintingIdProperty):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()
        self.commons = pywikibot.Site(u'commons', u'commons')
        self.wd = WD(self.repo)

        # Find allowed collections
        collections = set([INSTITUTION_Q])
        for p, k in PREFIX_MAP.iteritems():
            if k['subcol'] is not None:
                collections.add(k['subcol'].strip('Q'))
        self.collections = list(collections)

        # prepare WDQ query
        self.paintingIdProperty = paintingIdProperty
        query = u'CLAIM[195:%s] AND CLAIM[%s]' % \
                (',195:'.join(self.collections), self.paintingIdProperty)
        self.paintingIds = helpers.fill_cache(self.paintingIdProperty,
                                              queryoverride=query)

    def run(self, add_new=True, skip_miniatures=True):
        """Start the robot.

        @param add_new: Whether new objects should be created
        @type add_new: bool
        @param skip_miniatures: Whether (new) miniatures should be skipped
        @type skip_miniatures: bool
        """
        self.creators = {}

        for painting in self.generator:
            # paintingId = painting['object']['proxies'][0]['about'].replace(u'/proxy/provider/90402/', u'').replace(u'_', u'-')
            ids = painting['object']['proxies'][0]['dcIdentifier']['def']
            paintingId = ids[0].replace('Inv Nr.:', '').strip('( )')
            objId = ids[1]
            uri = u'http://collection.nationalmuseum.se/eMuseumPlus?service=' \
                  u'ExternalInterface&module=collection&objectId=%s&viewType=' \
                  u'detailView' % objId
            europeanaUrl = u'http://europeana.eu/portal/record%s.html' % \
                           painting['object']['about']

            # the museum contains sevaral subcollections. Only deal with mapped ones
            if paintingId.split(' ')[0] not in PREFIX_MAP.keys():
                if paintingId.split(' ')[0] not in BAD_PREFIX:
                    pywikibot.output(u'Skipped due to unknown collection: %s' % paintingId)
                continue

            paintingItem = None
            # newclaims = []
            if paintingId in self.paintingIds:
                paintingItemTitle = u'Q%s' % self.paintingIds.get(paintingId)
                # print paintingItemTitle
                paintingItem = self.wd.QtoItemPage(paintingItemTitle)

                # check label
                data = paintingItem.get()
                labels = makeLabels(painting)
                newLabels = {}
                for lang, labelObj in labels.iteritems():
                    if lang not in data.get('labels').keys():
                        newLabels[lang] = labelObj['value']
                if newLabels:
                    pywikibot.output('Adding label to %s' % paintingItem.title())
                    paintingItem.editLabels(newLabels)

                # check description
                descriptions, skip = makeDescriptions(painting)
                if not skip:
                    newDescr = {}
                    for lang, descrObj in descriptions.iteritems():
                        if lang not in data.get('descriptions').keys():
                            newDescr[lang] = descrObj['value']
                    if newDescr:
                        pywikibot.output('Adding descriptions to %s' % paintingItem.title())
                        paintingItem.editDescriptions(newDescr)

            elif add_new and not (
                    skip_miniatures and PaintingsBot.is_miniature(painting)):
                # if objection collection is allowed and
                # unless it is aminiature and we are skipping those
                paintingItem = self.create_new_painting(painting, paintingId,
                                                        europeanaUrl, uri)

            # add new claims
            if paintingItem and paintingItem.exists():
                data = paintingItem.get(force=True)
                claims = data.get('claims')

                # @todo: no need to check claims, just make protoclaims or
                # simply add (maybe not images)
                # Instance_of
                if u'P31' not in claims:
                    self.add_instanceof_claim(paintingItem, paintingId,
                                              painting)

                # Europeana_ID
                if u'P727' not in claims:
                    self.add_image_claim(paintingItem, painting)

                # Check for potential images to add, if none is present
                if u'P18' not in claims:
                    self.add_image_claim(paintingItem, uri)

                # creator IFF through dbpedia
                if u'P170' not in claims:
                    self.add_dbpedia_creator(paintingItem, painting)

    def add_locatedin_claim(self, painting_item, painting_id, painting):
        """Add a located_in/P276 claim based on subcollection.

        No longer used as subcollection does not match acual placing.

        @param painting_item: item to which claim is added
        @type painting_item: pywikibot.ItemPage
        @param painting_id: @todo
        @type painting_id: str
        @param painting: information object for the painting
        @type painting: dict
        """
        place = PREFIX_MAP[painting_id.split(' ')[0]]['place']
        place_item = self.wd.QtoItemPage(place)
        self.wd.addNewClaim(
            u'P276',
            WD.Statement(place_item),
            painting_item,
            self.make_europeana_reference(painting))

    def add_dbpedia_creator(self, painting_item, painting):
        """Add a Creator/P170 claim through a dbpedia lookup.

        @param painting_item: item to which claim is added
        @type painting_item: pywikibot.ItemPage
        @param painting: information object for the painting
        @type painting: dict
        """
        creator_Q = None
        try:
            dcCreatorDB = painting['object']['proxies'][1]['dcCreator']['def']
            if len(dcCreatorDB) == 1:
                # skip anything more complex than one creator
                dcCreatorDB = dcCreatorDB[0].strip()
                if dcCreatorDB.startswith('http://dbpedia.org/resource/'):
                    if dcCreatorDB not in self.creators.keys():
                        self.creators[dcCreatorDB] = \
                            dbpedia2wikidata(dcCreatorDB)
                    creator_Q = self.creators[dcCreatorDB]
        except KeyError:
            return

        if creator_Q is not None:
            creator_item = self.wd.QtoItemPage(creator_Q)
            self.wd.addNewClaim(
                u'P170',
                WD.Statement(creator_item),
                painting_item,
                self.make_europeana_reference(painting))

    def add_image_claim(self, painting_item, uri):
        """Add a image/P18 claim if exactly one image is found on Commons.

        Uses the nationalmuseum.se uri to search for matches on Commons. Adds a
        claim only if a unique hit is found.

        @param painting_item: item to which claim is added
        @type painting_item: pywikibot.ItemPage
        @param uri: reference url on nationalmuseum.se
        @type uri: str
        """
        images = self.fileFromExternalLink(uri)
        if len(images) > 1:  # for now don't want to choose the appropriate one
            pywikibot.output('Found multiple matching images for %s' %
                             painting_item)
            for image in images:
                pywikibot.output(u'\t%s' % image)
        elif len(images) == 1:
            self.wd.addNewClaim(
                u'P18',
                WD.Statement(images[0]),
                painting_item,
                self.make_commons_reference())

    def add_europeana_claim(self, painting_item, painting):
        """Add a Europeana ID/P727 claim.

        @param painting_item: item to which claim is added
        @type painting_item: pywikibot.ItemPage
        @param painting: information object for the painting
        @type painting: dict
        """
        europeana_id = painting['object']['about'].lstrip('/')
        self.wd.addNewClaim(
            u'P727',
            WD.Statement(europeana_id),
            painting_item,
            self.make_europeana_reference(painting))

    def add_instanceof_claim(self, painting_item, painting_id, painting):
        """Add an instance_of/P31 claim.

        Instance_of is always painting or icon while working on the paintings
        collection.

        @param painting_item: item to which claim is added
        @type painting_item: pywikibot.ItemPage
        @param painting_id: @todo
        @type painting_id: str
        @param painting: information object for the painting
        @type painting: dict
        """
        dcformat_item = self.wd.QtoItemPage(PAINTING_Q)  # painting
        if painting_id.split(' ')[0] == 'NMI':
            dcformat_item = self.wd.QtoItemPage(ICON_Q)  # icon

        self.wd.addNewClaim(
            u'P31',
            WD.Statement(dcformat_item),
            painting_item,
            self.make_europeana_reference(painting))

    @staticmethod
    def is_miniature(painting):
        """Determine if the painting is a miniature.

        @param painting: information object for the painting
        @type painting: dict
        @rtype bool
        """
        for concept in painting['object']['concepts']:
            if concept[u'about'] == MINIATURE_URL:
                # pywikibot.output(u'Skipping miniature')
                return True
        return False

    def create_new_painting(self, painting, painting_id, europeana_url, uri):
        """@todo: needs more cleanup

        @param painting: information object for the painting
        @type painting: dict
        @param painting_id: @odo
        @type painting_id: @todo
        @param europeana_url: reference url for europeana
        @type europeana_url: str
        @param uri: reference uri at nationalmuseum.se
        @type uri: str
        @return: the created painting item
        @rtype: pywikibot.ItemPage
        """
        nationalmuseum_item = self.wd.QtoItemPage(self.INSTITUTION_Q)

        data = {
            'labels': {},
            'descriptions': {}
            }

        data['labels'] = makeLabels(painting)
        data['descriptions'], skip = makeDescriptions(painting)
        if skip:
            return

        # print data
        # create new empty item and request Q-number
        summary = u'%s: Creating new item with data from %s' % (EDIT_SUMMARY,
                                                                europeana_url)
        painting_item = None
        try:
            painting_item = self.make_new_item(data, summary)
        except pywikibot.data.api.APIError, e:
            if e.code == u'modification-failed':
                # disambiguate and try again
                for lang, content in data['descriptions'].iteritems():
                    disambiguation = content['value'] + u' (%s)' % painting_id
                    data['descriptions'][lang]['value'] = disambiguation
                try:
                    painting_item = self.make_new_item(data, summary)
                except pywikibot.data.api.APIError, e:
                    if e.code == u'modification-failed':
                        pywikibot.output(u'modification-failed error: '
                                         u'skipping %s' % uri)
                        return
                    else:
                        raise pywikibot.Error(u'Error during item creation: '
                                              u'%s' % e)
            else:
                raise pywikibot.Error(u'Error during item creation: %s' % e)

        # @todo: break out as two separate methods
        # add inventory number with collection
        self.wd.addNewClaim(
            self.paintingIdProperty,
            WD.Statement(painting_id).addQualifier(
                WD.Qualifier(
                    P=COLLECTION_P,
                    itis=nationalmuseum_item),
                force=True),
            painting_item,
            self.make_reference(uri))

        # add collection (or subcollection)
        subcol = PREFIX_MAP[painting_id.split(' ')[0]]['subcol']
        collection_item = nationalmuseum_item
        if subcol is not None:
            collection_item = self.wd.QtoItemPage(subcol)

        self.wd.addNewClaim(
            COLLECTION_P,
            WD.Statement(collection_item),
            painting_item,
            self.make_europeana_reference(painting))

        return painting_item

    def make_new_item(self, data, summary):
        """Makes a new ItemPage given some data and an edit summary.

        @todo: Inverstigate if anything already exists in pywikibot, if not
               move this to WD
        @todo: make proper docstring

        @rtype: pywikibot.ItemPage
        """
        identification = {}  # @todo: what does this do?
        # monumentItem.editEntity(data, summary=summary)
        result = self.repo.editEntity(identification, data, summary=summary)
        pywikibot.output(summary)  # afterwards in case an error is raised

        # return the new item
        return self.wd.QtoItemPage(result.get(u'entity').get('id'))

    def make_europeana_reference(self, painting):
        """Make a Reference object with a Europeana retrieval url and todays date.

        @param uri: retrieval uri/url
        @type uri: str
        @rtype: WD.Reference
        """
        europeana_url = u'http://europeana.eu/portal/record%s.html' % \
                        painting['object']['about']
        return self.make_reference(europeana_url)

    def make_reference(self, uri):
        """Make a Reference object with a retrieval url and todays date.

        @param uri: retrieval uri/url
        @type uri: str
        @rtype: WD.Reference
        """
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year,
                                month=today.month,
                                day=today.day)
        ref = WD.Reference(
            source_test=self.wd.make_simple_claim(u'P854', uri),
            source_notest=self.wd.make_simple_claim(u'P813', date))
        return ref

    def make_commons_reference(self):
        """Make a Reference object saying imported from Wikimedia Commons."""
        commons_item = self.wd.QtoItemPage(COMMONS_Q)
        ref = WD.Reference(
            source_test=self.wd.make_simple_claim(
                u'P143', commons_item))  # imported from
        return ref

    def fileFromExternalLink(self, uri):
        """
        Given an eMuseumPlus uri this checks if there are any file pages
        linking to it
        """
        images = []
        uri = uri.split('://')[1]
        objgen = pagegenerators.LinksearchPageGenerator(uri, namespaces=[6],
                                                        site=self.commons)
        for page in objgen:
            images.append(pywikibot.FilePage(self.commons, page.title()))
        # I have no clue how the above results in duplicates, but it does so...
        images = list(set(images))
        return images

    def mostMissedCreators(self, cacheMaxAge=0):
        """
        Query WDQ for all objects in the collection missing an artist
        then put together a toplist for most desired creator
        """
        expectedItems = []
        query = u'CLAIM[195:%s] AND NOCLAIM[170]' % \
                ',195:'.join(self.collections)  # collection
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset)

        if data.get('status').get('error') == 'OK':
            expectedItems = data.get('items')

        creatorDict = {}
        counter = 0
        for qval in expectedItems:
            qItem = self.wd.QtoItemPage(qval)
            data = qItem.get()
            claims = data.get('claims')
            if u'P170' in claims:
                continue
            descr = data.get('descriptions').get('en')
            if descr and descr.startswith(u'painting by '):
                creator = descr[len(u'painting by '):]
                if '(' in creator:  # to get rid of disambiguation addition
                    creator = creator[:creator.find('(')].strip()
                if creator in creatorDict.keys():
                    creatorDict[creator] += 1
                else:
                    creatorDict[creator] = 1
                counter += 1
        pywikibot.output(u'Found %d mentions of %d creators' %
                         (counter, len(creatorDict)))
        # output
        f = codecs.open(u'creatorHitlist.csv', 'w', 'utf-8')
        for k, v in creatorDict.iteritems():
            f.write(u'%d|%s\n' % (v, k))
        f.close()


def makeDescriptions(painting):
    """
    Given a painitng object construct descriptions in en/nl/sv
    also sets skip=True if problems are encountered
    @todo: handle "skip" better, e.g. returning None or raising an error
    """
    skip = False
    dcCreatorName = None
    try:
        dcCreatorName = painting['object']['proxies'][0]['dcCreator']['sv'][0].strip()
        # print dcCreatorName
    except KeyError:
        # pywikibot.output(u'skipped due to weird creator settings in %s' % europeanaUrl)
        # skip = True
        pass

    descriptions = {}
    if dcCreatorName:
        if dcCreatorName == u'Okänd':
            descriptions['en'] = {
                'language': u'en',
                'value': u'painting by unknown painter'}
            descriptions['nl'] = {
                'language': u'nl',
                'value': u'schilderij van onbekende schilder'}
            descriptions['sv'] = {
                'language': u'sv',
                'value': u'målning av okänd konstnär'}
        elif dcCreatorName.startswith(u'Attributed to'):
            attribName = dcCreatorName[len(u'Attributed to'):].strip()
            descriptions['en'] = {
                'language': u'en',
                'value': u'painting attributed to %s' % attribName}
            descriptions['nl'] = {
                'language': u'nl',
                'value': u'schilderij toegeschreven aan %s' % attribName}
            descriptions['sv'] = {
                'language': u'sv',
                'value': u'målning tillskriven %s' % attribName}
        elif dcCreatorName.startswith(u'Manner of') or \
                dcCreatorName.startswith(u'Copy after') or \
                dcCreatorName.startswith(u'Workshop of') or \
                dcCreatorName.startswith(u'Circle of'):
            skip = True
        else:
            descriptions['en'] = {
                'language': u'en',
                'value': u'painting by %s' % dcCreatorName}
            descriptions['nl'] = {
                'language': u'nl',
                'value': u'schilderij van %s' % dcCreatorName}
            descriptions['sv'] = {
                'language': u'sv',
                'value': u'målning av %s' % dcCreatorName}
    else:
        descriptions['en'] = {'language': u'en', 'value': u'painting'}
        descriptions['nl'] = {'language': u'nl', 'value': u'schilderij'}
        descriptions['sv'] = {'language': u'sv', 'value': u'målning'}
    return descriptions, skip


def makeLabels(painting):
    """
    Given a painting object extract all labels
    """
    labels = {}
    for dcTitleLang, dcTitle in painting['object']['proxies'][0]['dcTitle'].iteritems():
        labels[dcTitleLang] = {'language': dcTitleLang, 'value': dcTitle[0]}
    return labels


def dbpedia2wikidata(dbpedia):
    """
    Given a dbpedia resource reference
    (e.g. http://dbpedia.org/resource/Richard_Bergh)
    this returns the sameAs wikidata value, if any
    """
    url = u'http://dbpedia.org/sparql?default-graph-uri=http%3A%2F%2Fdbpedia.org&query=DESCRIBE+%3C' \
        + dbpedia \
        + u'%3E&output=application%2Fld%2Bjson'
    # urlencode twice? per http://dbpedia.org/resource/%C3%89douard_Vuillard
    try:
        dbPage = urllib.urlopen(url)
    except IOError:
        pywikibot.output(u'dbpedia is complaining so sleeping for 10s')
        time.sleep(10)
        try:
            dbPage = urllib.urlopen(url)
        except IOError:
            pywikibot.output(u'dbpedia is still complaining about %s, '
                             u'skipping creator' % dbpedia)
            return None
    try:
        dbData = dbPage.read()
        jsonData = json.loads(dbData)
        dbPage.close()
    except ValueError, e:
        pywikibot.output(u'dbpedia-skip: %s, %s' % (dbpedia, e))
        return None

    if jsonData.get('@graph'):
        for g in jsonData.get('@graph'):
            if g.get('http://www.w3.org/2002/07/owl#sameAs'):
                for same in g.get('http://www.w3.org/2002/07/owl#sameAs'):
                    if isinstance(same, (str, unicode)):
                        if same.startswith('http://wikidata.org/entity/'):
                            return same[len('http://wikidata.org/entity/'):]
                return None
    return None


def getPaintingGenerator(rows=MAX_ROWS, start=1):
    """
    Get objects from Europeanas API.
    API call specifies:
    DATA_PROVIDER=Nationalmuseum (Sweden)
    what=paintings
    """
    searchurl = 'http://www.europeana.eu/api/v2/search.json?wskey=' \
                + config.APIKEY \
                + '&profile=minimal&rows=' \
                + str(min(MAX_ROWS, rows)) \
                + '&start=' \
                + str(start) \
                + '&query=*%3A*&qf=DATA_PROVIDER%3A%22Nationalmuseum%2C+Sweden%22&qf=what%3A+paintings'
    url = 'http://europeana.eu/api/v2/record/%s.json?wskey=' \
          + config.APIKEY \
          + '&profile=full'

    overviewPage = urllib.urlopen(searchurl)
    overviewData = overviewPage.read()
    overviewJsonData = json.loads(overviewData)
    overviewPage.close()
    fail = False
    totalResults = overviewJsonData.get('totalResults')
    if start > totalResults:
        pywikibot.output(u'Too high start value. There are only %d results' %
                         totalResults)
        exit(1)

    for item in overviewJsonData.get('items'):
        apiPage = urllib.urlopen(url % item.get('id'))
        apiData = apiPage.read()
        try:
            jsonData = json.loads(apiData)
        except ValueError, e:
            print e
            print url % item.get('id')
            exit(1)

        apiPage.close()
        if jsonData.get(u'success'):
            yield jsonData
        else:
            print jsonData
            fail = True

    # call again to get around the MAX_ROWS limit of the api
    if not fail and rows > MAX_ROWS:
        if (start + MAX_ROWS) > totalResults:
            pywikibot.output(u'No more results! You are done!')
        else:
            pywikibot.output(u'%d...' % (start + MAX_ROWS))
            for g in getPaintingGenerator(rows=(rows - MAX_ROWS),
                                          start=(start + MAX_ROWS)):
                yield g


def main(rows=MAX_ROWS, start=1, add_new=True):
    paintingGen = getPaintingGenerator(rows=rows, start=start)

    paintingsBot = PaintingsBot(paintingGen, INVNO_P)  # inv nr.
    paintingsBot.run(add_new=add_new)
    # paintingsBot.mostMissedCreators()


if __name__ == "__main__":
    usage = u'Usage:\tpython nationalmuseumSE.py rows start add_new\n' \
            u'\twhere rows and start are optional positive integers\n' \
            u'\tand add_new is a boolean (defaults to true)'
    import sys
    argv = sys.argv[1:]
    if not argv:
        main()
    elif len(argv) == 2:
        if int(argv[0]) < 1 or int(argv[1]) < 1:
            print usage
        else:
            main(rows=int(argv[0]), start=int(argv[1]))
    elif len(argv) == 3:
        if int(argv[0]) < 1 or int(argv[1]) < 1:
            print usage
            exit(1)
        if argv[2] in ('t', 'T', 'True', 'true'):
            main(rows=int(argv[0]), start=int(argv[1]), add_new=True)
        elif argv[2] in ('f', 'F', 'False', 'false'):
            main(rows=int(argv[0]), start=int(argv[1]), add_new=False)
        else:
            print u'Could not interpret the add_new parameter'
            print usage
    else:
        print usage
