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
import json
import pywikibot
from pywikibot import pagegenerators
import urllib
import pywikibot.data.wikidataquery as wdquery
import datetime
import config as config
import codecs
import time

EDIT_SUMMARY = u'NationalmuseumBot'
COMMONS_Q = u'565'
INSTITUTION_Q = u'842858'
INVNO_P = u'217'
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
    A bot to enrich and create paintings on Wikidata
    """
    def __init__(self, dictGenerator, paintingIdProperty):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()
        self.commons = pywikibot.Site(u'commons', u'commons')

        # Find allowed collections
        collections = set([INSTITUTION_Q])
        for p, k in PREFIX_MAP.iteritems():
            if k['subcol'] is not None:
                collections.add(k['subcol'].strip('Q'))
        self.collections = list(collections)

        self.paintingIdProperty = paintingIdProperty
        self.paintingIds = self.fillCache(self.paintingIdProperty)

    def fillCache(self, propertyId, queryoverride=u'', cacheMaxAge=0):
        """
        Query Wikidata to fill the cache of paintings we already have an
        object for
        """
        result = {}
        if queryoverride:
            query = queryoverride
        else:
            query = u'CLAIM[195:%s] AND CLAIM[%s]' % \
                    (',195:'.join(self.collections), propertyId)  # collection
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(propertyId), ])

        if data.get('status').get('error') == 'OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(propertyId))
            dupesFound = False
            for prop in props:
                if prop[2] in result.keys() and prop[0] != result[prop[2]]:
                    # Check for Q-numbers claiming to be the same painting
                    # second conditional needed since wdq sometimes returns same result twice (if object has been merged?)
                    pywikibot.output(u'%s is a dupliate of %s' % (prop[0], result[prop[2]]))
                    dupesFound = True
                else:
                    result[prop[2]] = prop[0]
            if dupesFound:
                pywikibot.output('Dupes found. Fix these before moving on')
                exit(1)

            if expectedItems == len(result):
                pywikibot.output('I now have %s items in cache' % expectedItems)

        return result

    def run(self, addNew=True):
        """
        Starts the robot.
        """
        nationalmuseum = pywikibot.ItemPage(self.repo, u'Q%s' % INSTITUTION_Q)
        self.creators = {}

        for painting in self.generator:
            # paintingId = painting['object']['proxies'][0]['about'].replace(u'/proxy/provider/90402/', u'').replace(u'_', u'-')
            ids = painting['object']['proxies'][0]['dcIdentifier']['def']
            paintingId = ids[0].replace('Inv Nr.:', '').strip('( )')
            objId = ids[1]
            uri = u'http://collection.nationalmuseum.se/eMuseumPlus?service=ExternalInterface&module=collection&objectId=%s&viewType=detailView' % objId
            europeanaUrl = u'http://europeana.eu/portal/record%s.html' % (painting['object']['about'],)

            # the museum contains sevaral subcollections. Only deal with mapped ones
            if paintingId.split(' ')[0] not in PREFIX_MAP.keys():
                if paintingId.split(' ')[0] not in BAD_PREFIX:
                    pywikibot.output(u'Skipped due to unknown collection: %s' % paintingId)
                continue

            # for now skip creating any new miniatures
            miniature = False
            for concept in painting['object']['concepts']:
                if concept[u'about'] == MINIATURE_URL:
                    # pywikibot.output(u'Skipping miniature')
                    miniature = True
                    break
            # if miniature:
            #    continue

            paintingItem = None
            # newclaims = []
            if paintingId in self.paintingIds:
                paintingItemTitle = u'Q%s' % (self.paintingIds.get(paintingId),)
                # print paintingItemTitle
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

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

            elif addNew and not miniature:  # skip all new miniatures
                # creating a new one
                data = {'labels': {},
                        'descriptions': {},
                        }

                data['labels'] = makeLabels(painting)
                data['descriptions'], skip = makeDescriptions(painting)
                if skip:
                    continue

                # print data
                # create new empty item and request Q-number
                identification = {}
                summary = u'%s: Creating new item with data from %s' % (EDIT_SUMMARY, europeanaUrl)
                pywikibot.output(summary)
                # monumentItem.editEntity(data, summary=summary)
                try:
                    result = self.repo.editEntity(identification, data, summary=summary)
                except pywikibot.data.api.APIError, e:
                    if e.code == u'modification-failed':
                        # disambiguate and try again
                        for lang in data['descriptions'].keys():
                            data['descriptions'][lang]['value'] += u' (%s)' % paintingId
                        try:
                            result = self.repo.editEntity(identification, data, summary=summary)
                        except pywikibot.data.api.APIError, e:
                            if e.code == u'modification-failed':
                                pywikibot.output(u'modification-failed error: skipping %s' % uri)
                                continue
                            else:
                                pywikibot.output(e)
                                exit(1)
                    else:
                        pywikibot.output(e)
                        exit(1)
                # print result
                paintingItemTitle = result.get(u'entity').get('id')
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

                # add inventory number
                newclaim = pywikibot.Claim(self.repo, u'P%s' % (self.paintingIdProperty,))
                newclaim.setTarget(paintingId)
                pywikibot.output('Adding new id claim to %s' % paintingItem)
                paintingItem.addClaim(newclaim)
                self.addReference(paintingItem, newclaim, uri)

                newqualifier = pywikibot.Claim(self.repo, u'P195')  # Add collection
                newqualifier.setTarget(nationalmuseum)
                pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                newclaim.addQualifier(newqualifier)

                # add collection (or subcollection)
                newclaim = pywikibot.Claim(self.repo, u'P195')
                subcol = PREFIX_MAP[paintingId.split(' ')[0]]['subcol']
                if subcol is not None:
                    subcolItem = pywikibot.ItemPage(self.repo, title=subcol)
                    newclaim.setTarget(subcolItem)
                else:
                    newclaim.setTarget(nationalmuseum)
                pywikibot.output('Adding collection claim to %s' % paintingItem)
                paintingItem.addClaim(newclaim)
                self.addReference(paintingItem, newclaim, europeanaUrl)

                # end of new item creation

            if paintingItem and paintingItem.exists():

                data = paintingItem.get(force=True)
                claims = data.get('claims')
                # print claims

                # located in commented out as subcollection does not match acual placing =(
                """
                # located in
                if u'P276' not in claims:
                    placeItem = pywikibot.ItemPage(self.repo, title=PREFIX_MAP[paintingId.split(' ')[0]]['place'])
                    newclaim = pywikibot.Claim(self.repo, u'P276')
                    newclaim.setTarget(placeItem)
                    pywikibot.output('Adding located in claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)
                    self.addReference(paintingItem, newclaim, europeanaUrl)
                """

                # instance of always painting or icon while working on the painting collection
                if u'P31' not in claims:
                    if paintingId.split(' ')[0] == 'NMI':
                        dcformatItem = pywikibot.ItemPage(self.repo, title='Q%s' % ICON_Q)  # icon
                    else:
                        dcformatItem = pywikibot.ItemPage(self.repo, title='Q%s' % PAINTING_Q)  # painting

                    newclaim = pywikibot.Claim(self.repo, u'P31')
                    newclaim.setTarget(dcformatItem)
                    pywikibot.output('Adding instance claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)
                    self.addReference(paintingItem, newclaim, europeanaUrl)

                # Europeana ID
                if u'P727' not in claims:
                    europeanaID = painting['object']['about'].lstrip('/')

                    newclaim = pywikibot.Claim(self.repo, u'P727')
                    newclaim.setTarget(europeanaID)
                    pywikibot.output('Adding Europeana ID claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)
                    self.addReference(paintingItem, newclaim, europeanaUrl)

                # check for potential images to add
                if u'P18' not in claims:
                    images = self.fileFromExternalLink(uri)
                    if not images:
                        pass
                    elif len(images) == 1:  # for now don't want to choose the appropriate one
                        newclaim = pywikibot.Claim(self.repo, u'P18')
                        newclaim.setTarget(images[0])
                        pywikibot.output('Adding image claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)
                        self.addCommonsReference(paintingItem, newclaim)
                    elif len(images) > 1:
                        pywikibot.output('Found multiple matching images for %s' % paintingItem)
                        for image in images:
                            pywikibot.output(u'\t%s' % image)

                # creator IFF through dbpedia
                if u'P170' not in claims:
                    creatorQ = None
                    try:
                        dcCreatorDB = painting['object']['proxies'][1]['dcCreator']['def']
                        if len(dcCreatorDB) == 1:  # skip anything more complex than one creator
                            dcCreatorDB = dcCreatorDB[0].strip()
                            if dcCreatorDB.startswith('http://dbpedia.org/resource/'):
                                if dcCreatorDB not in self.creators.keys():
                                    self.creators[dcCreatorDB] = dbpedia2wikidata(dcCreatorDB)
                                creatorQ = self.creators[dcCreatorDB]
                    except KeyError:
                        pass

                    if creatorQ is not None:
                        creatorItem = pywikibot.ItemPage(self.repo, title=creatorQ)

                        newclaim = pywikibot.Claim(self.repo, u'P170')
                        newclaim.setTarget(creatorItem)
                        pywikibot.output('Adding creator claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)
                        self.addReference(paintingItem, newclaim, europeanaUrl)

    def addReference(self, paintingItem, newclaim, uri):
        """
        Add a reference with a retrieval url and todays date
        """
        pywikibot.output('Adding new reference claim to %s' % paintingItem)
        refurl = pywikibot.Claim(self.repo, u'P854')  # Add url, isReference=True
        refurl.setTarget(uri)
        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)
        newclaim.addSources([refurl, refdate])

    def addCommonsReference(self, paintingItem, newclaim):
        """
        Add a stating imported from Wikimedia Commons
        """
        commonsItem = pywikibot.ItemPage(self.repo, title=u'Q%s' % COMMONS_Q)

        pywikibot.output('Adding new reference claim to %s' % paintingItem)
        ref = pywikibot.Claim(self.repo, u'P143')  # imported from
        ref.setTarget(commonsItem)
        newclaim.addSource(ref)

    def fileFromExternalLink(self, uri):
        """
        Given an eMuseumPlus uri this checks if there are any file pages
        linking to it
        """
        images = []
        uri = uri.split('://')[1]
        objgen = pagegenerators.LinksearchPageGenerator(uri, namespaces=[6], site=self.commons)
        for page in objgen:
            images.append(pywikibot.FilePage(self.commons, page.title()))
        images = list(set(images))  # I have no clue how the above resulted in duplicates, but it did
        return images

    def mostMissedCreators(self, cacheMaxAge=0):
        """
        Query WDQ for all objects in the collection missing an artist
        then put together a toplist for most desired creator
        """
        expectedItems = []
        query = u'CLAIM[195:%s] AND NOCLAIM[170]' % ',195:'.join(self.collections)  # collection
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset)

        if data.get('status').get('error') == 'OK':
            expectedItems = data.get('items')

        creatorDict = {}
        counter = 0
        for qval in expectedItems:
            qItem = pywikibot.ItemPage(self.repo, title=u'Q%d' % qval)
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
        pywikibot.output(u'Found %d mentions of %d creators' % (counter, len(creatorDict)))
        # output
        f = codecs.open(u'creatorHitlist.csv', 'w', 'utf-8')
        for k, v in creatorDict.iteritems():
            f.write(u'%d|%s\n' % (v, k))
        f.close()


def makeDescriptions(painting):
    """
    Given a painitng object construct descriptions in en/nl/sv
    also sets skip=True if problems are encountered
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
            descriptions['en'] = {'language': u'en', 'value': u'painting by unknown painter'}
            descriptions['nl'] = {'language': u'nl', 'value': u'schilderij van onbekende schilder'}
            descriptions['sv'] = {'language': u'sv', 'value': u'målning av okänd konstnär'}
        elif dcCreatorName.startswith(u'Attributed to'):
            attribName = dcCreatorName[len(u'Attributed to'):].strip()
            descriptions['en'] = {'language': u'en', 'value': u'painting attributed to %s' % (attribName,)}
            descriptions['nl'] = {'language': u'nl', 'value': u'schilderij toegeschreven aan %s' % (attribName,)}
            descriptions['sv'] = {'language': u'sv', 'value': u'målning tillskriven %s' % (attribName,)}
        elif dcCreatorName.startswith(u'Manner of') or \
             dcCreatorName.startswith(u'Copy after') or \
             dcCreatorName.startswith(u'Workshop of') or \
             dcCreatorName.startswith(u'Circle of'):
            skip = True
        else:
            descriptions['en'] = {'language': u'en', 'value': u'painting by %s' % (dcCreatorName,)}
            descriptions['nl'] = {'language': u'nl', 'value': u'schilderij van %s' % (dcCreatorName,)}
            descriptions['sv'] = {'language': u'sv', 'value': u'målning av %s' % (dcCreatorName,)}
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
    Given a dbpedia resource referense (e.g. http://dbpedia.org/resource/Richard_Bergh)
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
            pywikibot.output(u'dbpedia is still complaining about %s, skipping creator' % dbpedia)
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


def getPaintingGenerator(query=u'', rows=MAX_ROWS, start=1):
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
    url = 'http://europeana.eu/api/v2/record/%s.json?wskey=' + config.APIKEY + '&profile=full'

    overviewPage = urllib.urlopen(searchurl)
    overviewData = overviewPage.read()
    overviewJsonData = json.loads(overviewData)
    overviewPage.close()
    fail = False
    totalResults = overviewJsonData.get('totalResults')
    if start > totalResults:
        pywikibot.output(u'Too high start value. There are only %d results' % totalResults)
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
        if (start+MAX_ROWS) > totalResults:
            pywikibot.output(u'No more results! You are done!')
        else:
            pywikibot.output(u'%d...' % (start+MAX_ROWS))
            for g in getPaintingGenerator(rows=(rows-MAX_ROWS), start=(start+MAX_ROWS)):
                yield g


def main(rows=MAX_ROWS, start=1, addNew=True):
    paintingGen = getPaintingGenerator(rows=rows, start=start)

    paintingsBot = PaintingsBot(paintingGen, INVNO_P)  # inv nr.
    paintingsBot.run(addNew=addNew)
    # paintingsBot.mostMissedCreators()


if __name__ == "__main__":
    usage = u'Usage:\tpython nationalmuseumSE.py rows start addNew\n' \
            u'\twhere rows and start are optional positive integers\n' \
            u'\tand addNew is a boolean (defaults to true)'
    import sys
    argv = sys.argv[1:]
    if len(argv) == 0:
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
            main(rows=int(argv[0]), start=int(argv[1]), addNew=True)
        elif argv[2] in ('f', 'F', 'False', 'false'):
            main(rows=int(argv[0]), start=int(argv[1]), addNew=False)
        else:
            print u'Could not interpret the addNew parameter'
            print usage
    else:
        print usage
