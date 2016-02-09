#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Nationalmuseum (Sweden) to Wikidata.

Author: Lokal_Profil
License: MIT

Based on http://git.wikimedia.org/summary/labs%2Ftools%2Fmultichill.git
    /bot/wikidata/rijksmuseum_import.py by Multichill

@todo: Allow image updates to run without having to hammer the Europeana api

usage:
    python NatMus/nationalmuseumSE.py [OPTIONS]

Options (may be omitted):
-rows:INT         Number of entries to process (default: All)

-add_new:bool     Whether new objects should be created (default: True)

Can also handle any pywikibot options. Most importantly:
-simulate         Don't write to database
"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.wikidataquery as wdquery
import config as config
import helpers
from WikidataStuff import WikidataStuff as WD
import json
import datetime
import codecs
import urllib2

usage = u"""
Usage:            python NatMus/nationalmuseumSE.py [OPTIONS]
                  with options:

-rows:INT         Number of entries to process (default: All)

-add_new:bool     Whether new objects should be created (default: True)
"""

EDIT_SUMMARY = u'NationalmuseumBot'
COMMONS_Q = u'565'
INSTITUTION_Q = u'842858'
INVNO_P = u'217'
PAINTING_Q = u'3305213'
ICON_Q = u'132137'
MINIATURE_URL = u'http://partage.vocnet.org/part00814'
MAX_ROWS = 100  # max number of rows per request in Europeana API


