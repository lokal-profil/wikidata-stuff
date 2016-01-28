# -*- coding: utf-8 -*-
"""Common non-fundamental methods used by WikidataStuff bots.

Methods comonly shared by Wikidata-stuff bots but not fundamental
enough to be in WikidataStuff.py or limited to kulturNav (in which case they
are in kulturnavBot.py)
"""
import os
import json
import codecs
import pywikibot
import pywikibot.data.wikidataquery as wdquery
from pywikibot import pagegenerators
from WikidataStuff import WikidataStuff as WD
START_P = 'P580'  # start date
END_P = 'P582'  # end date
INSTANCE_OF_P = 'P31'

matchedNames = {  # a dict of found first/last_name_Q lookups
    u'lastName': {},
    u'firstName': {}
}


def load_json_file(filename):
    """Load a local json file and return the data.

    @param filename: The filename, and path, to the josn file
    @type filename: str, unicode
    @return: Data in the json file
    @rtype: any
    """
    f = codecs.open(filename, 'r', 'utf-8')
    return json.load(f)


def fill_cache(ID_P, queryoverride=u'', cacheMaxAge=0):
    """Query Wikidata to fill the cache of entities which contain the id.

    @param ID_P: The id property
    @type ID_P: str, unicode
    @param queryoverride: A WDQ query to use instead of CLAIM[ID_P]
    @type queryoverride: str, unicode
    @param cacheMaxAge: Max age of local cache, defaults to 0
    @type cacheMaxAge: int
    @return: Dictionary of IDno to Qno
    @rtype: dict
    """
    ID_P = ID_P.lstrip('P')  # standardise indput
    result = {}
    if queryoverride:
        query = queryoverride
    else:
        query = u'CLAIM[%s]' % ID_P
    wd_queryset = wdquery.QuerySet(query)

    wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
    data = wd_query.query(wd_queryset, props=[str(ID_P), ])

    if data.get('status').get('error') == 'OK':
        expectedItems = data.get('status').get('items')
        props = data.get('props').get(str(ID_P))
        for prop in props:
            if prop[2] in result.keys() and prop[0] != result[prop[2]]:
                # Detect id's that are used more than once.
                raise pywikibot.Error('Double ids in Wikidata: %s, %s' %
                                      (prop[0], result[prop[2]]))
            result[prop[2]] = prop[0]

        if expectedItems == len(result):
            pywikibot.output('I now have %s items in cache' %
                             expectedItems)

    return result


def ISO_to_WbTime(date):
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
                itis=ISO_to_WbTime(startVal)))
    if endVal:
        quals.append(
            WD.Qualifier(
                P=END_P,
                itis=ISO_to_WbTime(endVal)))
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


def match_name_on_labs(name, props, wd):
    """Check if there is an item matching the name using database on labs.

    Requires that the bot is running on WMF toollabs.

    @param name: The name to search for
    @type name: str, unicode
    @param props: The Q-values which are allowed for INSTANCE_OF_P
    @type props: tuple of unicode
    @param wd: The running WikidataStuff instance
    @type wd: WikidataStuff (WD)
    @return: Any matching items
    @rtype: list (of pywikibot.ItemPage)
    """
    matches = []
    objgen = pagegenerators.PreloadingItemGenerator(
        wd.searchGenerator(name, None))
    for obj in objgen:
        if INSTANCE_OF_P in obj.get().get('claims'):
            # print 'claims:', obj.get().get('claims')[u'P31']
            values = obj.get().get('claims')[INSTANCE_OF_P]
            for v in values:
                # print u'val:', v.getTarget()
                if v.getTarget().title() in props:
                    matches.append(obj)
    return matches


def match_name_off_labs(name, props, wd, limit):
    """Check if there is an item matching the name using API search.

    Less good than matchNameOnLabs() but works from anywhere.

    @param name: The name to search for
    @type name: str, unicode
    @param props: The Q-values which are allowed for INSTANCE_OF_P
    @type props: tuple of unicode
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
            matches = []
            break
        # print obj.title()
        if name in (obj.get().get('labels').values() +
                    obj.get().get('aliases').values()):

            # Check if the right type of object
            if INSTANCE_OF_P in obj.get().get('claims'):
                # print 'claims:', obj.get().get('claims')[u'P31']
                values = obj.get().get('claims')[INSTANCE_OF_P]
                for v in values:
                    # print u'val:', v.getTarget()
                    if v.getTarget().title() in props:
                        matches.append(obj)
    return matches


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


def listify(value):
    """Turn the given value, which might or might not be a list, into a list.

    @param value: The value to listify
    @type value: any
    @return list, or None
    """
    if value is None:
        return None
    elif isinstance(value, list):
        return value
    else:
        return [value, ]


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
