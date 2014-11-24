#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Nationalmuseum (Sweden) to Wikidata.
    by Lokal_Profil

Based on http://git.wikimedia.org/summary/labs%2Ftools%2Fmultichill.git
    /bot/wikidata/rijksmuseum_import.py by Multichill

"""
import json
import pywikibot
import urllib
import pywikibot.data.wikidataquery as wdquery
import datetime
import config as config

EDIT_SUMMARY = u'NationalmuseumBot'
INSTITUTION_Q = u'842858'
PAINTING_Q = u'3305213'
ICON_Q = u'132137'
MINIATURE_URL = u'http://partage.vocnet.org/part00814'


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

        self.paintingIdProperty = paintingIdProperty
        self.paintingIds = self.fillCache(self.paintingIdProperty)

    def fillCache(self, propertyId, queryoverride=u'', cacheMaxAge=0):
        """
        Query Wikidata to fill the cache of monuments we already have an object for
        """
        result = {}
        if queryoverride:
            query = queryoverride
        else:
            query = u'CLAIM[195:%s] AND CLAIM[%s]' % (INSTITUTION_Q, propertyId)  # collection
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(propertyId), ])

        if data.get('status').get('error') == 'OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(propertyId))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[prop[2]] = prop[0]

            if expectedItems == len(result):
                pywikibot.output('I now have %s items in cache' % expectedItems)

        return result

    def run(self, addNew=True):
        """
        Starts the robot.
        """
        nationalmuseum = pywikibot.ItemPage(self.repo, u'Q%s' % INSTITUTION_Q)
        self.creators = {}

        # mapping prefixes to subcollections
        prefixMap = {u'NM': {u'subcol': None, u'place': u'Q%s' % INSTITUTION_Q},
                     u'NMB': {u'subcol': None, u'place': u'Q%s' % INSTITUTION_Q},
                     #u'NMI': {u'subcol': u'Q18573057', u'place': u'Q%s' % INSTITUTION_Q},
                     u'NMDrh': {u'subcol': u'Q18572999', u'place': u'Q208559'},
                     u'NMGrh': {u'subcol': u'Q2817221', u'place': u'Q714783'},
                     u'NMGu': {u'subcol': u'Q18573011', u'place': u'Q1556819'},
                     u'NMRbg': {u'subcol': u'Q18573027', u'place': u'Q1934091'},
                     u'NMStrh': {u'subcol': u'Q18573032', u'place': u'Q1416870'},
                     u'NMVst': {u'subcol': u'Q18573020', u'place': u'Q1757808'},
                     u'NMTiP': {u'subcol': u'Q18573041', u'place': u'Q927844'}
                     }

        for painting in self.generator:
            # Buh, for this one I know for sure it's in there

            # paintingId = painting['object']['proxies'][0]['about'].replace(u'/proxy/provider/90402/', u'').replace(u'_', u'-')
            ids = painting['object']['proxies'][0]['dcIdentifier']['def']
            paintingId = ids[0].replace('Inv. Nr.:', '').strip('( )')
            objId = ids[1]
            uri = u'http://emp-web-22.zetcom.ch/eMuseumPlus?service=ExternalInterface&module=collection&objectId=%s&viewType=detailView' % objId
            europeanaUrl = u'http://europeana.eu/portal/record/%s.html' % (painting['object']['about'],)

            # the museum contains sevaral subcollections. Only deal with mapped ones
            if paintingId.split(' ')[0] not in prefixMap.keys():
                pywikibot.output(u'Skipped due to collection: %s' % paintingId)
                continue

            # for now skip all of the miniatures
            miniature = False
            for concept in painting['object']['concepts']:
                if concept[u'about'] == MINIATURE_URL:
                    pywikibot.output(u'Skipping miniature')
                    miniature = True
                    break
            if miniature:
                continue

            try:
                dcCreatorName = painting['object']['proxies'][0]['dcCreator']['sv'][0].strip()
                # print dcCreatorName
            except KeyError:
                print 'skipped'
                continue

            paintingItem = None
            # newclaims = []
            if paintingId in self.paintingIds:
                paintingItemTitle = u'Q%s' % (self.paintingIds.get(paintingId),)
                # print paintingItemTitle
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

            elif addNew:
                # creating a new one
                data = {'labels': {},
                        'descriptions': {},
                        }

                for dcTitleLang, dcTitle in painting['object']['proxies'][0]['dcTitle'].iteritems():
                    data['labels'][dcTitleLang] = {'language': dcTitleLang,
                                                   'value': dcTitle[0]}

                if dcCreatorName:
                    if dcCreatorName == u'Okänd':
                        data['descriptions']['en'] = {'language': u'en', 'value': u'painting by unknown painter'}
                        data['descriptions']['nl'] = {'language': u'nl', 'value': u'schilderij van onbekende schilder'}
                        data['descriptions']['sv'] = {'language': u'sv', 'value': u'målning av okänd konstnär'}
                    elif dcCreatorName.startswith(u'Attributed to'):
                        attribName = dcCreatorName[len(u'Attributed to'):].strip()
                        data['descriptions']['en'] = {'language': u'en', 'value': u'painting attributed to %s' % (attribName,)}
                        data['descriptions']['nl'] = {'language': u'nl', 'value': u'schilderij toegeschreven aan %s' % (attribName,)}
                        data['descriptions']['sv'] = {'language': u'sv', 'value': u'målning tillskriven %s' % (attribName,)}
                    elif dcCreatorName.startswith(u'Manner of') or dcCreatorName.startswith(u'Copy after'):
                        continue
                    else:
                        data['descriptions']['en'] = {'language': u'en', 'value': u'painting by %s' % (dcCreatorName,)}
                        data['descriptions']['nl'] = {'language': u'nl', 'value': u'schilderij van %s' % (dcCreatorName,)}
                        data['descriptions']['sv'] = {'language': u'sv', 'value': u'målning av %s' % (dcCreatorName,)}

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
                        pywikibot.output(u'modification-failed error: skipping %s' % uri)
                        continue
                    else:
                        pywikibot.output(e)
                        exit(1)
                # print result
                paintingItemTitle = result.get(u'entity').get('id')
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

                # add identifier
                newclaim = pywikibot.Claim(self.repo, u'P%s' % (self.paintingIdProperty,))
                newclaim.setTarget(paintingId)
                pywikibot.output('Adding new id claim to %s' % paintingItem)
                paintingItem.addClaim(newclaim)
                self.addReference(paintingItem, newclaim, uri)

                newqualifier = pywikibot.Claim(self.repo, u'P195')  # Add collection, isQualifier=True
                newqualifier.setTarget(nationalmuseum)
                pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                newclaim.addQualifier(newqualifier)

                # add collection (and subcollection)
                newclaim = pywikibot.Claim(self.repo, u'P195')
                newclaim.setTarget(nationalmuseum)
                pywikibot.output('Adding collection claim to %s' % paintingItem)
                paintingItem.addClaim(newclaim)
                self.addReference(paintingItem, newclaim, europeanaUrl)

                subcol = prefixMap[paintingId.split(' ')[0]]['subcol']
                if subcol is not None:
                    subcolItem = pywikibot.ItemPage(self.repo, title=subcol)

                    newqualifier = pywikibot.Claim(self.repo, u'P518')  # Add appliesToPart
                    newqualifier.setTarget(subcolItem)
                    pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                    newclaim.addQualifier(newqualifier)

                # end of new item creation

            if paintingItem and paintingItem.exists():

                data = paintingItem.get()
                claims = data.get('claims')
                # print claims

                # located in commented out as subcollection does not match acual placing =(
                """
                # located in
                if u'P276' not in claims:
                    placeItem = pywikibot.ItemPage(self.repo, title=prefixMap[paintingId.split(' ')[0]]['place'])
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