class PaintingsBot:
    """Bot to enrich, and create, for items about paintings on Wikidata."""

    def __init__(self, dict_generator, painting_id_prop, add_new=False,
                 skip_miniatures=True):
        """Initiate the bot, loading files and querying WDQ.

        @param dict_generator: The generator for the Europeana painting objects
        @type dict_generator: generator (that yields Dict objects).
        @param painting_id_prop: the P-id of the painting-id property
        @type painting_id_prop: str
        @param add_new: Whether new objects should be created
        @type add_new: bool
        @param skip_miniatures: Whether (new) miniatures should be skipped
        @type skip_miniatures: bool
        """
        self.generator = dict_generator
        self.repo = pywikibot.Site().data_repository()
        self.commons = pywikibot.Site(u'commons', u'commons')
        self.wd = WD(self.repo)
        self.add_new = add_new
        self.skip_miniatures = skip_miniatures

        # Load prefixes and find allowed collections
        collections = set([INSTITUTION_Q])
        self.mappings = helpers.load_json_file('mappings.json',
                                               force_path=__file__)
        self.prefix_map = self.mappings['prefix_map']
        self.bad_prefix = self.mappings['bad_prefix']
        for p, k in self.prefix_map.iteritems():
            if k['subcol'] is not None:
                collections.add(k['subcol'].strip('Q'))
        self.collections = list(collections)

        # prepare WDQ query
        query = u'CLAIM[195:%s] AND CLAIM[%s]' % \
                (',195:'.join(self.collections), painting_id_prop)
        self.painting_ids = helpers.fill_cache(painting_id_prop,
                                               queryoverride=query)
        self.painting_id_prop = 'P%s' % painting_id_prop

    def run(self):
        """Start the robot."""
        self.creators = {}

        for painting in self.generator:
            # isolate ids
            ids = painting['object']['proxies'][0]['dcIdentifier']['def']
            painting_id = ids[0].replace('Inv Nr.:', '').strip('( )')
            obj_id = ids[1]

            # Museum contains sevaral subcollections. Only handle mapped ones
            if painting_id.split(' ')[0] in self.prefix_map.keys():
                self.process_painting(painting, painting_id, obj_id)
            elif painting_id.split(' ')[0] not in self.bad_prefix:
                pywikibot.output(u'Skipped due to unknown collection: %s' %
                                 painting_id)

    def process_painting(self, painting, painting_id, obj_id):
        """Process a single painting.

        This will also create it if self.add_new is True.

        @param painting: information object for the painting
        @type painting: dict
        @param painting_id: the common (older) id of the painting in the
            Nationalmuseum collection
        @type painting_id: str
        @param obj_id: the internal id of the painting in the Nationalmuseum
            database.
        @type obj_id: str
        """
        uri = u'http://collection.nationalmuseum.se/eMuseumPlus?service=' \
              u'ExternalInterface&module=collection&objectId=%s&viewType=' \
              u'detailView' % obj_id
        europeana_url = u'http://europeana.eu/portal/record%s.html' % \
                        painting['object']['about']

        painting_item = None
        # newclaims = []
        if painting_id in self.painting_ids:
            painting_item = self.create_existing_painting(painting,
                                                          painting_id)
        elif self.add_new and not (
                self.skip_miniatures and PaintingsBot.is_miniature(painting)):
            # if objection collection is allowed and
            # unless it is aminiature and we are skipping those
            painting_item = self.create_new_painting(painting, painting_id,
                                                     europeana_url, uri)

        # add new claims
        if painting_item and painting_item.exists():
            data = painting_item.get(force=True)
            claims = data.get('claims')

            # add inventory number with collection
            self.add_inventory_and_collection_claim(painting_item, painting_id,
                                                    painting, uri)

            # Instance_of
            if u'P31' not in claims:
                self.add_instanceof_claim(painting_item, painting_id,
                                          painting)

            # title (as claim)
            # commented out as the titles in europeana are not reliable
            # if u'P1476' not in claims:
            #    self.add_title_claim(painting_item, painting)

            # Europeana_ID
            self.add_europeana_claim(painting_item, painting)

            # Check for potential images to add, if none is present
            if u'P18' not in claims:
                self.add_image_claim(painting_item, uri)

            # creator IFF through dbpedia
            if u'P170' not in claims:
                self.add_dbpedia_creator(painting_item, painting)

    def add_title_claim(self, painting_item, painting):
        """Add a title/P1476 claim based on dcTitle.

        @param painting_item: item to which claim is added
        @type painting_item: pywikibot.ItemPage
        @param painting: information object for the painting
        @type painting: dict
        """
        dc_title = painting['object']['proxies'][0]['dcTitle']
        titles = []
        for lang, title in dc_title.iteritems():
            titles.append(pywikibot.WbMonolingualText(title[0], lang))
        for title in titles:
            self.wd.addNewClaim(
                u'P1476',
                WD.Statement(title),
                painting_item,
                self.make_europeana_reference(painting))

    def add_locatedin_claim(self, painting_item, painting_id, painting):
        """Add a located_in/P276 claim based on subcollection.

        No longer used as subcollection does not match acual placing.

        @param painting_item: item to which claim is added
        @type painting_item: pywikibot.ItemPage
        @param painting_id: the common (older) id of the painting in the
            Nationalmuseum collection
        @type painting_id: str
        @param painting: information object for the painting
        @type painting: dict
        """
        place = self.prefix_map[painting_id.split(' ')[0]]['place']
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
            db_creator = painting['object']['proxies'][1]['dcCreator']['def']
            if len(db_creator) == 1:
                # skip anything more complex than one creator
                db_creator = db_creator[0].strip()
                if db_creator.startswith('http://dbpedia.org/resource/'):
                    if db_creator not in self.creators.keys():
                        self.creators[db_creator] = \
                            helpers.dbpedia_2_wikidata(db_creator)
                    creator_Q = self.creators[db_creator]
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
        images = self.file_from_external_link(uri)
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
        europeana_prop = u'P727'
        europeana_id = painting['object']['about'].lstrip('/')

        # abort if conflicting info
        if europeana_prop in painting_item.claims and \
                not self.wd.hasClaim(europeana_prop, europeana_id,
                                     painting_item):
            pywikibot.output(u'%s has conflicting %s. Expected %s' %
                             (painting_item, europeana_prop, europeana_id))
            return

        self.wd.addNewClaim(
            europeana_prop,
            WD.Statement(europeana_id),
            painting_item,
            self.make_europeana_reference(painting))

    def add_instanceof_claim(self, painting_item, painting_id, painting):
        """Add an instance_of/P31 claim.

        Instance_of is always painting or icon while working on the paintings
        collection.

        @param painting_item: item to which claim is added
        @type painting_item: pywikibot.ItemPage
        @param painting_id: the common (older) id of the painting in the
            Nationalmuseum collection
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

    def create_existing_painting(self, painting, painting_id):
        """Add base info to an existing paining.

        Adds the same info as would have been added had it been created with
        create_new_painting()

        @param painting: information object for the painting
        @type painting: dict
        @param painting_id: the common (older) id of the painting in the
            Nationalmuseum collection
        @type painting_id: str
        @return: the created painting item
        @rtype: pywikibot.ItemPage
        """
        painting_item = self.wd.QtoItemPage(self.painting_ids.get(painting_id))

        # check label
        data = painting_item.get()
        labels = make_labels(painting)
        new_labels = find_new_values(data, labels, 'labels')
        if new_labels:
            pywikibot.output('Adding label to %s' %
                             painting_item.title())
            painting_item.editLabels(new_labels)

        # check description
        descriptions = make_descriptions(painting)
        if descriptions:
            new_descr = find_new_values(data, descriptions, 'descriptions')
            if new_descr:
                pywikibot.output('Adding description to %s' %
                                 painting_item.title())
                painting_item.editDescriptions(new_descr)

        return painting_item

    def create_new_painting(self, painting, painting_id, europeana_url, uri):
        """Create a new painting item and return it.

        @param painting: information object for the painting
        @type painting: dict
        @param painting_id: the common (older) id of the painting in the
            Nationalmuseum collection
        @type painting_id: str
        @param europeana_url: reference url for europeana
        @type europeana_url: str
        @param uri: reference uri at nationalmuseum.se
        @type uri: str
        @return: the created painting item
        @rtype: pywikibot.ItemPage
        """
        data = {
            'labels': {},
            'descriptions': {}}

        data['labels'] = make_labels(painting)
        data['descriptions'] = make_descriptions(painting)
        if not data['descriptions']:
            return

        # print data
        # create new empty item and request Q-number
        summary = u'%s: Creating new item with data from %s' % (EDIT_SUMMARY,
                                                                europeana_url)
        painting_item = None
        try:
            painting_item = self.wd.make_new_item(data, summary)
        except pywikibot.data.api.APIError, e:
            if e.code == u'modification-failed':
                # disambiguate and try again
                for lang, content in data['descriptions'].iteritems():
                    disambiguation = content['value'] + u' (%s)' % painting_id
                    data['descriptions'][lang]['value'] = disambiguation
                try:
                    painting_item = self.wd.make_new_item(data, summary)
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

        return painting_item

    def add_inventory_and_collection_claim(self, painting_item, painting_id,
                                           painting, uri):
        """Add an inventory_no, with qualifier, and a collection/P195 claim.

        This will add the collection qualifier to any matching
        claim missing it.

        @param painting_item: item to which claim is added
        @type painting_item: pywikibot.ItemPage
        @param painting_id: the common (older) id of the painting in the
            Nationalmuseum collection
        @type painting_id: str
        @param painting: information object for the painting
        @type painting: dict
        @param uri: reference url on nationalmuseum.se
        @type uri: str
        """
        nationalmuseum_item = self.wd.QtoItemPage(INSTITUTION_Q)
        collection_p = u'P195'

        # abort if conflicting info
        if self.painting_id_prop in painting_item.claims and \
                not self.wd.hasClaim(self.painting_id_prop, painting_id,
                                     painting_item):
            pywikibot.output(u'%s has conflicting inv. no (%s). Expected %s' %
                             (painting_item, self.painting_id_prop,
                              painting_id))
            return

        # add inventory number with collection
        self.wd.addNewClaim(
            self.painting_id_prop,
            WD.Statement(painting_id).addQualifier(
                WD.Qualifier(
                    P=collection_p,
                    itis=nationalmuseum_item),
                force=True),
            painting_item,
            self.make_reference(uri))

        # add collection (or subcollection)
        subcol = self.prefix_map[painting_id.split(' ')[0]]['subcol']
        collection_item = nationalmuseum_item
        if subcol is not None:
            collection_item = self.wd.QtoItemPage(subcol)

        self.wd.addNewClaim(
            collection_p,
            WD.Statement(collection_item),
            painting_item,
            self.make_europeana_reference(painting))

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

    def file_from_external_link(self, uri):
        """Identify files from a Nationalmuseum uri.

        Hits are any files containing a link to the eMuseumPlus uri.

        @param uri: reference url on nationalmuseum.se
        @type uri: str
        @return: matching images
        @rtype: list
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

    def most_missed_creators(self, cacheMaxAge=0):
        """Produce list of most frequent, but unlinked, creators.

        Query WDQ for all objects in the collection missing an artist
        then put together a toplist for most desired creator
        """
        expected_items = []
        query = u'CLAIM[195:%s] AND NOCLAIM[170]' % \
                ',195:'.join(self.collections)  # collection
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset)

        if data.get('status').get('error') == 'OK':
            expected_items = data.get('items')

        creator_dict = {}
        counter = 0
        for q_val in expected_items:
            q_item = self.wd.QtoItemPage(q_val)
            data = q_item.get()
            claims = data.get('claims')
            if u'P170' in claims:
                continue
            descr = data.get('descriptions').get('en')
            if descr and descr.startswith(u'painting by '):
                creator = descr[len(u'painting by '):]
                if '(' in creator:  # to get rid of disambiguation addition
                    creator = creator[:creator.find('(')].strip()
                if creator in creator_dict.keys():
                    creator_dict[creator] += 1
                else:
                    creator_dict[creator] = 1
                counter += 1
        pywikibot.output(u'Found %d mentions of %d creators' %
                         (counter, len(creator_dict)))
        # output
        f = codecs.open(u'creatorHitlist.csv', 'w', 'utf-8')
        for k, v in creator_dict.iteritems():
            f.write(u'%d|%s\n' % (v, k))
        f.close()


