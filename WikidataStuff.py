#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author: Lokal_Profil
# License: MIT
#
"""Generally useful methods for interacting with Wikidata using pywikibot."""
import pywikibot

# Needed only for wdqLookup
import pywikibot.data.wikidataquery as wdquery

# Needed only for WikidataStringSearch
import os.path
from WikidataStringSearch import WikidataStringSearch


class WikidataStuff(object):
    """Useful methods for interacting with Wikidata using pywikibot."""

    repo = None

    class Reference(object):
        """A class for encoding the contents of a reference.

        Makes a distinction between the elements which should be included in a
        comparison with other references and those which shouldn't.

        e.g. for "reference URL: some URL", "retrieved: some_date" you would
        want to compare sources on the URL but not the date.

        A comparison will fail if ANY of the source_test sources are present.
        """

        def __init__(self, source_test=[], source_notest=[]):
            """Make a Reference object from the provided sources.

            param source_test: claims which should be included in
                comparison tests
            type source_test: pywikibot.Claim|list of pywikibot.Claim
            param source_notest: claims which should be excluded from
                comparison tests
            type source_notest: pywikibot.Claim|list of pywikibot.Claim
            """
            # standardise the two types of allowed input
            self.source_test = listify(source_test)
            self.source_notest = listify(source_notest)

            # validate input
            self.validate_sources()

        def validate_sources(self):
            """Validate the sources of a Reference."""
            sources = self.get_all_sources()
            if not sources:
                raise pywikibot.Error(
                    'You tried to create a reference without any sources')
            if not all(isinstance(s, pywikibot.Claim) for s in sources):
                raise pywikibot.Error(
                    'You tried to create a reference with a non-Claim source')

        def get_all_sources(self):
            """Return all the sources of a Reference."""
            return self.source_test + self.source_notest

        def __repr__(self):
            """Return a more complete string representation."""
            return u'WD.Reference(test: %s, no_test: %s)' % (
                self.source_test, self.source_notest)

    class Qualifier(object):
        """A class for encoding the contents of a qualifier.

        Essentially pywikibot.Claim without having to provide an instantiated
        repo.

        @todo: redo as SimpleClaim (if so reuse in Reference) or
               retire in favour of pywikibot.Claim
        """

        def __init__(self, P, itis):
            """Make a correctly formatted qualifier object for claims.

            param P: string the property (with or without "P")
            param itis: a valid claim target e.g. pywikibot.ItemPage
            """
            self.prop = u'P%s' % P.lstrip('P')
            self.itis = itis

        def __repr__(self):
            """Return a more complete string representation."""
            return u'WD.Qualifier(%s, %s)' % (self.prop, self.itis)

    class Statement(object):
        """A class for encoding the contents of a statement.

        Meaning a value and optional qualifiers
        @todo: itis test
        """

        def __init__(self, itis, special=False):
            """Make a correctly formatted statement object for claims.

            param itis: a valid claim target e.g. pywikibot.ItemPage
            param special: bool if itis is actaually a snackvalue
            """
            if special and itis not in ['somevalue', 'novalue']:
                raise pywikibot.Error(
                    'You tried to create a special statement with a '
                    'non-allowed snakvalue: %s' % itis)
            self.itis = itis
            self.quals = []
            self.special = special
            self.force = False

        def addQualifier(self, qual, force=False):
            """
            Add qualifer to the statement if not None,
            returns self to allow chaining
            param qual: Qualifier|None
            param force: bool whether qualifier should be added even to
                         already sourced items
            return Statement
            """
            # test input
            if qual is None:
                # simply skip any action
                return self
            elif not isinstance(qual, WikidataStuff.Qualifier):
                raise pywikibot.Error(
                    'addQualifier was called with something other '
                    'than a Qualifier|None object: %s' % qual)

            # register qualifier
            self.quals.append(qual)
            if force:
                self.force = True
            return self

        def isNone(self):
            """Test if Statment was created with itis=None."""
            return self.itis is None

        def __repr__(self):
            """Return a more complete string representation."""
            return u'WD.Statement(itis:%s, quals:%s, special:%s, force:%s)' % (
                self.itis, self.quals, self.special, self.force)

    def __init__(self, repo):
        """
        param repo: a pywikibot.Site().data_repository()
        """
        self.repo = repo

        # check if I am running on labs, for WikidataStringSearch
        self.onLabs = os.path.isfile(
            os.path.expanduser("~") +
            "/replica.my.cnf")
        if self.onLabs:
            self.wdss = WikidataStringSearch()

        # extend pywikibot.Claim with a __repr__ method
        def new_repr(self):
            return u'WD.Claim(%s: %s)' % (self.getID(), self.getTarget())
        pywikibot.Claim.__repr__ = new_repr

    def wdqLookup(self, query, cacheMaxAge=0):
        """
        Do a simple WDQ lookup returning the items ( less advanced than
        fillCache() in KulturnavBot )

        param query: a correctly formated wdq query
        param cacheMaxAge: age of local cache, 0 = disabled
        return list|None
        """
        wd_queryset = wdquery.QuerySet(query)
        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset)

        if data.get('status').get('error') == 'OK':
            return data.get('items')
        return None

    def searchGenerator(self, text, language):
        for q in self.wdss.search(text, language=language):
            yield self.QtoItemPage(q)

    def addLabelOrAlias(self, lang, name, item, prefix=None,
                        caseSensitive=False):
        """
        Adds a name as either a label (if none) or an alias
        in the given language

        param lang: the language code
        param name: the value to be added
        param item: the item to which the label/alias should be added
        param prefix: a prefix for the edit summary
        param caseSensitive: if the comparison is case sensitive
        """
        summary = u'Added [%s] %s to [[%s]]' % (lang, '%s', item.title())
        if prefix:
            summary = u'%s: %s' % (prefix, summary)
        # look at label
        if not item.labels or lang not in item.labels.keys():
            # add name to label
            labels = {lang: name}
            summary %= 'label'
            item.editLabels(labels, summary=summary)
            pywikibot.output(summary)
        elif name != item.labels[lang]:
            # look at aliases
            if not caseSensitive:
                if name.lower() == item.labels[lang].lower():
                    return None
            summary %= 'alias'
            if not item.aliases or lang not in item.aliases.keys():
                aliases = {lang: [name, ]}
                item.editAliases(aliases, summary=summary)
                pywikibot.output(summary)
            elif name not in item.aliases[lang]:
                if not caseSensitive:
                    if name.lower() in list_to_lower(item.aliases[lang]):
                        return None
                aliases = {lang: item.aliases[lang]}
                aliases[lang].append(name)
                item.editAliases(aliases, summary=summary)
                pywikibot.output(summary)

    # some more generic Wikidata methods
    def hasRef(self, prop, itis, claim):
        """
        Check if a given reference is already present at the given claim.

        param prop: the source property
        param itis: the source target value
        param claim: the pywikibot.Claim to be checked
        """
        if claim.sources:
            for i, source in enumerate(claim.sources):
                if prop in source.keys():
                    for s in source[prop]:
                        if self.bypassRedirect(s.getTarget()) == itis:
                            return True
        return False

    def addReference(self, item, claim, ref):
        """Add a reference if not already present.

        param item: the item on which all of this happens
        param claim: the pywikibot.Claim to be sourced
        param ref: the WD.Reference to add
        """
        # check if any of the sources are already present
        # note that this can be in any of its references
        if any(self.hasRef(source.getID(), source.getTarget(), claim)
                for source in ref.source_test):
            return False

        try:
            claim.addSources(ref.get_all_sources())  # writes to database
            pywikibot.output('Adding reference claim to %s in %s' %
                             (claim.getID(), item))
            return True
        except pywikibot.data.api.APIError, e:
            if e.code == u'modification-failed':
                pywikibot.output(u'modification-failed error: '
                                 u'ref to %s in %s' % (claim.getID(), item))
                return False
            else:
                raise pywikibot.Error(
                    'Something went very wrong trying to add a source: %s' % e)

    def hasAllQualifiers(self, quals, claim):
        """
        Checks if all qualifier are already present
        param quals: list of Qualifier
        param claim: Claim
        """
        for qual in quals:
            if not self.hasQualifier(qual, claim):
                return False
        return True

    def hasQualifier(self, qual, claim):
        """
        Checks if qualifier is already present
        param qual: Qualifier
        param claim: Claim
        """
        if claim.qualifiers:
            if qual.prop in claim.qualifiers.keys():
                for s in claim.qualifiers[qual.prop]:
                    if self.bypassRedirect(s.getTarget()) == qual.itis:
                        return True
                    # else:
                    #    pywikibot.output(s.getTarget())
        return False

    def addQualifier(self, item, claim, qual):
        """
        Check if a qualifier is present at the given claim,
        otherwise add it

        Known issue: This will qualify an already referenced claim
            this must therefore be tested before

        param item: itemPage to check
        param claim: Claim to check
        param qual: Qualifier to check
        """
        # check if already present
        if self.hasQualifier(qual, claim):
            return False

        qClaim = self.make_simple_claim(qual.prop, qual.itis)

        try:
            claim.addQualifier(qClaim)  # writes to database
            pywikibot.output('Adding qualifier to %s in %s' % (qual.prop,
                                                               item))
            return True
        except pywikibot.data.api.APIError, e:
            if e.code == u'modification-failed':
                pywikibot.output(u'modification-failed error: '
                                 u'qualifier to %s in %s' % (qual.prop,
                                                             item))
                return False
            else:
                raise pywikibot.Error(
                    'Something went very wrong trying to add a qualifier: %s' %
                    e)

    def hasClaim(self, prop, itis, item):
        """
        Checks if the claim already exists, if so returns that claim
        """
        if prop in item.claims.keys():
            for claim in item.claims[prop]:
                if isinstance(itis, pywikibot.WbTime):
                    # WbTime compared differently
                    if self.compareWbTimeClaim(claim.getTarget(), itis):
                        return claim
                elif self.bypassRedirect(claim.getTarget()) == itis:
                    return claim
        return None

    def hasSpecialClaim(self, prop, snaktype, item):
        """
        hasClaim() in the special case of 'somevalue' and 'novalue'
        """
        if prop in item.claims.keys():
            for claim in item.claims[prop]:
                if claim.getSnakType() == snaktype:
                    return claim
        return None

    def addNewClaim(self, prop, statement, item, ref):
        """
        Given an item, a property and a claim (in the itis format) this
        either adds the sourced claim, or sources it if already existing

        Known issues:
        * Only allows one qualifier to be added
        * Will source a claim with other qualifiers

        prop: a PXX code, unicode
        statement: a Statement() object
        item: the item being checked
        ref: None|Reference
        quals: None|list of Qualifiers
        """
        claim = pywikibot.Claim(self.repo, prop)

        # handle special cases
        if statement.special:
            claim.setSnakType(statement.itis)
            priorClaim = self.hasSpecialClaim(prop, statement.itis, item)
        else:
            claim.setTarget(statement.itis)
            priorClaim = self.hasClaim(prop, statement.itis, item)

        # test reference
        if not isinstance(ref, WikidataStuff.Reference):
            raise pywikibot.Error('No reference was given when making a new '
                                  'claim. Crashing')

        # test qualifier
        if priorClaim and statement.quals:
            # cannot add a qualifier to a previously sourced claim
            if not priorClaim.sources:
                # if unsourced
                for qual in statement.quals:
                    self.addQualifier(item, priorClaim, qual)
                self.addReference(item, priorClaim, ref)
            elif self.hasAllQualifiers(statement.quals, priorClaim):
                # if all qualifiers already present
                self.addReference(item, priorClaim, ref)
            elif statement.force:
                # if force is set
                for qual in statement.quals:
                    self.addQualifier(item, priorClaim, qual)
                self.addReference(item, priorClaim, ref)
            else:
                # add new qualified claim
                item.addClaim(claim)
                pywikibot.output('Adding %s claim to %s' % (prop, item))
                for qual in statement.quals:
                    self.addQualifier(item, claim, qual)
                self.addReference(item, claim, ref)
        elif priorClaim:
            self.addReference(item, priorClaim, ref)
        else:
            item.addClaim(claim)
            pywikibot.output('Adding %s claim to %s' % (prop, item))
            for qual in statement.quals:
                self.addQualifier(item, claim, qual)
            self.addReference(item, claim, ref)

    def bypassRedirect(self, item):
        """
        Checks if an item is a Redirect, and if so returns the
        target item instead of the original.
        This is needed for itis comparisons

        Not that this should either be called before an
        item.exists()/item.get() call or a new one must be made afterwards

        return ItemPage
        """
        # skip all non-ItemPage
        if not isinstance(item, pywikibot.ItemPage):
            return item

        if item.isRedirectPage():
            return item.getRedirectTarget()
        else:
            return item

    def compareWbTimeClaim(self, target, itis):
        """Compare if two WbTime claims are the same (regarding precision).

        thereby handling T107870

        param target: any Claim
        param itis: a WbTime
        raises: pywikibot.Error
        return bool
        """
        if not isinstance(target, pywikibot.WbTime):
            return False
        if itis.precision != target.precision:
            return False
        if itis.calendarmodel != target.calendarmodel:
            return False

        # comparison based on precision
        PRECISION = pywikibot.WbTime.PRECISION
        if itis.precision < PRECISION['year']:
            raise pywikibot.Error(
                u'Comparison cannot be done if precision is more coarse '
                u'than a year')
        if itis.year != target.year:
            return False
        if itis.precision >= PRECISION['month']:
            if itis.month != target.month:
                return False
            if itis.precision >= PRECISION['day']:
                if itis.day != target.day:
                    return False
                if itis.precision >= PRECISION['hour']:
                    if itis.hour != target.hour:
                        return False
                    if itis.precision >= PRECISION['minute']:
                        if itis.minute != target.minute:
                            return False
                        if itis.precision >= PRECISION['second']:
                            if itis.second != target.second:
                                return False
        return True

    def QtoItemPage(self, Q):
        """Make a pywikibot.ItemPage given a Q-value.

        @param Q: the Q-id of the item (with or without "Q")
        @type Q: string or int
        @rtype pywikibot.ItemPage
        """
        return pywikibot.ItemPage(
            self.repo,
            u'Q%s' % str(Q).lstrip('Q'))

    def make_simple_claim(self, prop, target):
        """Make a pywikibot.Claim given a property and target.

        @param prop: the P-id of a property (with or without "P")
        @type prop: str or int
        @param target: the target of the Claim
        @type target: object
        @rtype: pywikibot.Claim
        """
        claim = pywikibot.Claim(self.repo, u'P%s' % str(prop).lstrip('P'))
        claim.setTarget(target)
        return claim


# generic methods which are used already here and so could not be in helpers
# since that would cause a cyclical import
def list_to_lower(string_list):
    """Convert every string in a list to lower case.

    @param string_list: list of strings to convert
    @type string_list: list (of str)
    @rtype: list (of str)
    """
    lower_list = []
    for s in string_list:
        lower_list.append(s.lower())
    return lower_list


def listify(value):
    """Turn the given value, which might or might not be a list, into a list.

    @param value: The value to listify
    @type value: any
    @rtype: list, or None
    """
    if value is None:
        return None
    elif isinstance(value, list):
        return value
    else:
        return [value, ]
