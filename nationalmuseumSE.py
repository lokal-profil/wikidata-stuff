#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Nationalmuseum (Sweden) to Wikidata.
    by Lokal_Profil

Based on http://git.wikimedia.org/blob/labs/tools/multichill/bot/wikidata/rijksmuseum_import.py
    by Multichill

"""
import json
import pywikibot
#from pywikibot import pagegenerators
import urllib
#import re
import pywikibot.data.wikidataquery as wdquery
import datetime
import config as config

EDIT_SUMMARY = u'NationalmuseumBot'
INSTITUTION_Q = u'842858'
PAINTING_Q = u'3305213'


class PaintingsBot:
    """
    A bot to enrich and create monuments on Wikidata
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
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
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

    def run(self):
        """
        Starts the robot.
        """
        nationalmuseum = pywikibot.ItemPage(self.repo, u'Q%s' % INSTITUTION_Q)
        for painting in self.generator:
            # Buh, for this one I know for sure it's in there

            # paintingId = painting['object']['proxies'][0]['about'].replace(u'/proxy/provider/90402/', u'').replace(u'_', u'-')
            ids = painting['object']['proxies'][0]['dcIdentifier']['def']
            paintingId = ids[0].replace('Inv. Nr.:', '').strip('( )')
            objId = ids[1]
            uri = u'http://emp-web-22.zetcom.ch/eMuseumPlus?service=ExternalInterface&module=collection&objectId=%s&viewType=detailView' % objId
            europeanaUrl = u'http://europeana.eu/portal/record/%s.html' % (painting['object']['about'],)

            print paintingId
            print uri
            print europeanaUrl

            try:
                dcCreatorName = painting['object']['proxies'][0]['dcCreator']['sv'][0].strip()
                print dcCreatorName
            except KeyError:
                print 'skipped'
                continue

            paintingItem = None
            # newclaims = []
            if paintingId in self.paintingIds:
                paintingItemTitle = u'Q%s' % (self.paintingIds.get(paintingId),)
                print paintingItemTitle
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

            else:
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
                        pywikibot.output(u'modification-failed error: skipping')
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

                # add collection
                newclaim = pywikibot.Claim(self.repo, u'P195')
                newclaim.setTarget(nationalmuseum)
                pywikibot.output('Adding collection claim to %s' % paintingItem)
                paintingItem.addClaim(newclaim)
                self.addReference(paintingItem, newclaim, europeanaUrl)

                # end of new item creation

            if paintingItem and paintingItem.exists():

                data = paintingItem.get()
                claims = data.get('claims')
                # print claims

                # located in
                if u'P276' not in claims:
                    newclaim = pywikibot.Claim(self.repo, u'P276')
                    newclaim.setTarget(nationalmuseum)
                    pywikibot.output('Adding located in claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)
                    self.addReference(paintingItem, newclaim, europeanaUrl)

                # instance of always painting while working on the painting collection
                if u'P31' not in claims:
                    dcformatItem = pywikibot.ItemPage(self.repo, title='Q%s' % PAINTING_Q)  # painting

                    newclaim = pywikibot.Claim(self.repo, u'P31')
                    newclaim.setTarget(dcformatItem)
                    pywikibot.output('Adding instance claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)
                    self.addReference(paintingItem, newclaim, europeanaUrl)

                """
                # creator
                # beweare of dcCreatorName == u'Okänd':
                if u'P170' not in claims and dcCreatorName:
                    creategen = pagegenerators.PreloadingItemGenerator(
                                    pagegenerators.WikidataItemGenerator(
                                        pagegenerators.SearchPageGenerator(
                                            dcCreatorName, step=None, total=10, namespaces=[0], site=self.repo)))

                    newcreator = None

                    for creatoritem in creategen:
                        print creatoritem.title()
                        if creatoritem.get().get('labels').get('en') == dcCreatorName or creatoritem.get().get('labels').get('nl') == dcCreatorName:
                            print creatoritem.get().get('labels').get('en')
                            print creatoritem.get().get('labels').get('nl')
                            # Check occupation and country of citizinship
                            if u'P106' in creatoritem.get().get('claims') and u'P27' in creatoritem.get().get('claims'):
                                newcreator = creatoritem
                                continue
                        elif (creatoritem.get().get('aliases').get('en') and dcCreatorName in creatoritem.get().get('aliases').get('en')) or (creatoritem.get().get('aliases').get('nl') and dcCreatorName in creatoritem.get().get('aliases').get('nl')):
                            if u'P106' in creatoritem.get().get('claims') and u'P27' in creatoritem.get().get('claims'):
                                newcreator = creatoritem
                                continue

                    if newcreator:
                        pywikibot.output(newcreator.title())

                        newclaim = pywikibot.Claim(self.repo, u'P170')
                        newclaim.setTarget(newcreator)
                        pywikibot.output('Adding creator claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)
                        self.addReference(paintingItem, newclaim, europeanaUrl)

                        #creatoritem = pywikibot.ItemPage(self.repo, creatorpage)
                        print creatoritem.title()
                        print creatoritem.get()

                    else:
                        pywikibot.output('No item found for %s' % (dcCreatorName, ))
                """
                """
                # material used
                if u'P186' not in claims:
                    dcFormats = { u'http://vocab.getty.edu/aat/300014078' : u'Q4259259', # Canvas
                                  u'http://vocab.getty.edu/aat/300015050' : u'Q296955', # Oil paint
                                  }
                    if painting['object']['proxies'][0].get('dcFormat') and painting['object']['proxies'][0]['dcFormat'].get('def'):
                        for dcFormat in painting['object']['proxies'][0]['dcFormat']['def']:
                            if dcFormat in dcFormats:
                                dcformatItem = pywikibot.ItemPage(self.repo, title=dcFormats[dcFormat])

                                newclaim = pywikibot.Claim(self.repo, u'P186')
                                newclaim.setTarget(dcformatItem)
                                pywikibot.output('Adding material used claim to %s' % paintingItem)
                                paintingItem.addClaim(newclaim)

                                newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                                newreference.setTarget(europeanaUrl)
                                pywikibot.output('Adding new reference claim to %s' % paintingItem)
                                newclaim.addSource(newreference)

                # Handle
                if u'P1184' not in claims:
                    handleUrl = painting['object']['proxies'][0]['dcIdentifier']['def'][0]
                    handle = handleUrl.replace(u'http://hdl.handle.net/', u'')

                    newclaim = pywikibot.Claim(self.repo, u'P1184')
                    newclaim.setTarget(handle)
                    pywikibot.output('Adding handle claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)

                    newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                    newreference.setTarget(europeanaUrl)
                    pywikibot.output('Adding new reference claim to %s' % paintingItem)
                    newclaim.addSource(newreference)
                """
                # Europeana ID
                if u'P727' not in claims:
                    europeanaID = painting['object']['about'].lstrip('/')

                    newclaim = pywikibot.Claim(self.repo, u'P727')
                    newclaim.setTarget(europeanaID)
                    pywikibot.output('Adding Europeana ID claim to %s' % paintingItem)
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


def getPaintingGenerator(query=u'', rows=100, start=1):
    '''
    Bla %02d
    '''
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
            u'where rows and start are optional positive integers'
    import sys
    argv = sys.argv[1:]
    if len(argv) == 0:
        main()
    elif len(argv) == 2:
        main(rows=argv[0], start=argv[1])
    else:
        print usage