def make_descriptions(painting):
    """Given a painting object construct descriptions in en/nl/sv.

    Returns None if there is a problem.

    @param painting: information object for the painting
    @type painting: dict
    @return: descriptions formatted for Wikidata input
    @rtype: dict
    """
    dcCreatorName = None
    try:
        dcCreator = painting['object']['proxies'][0]['dcCreator']
        dcCreatorName = dcCreator['sv'][0].strip()
    except KeyError:
        # Skip any weird creator settings
        return

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
            return None
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
    return descriptions


def make_labels(painting):
    """
    Given a painting object extract all potential labels.

    @param painting: information object for the painting
    @type painting: dict
    @return: language-lable pairs
    @rtype: dict
    """
    labels = {}
    for dcTitleLang, dcTitle in \
            painting['object']['proxies'][0]['dcTitle'].iteritems():
        labels[dcTitleLang] = {'language': dcTitleLang, 'value': dcTitle[0]}
    return labels


def find_new_values(data, values, key):
    """Identify any new label/description values which could be added to an item.

    @param data: the contents of the painting item
    @type data: dict
    @param values: the output of either make_labels or make_descriptions
    @type values: dict
    @param key: the type of values being processed (labels or descriptions)
    @type key: string
    @return lang-value pairs for new information
    @rtype dict
    """
    new_values = {}
    for lang, value in values.iteritems():
        if lang not in data.get(key).keys():
            new_values[lang] = value['value']
    return new_values