def dbpedia2wikidata(dbpedia):
    """
    Given a dbpedia resource referense (e.g. http://dbpedia.org/resource/Richard_Bergh)
    this returns the sameAs wikidata value, if any
    """
    url = u'http://dbpedia.org/sparql?default-graph-uri=http%3A%2F%2Fdbpedia.org&query=DESCRIBE+%3C' \
        + dbpedia \
        + u'%3E&output=application%2Fld%2Bjson'

    dbPage = urllib.urlopen(url)
    dbData = dbPage.read()
    jsonData = json.loads(dbData)
    dbPage.close()

    if jsonData.get('@graph'):
        for g in jsonData.get('@graph'):
            if g.get('http://www.w3.org/2002/07/owl#sameAs'):
                for same in g.get('http://www.w3.org/2002/07/owl#sameAs'):
                    if same.startswith('http://wikidata.org/entity/'):
                        return same[len('http://wikidata.org/entity/'):]
                return None
    return None


def getPaintingGenerator(query=u'', rows=100, start=1):
    """
    Bla %02d
    """
    searchurl = 'http://www.europeana.eu/api/v2/search.json?wskey=' \
               + config.APIKEY \
               + '&profile=minimal&rows=' \
               + str(rows) \
               + '&start=' \
               + str(start) \
               + '&query=*%3A*&qf=DATA_PROVIDER%3A%22Nationalmuseum%2C+Sweden%22&qf=what%3A+paintings'
    url = 'http://europeana.eu/api/v2/record/%s.json?wskey=' + config.APIKEY + '&profile=full'

    overviewPage = urllib.urlopen(searchurl)
    overviewData = overviewPage.read()
    overviewJsonData = json.loads(overviewData)
    overviewPage.close()

    for item in overviewJsonData.get('items'):
        apiPage = urllib.urlopen(url % item.get('id'))
        apiData = apiPage.read()
        jsonData = json.loads(apiData)

        apiPage.close()
        if jsonData.get(u'success'):
            yield jsonData
        else:
            print jsonData


def main(rows=100, start=1):
    paintingGen = getPaintingGenerator(rows=rows, start=start)

    paintingsBot = PaintingsBot(paintingGen, 217)  # inv nr.
    paintingsBot.run()


if __name__ == "__main__":
    usage = u'Usage:\tpython nationalmuseumSE.py rows start\n' \
            u'\twhere rows and start are optional positive integers'
    import sys
    argv = sys.argv[1:]
    if len(argv) == 0:
        main()
    elif len(argv) == 2:
        main(rows=argv[0], start=argv[1])
    else:
        print usage
