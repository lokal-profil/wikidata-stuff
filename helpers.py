# -*- coding: utf-8 -*-
"""Common non-fundamental methods used by WikidataStuff bots.

Methods comonly shared by Wikidata-stuff bots which are:
* not fundamental enough to be in WikidataStuff.py
* not limited to kulturNav (in which case they are in kulturnavBot.py)
* unrelated to Wikidata but reused throughout, if also needed in
  WikidataStuff.py then it is defined there and a wrapper provided here.
"""
import os
import json
import codecs
import urllib  # for dbpedia_2_wikidata
import urllib2  # for dbpedia_2_wikidata
import time  # for dbpedia_2_wikidata
from datetime import datetime  # for today_as_WbTime
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.wikidataquery as wdquery
import WikidataStuff
from WikidataStuff import WikidataStuff as WD
START_P = 'P580'  # start date
END_P = 'P582'  # end date
INSTANCE_OF_P = 'P31'

matchedNames = {  # a dict of found first/last_name_Q lookups
    u'lastName': {},
    u'firstName': {}
}


def load_json_file(filename, force_path=None):
    """Load a local json file and return the data.

    The force_path parameter is needed for loading files in the same
    directory as the calling script, when that script is called from
    another directory.

    @param filename: The filename, and path, to the josn file
    @type filename: str, unicode
    @param force_path: Force the system to look for the file in the
        same directory as this file
    @type force_path: str
    @return: Data in the json file
    @rtype: any
    """
    if force_path:
        path = os.path.dirname(os.path.abspath(force_path))
        filename = os.path.join(path, filename)
    f = codecs.open(filename, 'r', 'utf-8')
    return json.load(f)


def fill_cache(pid, queryoverride=None, cache_max_age=0):
    """Query Wikidata to fill the cache of entities which contain the id.

    @param pid: The id property
    @type pid: str, unicode
    @param queryoverride: A WDQ query to use instead of CLAIM[pid]
    @type queryoverride: str, unicode
    @param cache_max_age: Max age of local cache, defaults to 0
    @type cache_max_age: int
    @return: Dictionary of IDno to Qno
    @rtype: dict
    """
    pid = pid.lstrip('P')  # standardise indput
    result = {}
    if queryoverride:
        query = queryoverride
    else:
        query = u'CLAIM[%s]' % pid
    wd_queryset = wdquery.QuerySet(query)

    wd_query = wdquery.WikidataQuery(cacheMaxAge=cache_max_age)
    data = wd_query.query(wd_queryset, props=[str(pid), ])

    if data.get('status').get('error') == 'OK':
        expectedItems = data.get('status').get('items')
        props = data.get('props').get(str(pid))
        for prop in props:
            if prop[2] in result.keys() and prop[0] != result[prop[2]]:
                # Detect id's that are used more than once.
                raise pywikibot.Error('Double ids in Wikidata: %s, %s (%s)' %
                                      (prop[0], result[prop[2]], query))
            result[prop[2]] = prop[0]

        if expectedItems == len(result):
            pywikibot.output('I now have %s items in cache' %
                             expectedItems)

    return result


def today_as_WbTime():
    """Get todays data as a WbTime object.

    Given an ISO date object (1922-09-17Z or 2014-07-11T08:14:46Z)
    this returns the equivalent WbTime object

    @return: Todays date correctly formated
    @rtype: pywikibot.WbTime
    """
    today = datetime.today()
    date = pywikibot.WbTime(year=today.year,
                            month=today.month,
                            day=today.day)
    return date


def iso_to_WbTime(date):
    """Convert ISO date string into WbTime object.

    Given an ISO date object (1922-09-17Z or 2014-07-11T08:14:46Z)
    this returns the equivalent WbTime object

    @param item: An ISO date string
    @type item: str, unicode
    @return: The converted result
    @rtype: pywikibot.WbTime
    """
    date = date[:len('YYYY-MM-DD')].split('-')
    if len(date) == 3 and all(is_int(x) for x in date):
        # 1921-09-17Z or 2014-07-11T08:14:46Z
        d = int(date[2])
        if d == 0:
            d = None
        m = int(date[1])
        if m == 0:
            m = None
        return pywikibot.WbTime(
            year=int(date[0]),
            month=m,
            day=d)
    elif len(date) == 1 and is_int(date[0][:len('YYYY')]):
        # 1921Z
        return pywikibot.WbTime(year=int(date[0][:len('YYYY')]))
    elif len(date) == 2 and \
            all(is_int(x) for x in (date[0], date[1][:len('MM')])):
        # 1921-09Z
        m = int(date[1][:len('MM')])
        if m == 0:
            m = None
        return pywikibot.WbTime(
            year=int(date[0]),
            month=m)

    # once here all interpretations have failed
    raise pywikibot.Error(u'An invalid ISO-date string received: ' % date)