def get_painting_generator(rows=None, cursor=None, counter=0):
    """Get objects from Europeanas API.

    @param rows: the number of results to request
    @type rows: int
    @param cursor: the cursor for the next paginated response
    @type cursor: str
    @yield: dict
    """
    cursor = cursor or '*'  # initial value for cursor
    num_rows = rows or MAX_ROWS  # to separate the None case

    # perform search
    overview_json_data = get_search_results(min(MAX_ROWS, num_rows),
                                            cursor)
    cursor = overview_json_data.get('nextCursor')  # None if at the end

    # get data for each individual item in the search batch
    for item in overview_json_data.get('items'):
        yield get_single_painting(item)

    # call again to get around the MAX_ROWS limit of the api
    if cursor:
        if not rows or num_rows > MAX_ROWS:
            counter += MAX_ROWS
            pywikibot.output(u'%d...' % (counter))
            rows = min(rows, num_rows - MAX_ROWS)  # preserves None
            for g in get_painting_generator(rows=rows,
                                            cursor=cursor,
                                            counter=counter):
                yield g
        else:
            pywikibot.output(u'You are done!')
    else:
        pywikibot.output(u'No more results! You are done!')


def get_search_results(rows, cursor):
    """Retrieve the results from a single API search.

    The API call specifies:
    * DATA_PROVIDER=Nationalmuseum (Sweden)
    * what=paintings
    * PROVIDER=AthenaPlus

    @param rows: the number of results to request
    @type rows: int
    @param cursor: the cursor for the next paginated response
    @type cursor: str
    @return: the search result object
    @rtype: dict
    """
    search_url = 'http://www.europeana.eu/api/v2/search.json?wskey=' + \
                 config.APIKEY + \
                 '&profile=minimal&rows=%d' + \
                 '&cursor=%s' + \
                 '&query=%s'

    # split query off to better deal with escaping
    search_query = '*%3A*' + \
                   '&qf=DATA_PROVIDER%3A%22Nationalmuseum%2C+Sweden%22' + \
                   '&qf=what%3A+paintings' + \
                   '&qf=PROVIDER%3A%22AthenaPlus%22'

    overview_page = urllib2.urlopen(search_url % (rows, cursor, search_query))
    overview_json_data = json.loads(overview_page.read())
    overview_page.close()
    return overview_json_data


def get_single_painting(item):
    """Retrieve the data on a single painting.

    Raises an pywikibot.Error if a non-json response is recieved or if the
    querry status is not success.

    @param item: an item entry from the search results
    @type item: dict
    @return: the painting object
    @rtype: dict
    @raise: pywikibot.Error
    """
    url = 'http://europeana.eu/api/v2/record/%s.json?wskey=' + \
          config.APIKEY + \
          '&profile=full'
    item_url = url % item.get('id').lstrip('/')
    # retrieve and load the data
    try:
        api_page = urllib2.urlopen(item_url)
        json_data = json.loads(api_page.read())
        api_page.close()
    except ValueError, e:
        raise pywikibot.Error('Error loading Europeana item at '
                              '%s with error %s' % (item_url, e))

    # check that it worked
    if json_data.get(u'success'):
        return json_data
    else:
        raise pywikibot.Error('Error loading Europeana item at '
                              '%s with data:\n%s' % (item_url, json_data))


def main(*args):
    """Run the bot from the command line and handle any arguments."""
    # handle arguments
    rows = None
    add_new = True

    for arg in pywikibot.handle_args(args):
        for v in helpers.if_arg_value(arg, '-rows'):
            if helpers.is_pos_int(v):
                rows = int(v)
            else:
                raise pywikibot.Error(usage)
        for v in helpers.if_arg_value(arg, '-new'):
            if v.lower() in ('t', 'true'):
                add_new = True
            elif v.lower() in ('f', 'false'):
                add_new = True
            else:
                raise pywikibot.Error(usage)

    painting_gen = get_painting_generator(rows=rows)

    paintingsBot = PaintingsBot(painting_gen, INVNO_P, add_new)  # inv nr.
    paintingsBot.run()
    # paintingsBot.most_missed_creators()

if __name__ == "__main__":
    main()