def add_start_end_qualifiers(statement, startVal, endVal):
    """Add start/end qualifiers to a statement if non-None, or return None.

    @param statement: The statement to decorate
    @type statement: WD.Statement
    @param startVal: An ISO date string for the starting point
    @type startVal: str, unicode, or None
    @param endVal: An ISO date string for the end point
    @type endVal: str, unicode, or None
    @return: A statement decorated with start/end qualifiers
    @rtype: WD.Statement, or None
    """
    if not isinstance(statement, WD.Statement):
        raise pywikibot.Error(u'Non-statement recieved: %s' % statement)
    if statement.isNone():
        return None

    # add qualifiers
    quals = []
    if startVal:
        quals.append(
            WD.Qualifier(
                P=START_P,
                itis=iso_to_WbTime(startVal)))
    if endVal:
        quals.append(
            WD.Qualifier(
                P=END_P,
                itis=iso_to_WbTime(endVal)))
    for q in quals:
        statement.addQualifier(q)
    return statement


def match_name(name, typ, wd, limit=75):
    """Check if there is an item matching the name.

    Given a plaintext name (first or last) this checks if there is
    a unique matching entity of the right name type. Search results are
    stored in 'matchedNames' for later look-up.

    @param name: The name to search for
    @type name: str, unicode
    @param typ: The name type (either 'lastName' or 'firstName')
    @type typ: str, unicode
    @param wd: The running WikidataStuff instance
    @type wd: WikidataStuff (WD)
    @param limit: Number of hits before skipping (defaults to 75,
        ignored if onLabs)
    @type limit: int
    @return: A matching item, if any
    @rtype: pywikibot.ItemPage, or None
    """
    global matchedNames
    prop = {u'lastName': (u'Q101352',),
            u'firstName': (u'Q12308941', u'Q11879590', u'Q202444')}

    # Skip any empty values
    if not name.strip():
        return

    # Check if already looked up
    if name in matchedNames[typ].keys():
        return matchedNames[typ][name]

    # search for potential matches
    matches = None
    props = prop[typ]
    if wd.onLabs:
        matches = match_name_on_labs(name, props, wd)
    else:
        matches = match_name_off_labs(name, props, wd, limit)

    # get rid of duplicates then check for uniqueness
    matches = list(set(matches))
    if len(matches) == 1:
        item = wd.bypassRedirect(matches[0])
        matchedNames[typ][name] = item  # store for later reuse
        return item
    elif len(matches) > 1:
        pywikibot.log(u'Possible duplicates: %s' % matches)

    # getting here means no hits so store that for later reuse
    matchedNames[typ][name] = None


def match_name_on_labs(name, types, wd):
    """Check if there is an item matching the name using database on labs.

    Requires that the bot is running on WMF toollabs.

    @param name: The name to search for
    @type name: str, unicode
    @param types: The Q-values which are allowed for INSTANCE_OF_P
    @type types: tuple of unicode
    @param wd: The running WikidataStuff instance
    @type wd: WikidataStuff (WD)
    @return: Any matching items
    @rtype: list (of pywikibot.ItemPage)
    """
    matches = []
    objgen = pagegenerators.PreloadingItemGenerator(
        wd.searchGenerator(name, None))
    for obj in objgen:
        filter_on_types(obj, types, matches)
    return matches


def match_name_off_labs(name, types, wd, limit):
    """Check if there is an item matching the name using API search.

    Less good than match_name_on_labs() but works from anywhere.

    @param name: The name to search for
    @type name: str, unicode
    @param types: The Q-values which are allowed for INSTANCE_OF_P
    @type types: tuple of unicode
    @param wd: The running WikidataStuff instance
    @type wd: WikidataStuff (WD)
    @return: Any matching items
    @rtype: list (of pywikibot.ItemPage)
    """
    matches = []
    objgen = pagegenerators.PreloadingItemGenerator(
        pagegenerators.WikibaseItemGenerator(
            pagegenerators.SearchPageGenerator(
                name, step=None, total=10,
                namespaces=[0], site=wd.repo)))

    # check if P31 and then if any of prop[typ] in P31
    i = 0
    for obj in objgen:
        obj = wd.bypassRedirect(obj)
        i += 1
        if i > limit:
            # better to skip than to crash when search times out
            # remove any matches (since incomplete) and exit loop
            return []  # avoids keeping a partial list

        if name in (obj.get().get('labels').values() +
                    obj.get().get('aliases').values()):
            filter_on_types(obj, types, matches)
    return matches


def filter_on_types(obj, types, matches):
    """Filter potential matches by (instance of) type.

    @param obj: potential matches
    @type obj: pywikibot.ItemPage
    @param types: The Q-values which are allowed for INSTANCE_OF_P
    @type types: tuple of unicode
    @param matches: list of confirmed matches
    @type matches: list (of pywikibot.ItemPage)
    """
    if INSTANCE_OF_P in obj.get().get('claims'):
        # print 'claims:', obj.get().get('claims')[u'P31']
        values = obj.get().get('claims')[INSTANCE_OF_P]
        for v in values:
            # print u'val:', v.getTarget()
            if v.getTarget().title() in types:
                matches.append(obj)


def is_int(value):
    """Check if the given value is an integer.

    @param value: The value to check
    @type value: str, or int
    @return bool
    """
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False


def is_pos_int(value):
    """Check if the given value is a positive integer.

    @param value: The value to check
    @type value: str, or int
    @return bool
    """
    if is_int(value) and int(value) > 0:
        return True
    return False


def bundle_values(values):
    """Merge multiple values/lists into one list.

    @param values: values to bundle
    @param values: list, of values or lists
    @return: the bundled list
    @rtype: list
    """
    bundle = []
    for v in values:
        if v is not None:
            v = listify(v)
            bundle += v
    if bundle:
        return bundle


def reorder_names(name):
    """Detect a "Last, First" string and return as "First Last".

    Strings without commas are returned as is.
    Strings with multiple commas result in an None being returned.

    @param name: The value to check
    @type name: str, or unicode
    @return str, or None
    """
    if name.find(',') > 0 and len(name.split(',')) == 2:
        p = name.split(',')
        name = u'%s %s' % (p[1].strip(), p[0].strip())
        return name
    elif name.find(',') == -1:
        # no comma means just a nickname e.g. Michelangelo
        return name
    else:
        # e.g. more than 1 comma
        pywikibot.output(u'unexpectedly formatted name: %s' % name)
        return None


def find_files(path, fileExts, subdir=True):
    """Identify all files with a given extension in a given directory.

    @param path: Path to directory to look in
    @type path: str, or unicode
    @param fileExts: Allowed file extensions (case insensitive)
    @type fileExts: tuple (of str, or unicode)
    @param subdir: Whether subdirs should also be searched, default=True
    @return: Paths to found files
    @rtype: list (of str, or unicode)
    """
    files = []
    subdirs = []
    for filename in os.listdir(path):
        if os.path.splitext(filename)[1].lower() in fileExts:
            files.append(os.path.join(path, filename))
        elif os.path.isdir(os.path.join(path, filename)):
            subdirs.append(os.path.join(path, filename))
    if subdir:
        for subdir in subdirs:
            files += find_files(path=subdir, fileExts=fileExts)
    return files


def dbpedia_2_wikidata(dbpedia):
    """Return the wikidata id matching a dbpedia entry.

    Given a dbpedia resource reference
    (e.g. http://dbpedia.org/resource/Richard_Bergh)
    this returns the sameAs wikidata value, if any.
    Returns None if no matches.

    @param dbpedia: the dbpedia resource reference
    @type dbpedia: str
    @return: Q-value of matching wikidata entry
    @rtype: str
    """
    url = u'http://dbpedia.org/sparql?' + \
          u'default-graph-uri=http%3A%2F%2Fdbpedia.org&query=DESCRIBE+%3C' + \
          urllib.quote(dbpedia.encode('utf-8')) + \
          u'%3E&output=application%2Fld%2Bjson'

    try:
        db_page = urllib2.urlopen(url)
    except IOError:
        pywikibot.output(u'dbpedia is complaining so sleeping for 10s')
        time.sleep(10)
        try:
            db_page = urllib2.urlopen(url)
        except IOError:
            pywikibot.output(u'dbpedia is still complaining about %s, '
                             u'skipping' % dbpedia)
            return None

    try:
        db_data = db_page.read()
        json_data = json.loads(db_data)
        db_page.close()
    except ValueError, e:
        pywikibot.output(u'dbpedia-skip: %s, %s' % (dbpedia, e))
        return None

    if json_data.get('@graph'):
        for g in json_data.get('@graph'):
            if g.get('http://www.w3.org/2002/07/owl#sameAs'):
                for same in g.get('http://www.w3.org/2002/07/owl#sameAs'):
                    if isinstance(same, (str, unicode)) and \
                            same.startswith('http://wikidata.org/entity/'):
                        return same[len('http://wikidata.org/entity/'):]
                return None
    return None


# generic methods which are needed in WikidataStuff.py are defined there to
# avoid a cyclical import
def listify(value):
    """Wrapper for WikidataStuff instance of the method."""
    return WikidataStuff.listify(value)


def list_to_lower(string_list):
    """Wrapper for WikidataStuff instance of the method."""
    return WikidataStuff.list_to_lower(string_list)
