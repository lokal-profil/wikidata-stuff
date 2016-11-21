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
from wikidataStuff.WikidataStringSearch import WikidataStringSearch


class WikidataStuff(object):
    """Useful methods for interacting with Wikidata using pywikibot."""

    repo = None
    edit_summary = None

    class Reference(object):
        """
        A class for encoding the contents of a reference.

        Makes a distinction between the elements which should be included in a
        comparison with other references and those which shouldn't.

        e.g. for "reference URL: some URL", "retrieved: some_date" you would
        want to compare sources on the URL but not the date.

        A comparison will fail if ANY of the source_test sources are present.
        """

        def __init__(self, source_test=None, source_notest=None):
            """
            Make a Reference object from the provided sources.

            @param source_test: claims which should be included in
                comparison tests
            @type source_test: pywikibot.Claim|list of pywikibot.Claim
            @param source_notest: claims which should be excluded from
                comparison tests
            @type source_notest: pywikibot.Claim|list of pywikibot.Claim
            """
            # avoid mutable default arguments
            source_test = source_test or []
            source_notest = source_notest or []

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
        """
        A class for encoding the contents of a qualifier.

        Essentially pywikibot.Claim without having to provide an instantiated
        repo.

        @todo: redo as SimpleClaim (if so reuse in Reference) or
               retire in favor of pywikibot.Claim
        """

        def __init__(self, P, itis):
            """
            Make a correctly formatted qualifier object for claims.

            @param P: the property (with or without "P")
            @type P: basestring
            @param itis: a valid claim target e.g. pywikibot.ItemPage
            @type itis: object
            """
            self.prop = u'P%s' % P.lstrip('P')
            self.itis = itis

        def __repr__(self):
            """Return a more complete string representation."""
            return u'WD.Qualifier(%s, %s)' % (self.prop, self.itis)

    class Statement(object):
        """A class for the contents of a statement (value + qualifiers)."""

        def __init__(self, itis, special=False):
            """
            Make a correctly formatted statement object for claims.

            @todo: itis test

            @param itis: a valid claim target e.g. pywikibot.ItemPage
            @type itis: object
            @param special: if itis is actually a snackvalue
            @type special: bool
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
            Add qualifier to the statement if not None.

            Returns self to allow chaining.

            @param qual: the qualifier to add
            @type qual: Qualifier|None
            @param force: whether qualifier should be added even to already
                sourced items
            @type force: bool
            @rtype Statement
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
            """Test if Statement was created with itis=None."""
            return self.itis is None

        def __repr__(self):
            """Return a more complete string representation."""
            return u'WD.Statement(itis:%s, quals:%s, special:%s, force:%s)' % (
                self.itis, self.quals, self.special, self.force)

    def __init__(self, repo, edit_summary=None):
        """
        Initialise the WikidataStuff object with a data repository.

        @param repo: the WikiBase repository site
        @type repo: pywikibot.site.DataSite
        @param edit_summary: optional string to append to all automatically
            generated edit summaries
        @type edit_summary: basestring|None
        """
        self.repo = repo
        if edit_summary:
            self.edit_summary = edit_summary

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

    def wdqLookup(self, query, cache_max_age=0):
        """
        Do a simple WDQ lookup returning the items.

        This is less advanced than fillCache() in KulturnavBot.

        @param query: a correctly formated wdq query
        @type query: basestring
        @param cache_max_age: age of local cache, 0 = disabled
        @type cache_max_age: int
        @rtype list|None
        """
        wd_queryset = wdquery.QuerySet(query)
        wd_query = wdquery.WikidataQuery(cacheMaxAge=cache_max_age)
        data = wd_query.query(wd_queryset)

        if data.get('status').get('error') == 'OK':
            return data.get('items')
        return None

    def searchGenerator(self, text, language):
        """A generator for WikidataStringSearch."""
        for q in self.wdss.search(text, language=language):
            yield self.QtoItemPage(q)

    def addLabelOrAlias(self, lang, name, item, summary=None,
                        caseSensitive=False):
        """
        Add a name as either label (if none) or alias in the given language.

        @param lang: the language code
        @param name: the value to be added
        @param item: the item to which the label/alias should be added
        @param summary: optional summary to append to auto-generated edit summary
        @param caseSensitive: if the comparison is case sensitive
        """
        summary = summary or self.edit_summary

        edit_summary = u'Added [%s] %s to [[%s]]' % (lang, '%s', item.title())
        if summary:
            edit_summary = u'%s, %s' % (edit_summary, summary)

        # look at label
        if not item.labels or lang not in item.labels.keys():
            # add name to label
            labels = {lang: name}
            edit_summary %= 'label'
            item.editLabels(labels, summary=edit_summary)
            pywikibot.output(edit_summary)
        elif name != item.labels[lang]:
            # look at aliases
            if not caseSensitive:
                if name.lower() == item.labels[lang].lower():
                    return None
            edit_summary %= 'alias'
            if not item.aliases or lang not in item.aliases.keys():
                aliases = {lang: [name, ]}
                item.editAliases(aliases, summary=edit_summary)
                pywikibot.output(edit_summary)
            elif name not in item.aliases[lang]:
                if not caseSensitive:
                    if name.lower() in list_to_lower(item.aliases[lang]):
                        return None
                aliases = {lang: item.aliases[lang]}
                aliases[lang].append(name)
                item.editAliases(aliases, summary=edit_summary)
                pywikibot.output(edit_summary)

    # some more generic Wikidata methods
    def hasRef(self, prop, itis, claim):
        """
        Check if a given reference is already present at the given claim.

        @param prop: the source property
        @param itis: the source target value
        @param claim: the pywikibot.Claim to be checked
        """
        if claim.sources:
            for i, source in enumerate(claim.sources):
                if prop in source.keys():
                    for s in source[prop]:
                        if self.bypassRedirect(s.getTarget()) == itis:
                            return True
        return False

    def addReference(self, item, claim, ref, summary=None):
        """
        Add a reference if not already present.

        @param item: the item on which all of this happens
        @param claim: the pywikibot.Claim to be sourced
        @param ref: the WD.Reference to add
        @param summary: optional summary to append to auto-generated edit summary
        """
        # check if any of the sources are already present
        # note that this can be in any of its references
        if ref is None:
            return False

        if any(self.hasRef(source.getID(), source.getTarget(), claim)
                for source in ref.source_test):
            return False

        try:
            # writes to database
            claim.addSources(ref.get_all_sources(), summary=summary)
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
        Check if all qualifiers are already present.

        @param quals: list of Qualifier
        @param claim: Claim
        """
        for qual in quals:
            if not self.hasQualifier(qual, claim):
                return False
        return True

    def hasQualifier(self, qual, claim):
        """
        Check if qualifier is already present.

        @param qual: Qualifier
        @param claim: Claim
        """
        if claim.qualifiers:
            if qual.prop in claim.qualifiers.keys():
                for s in claim.qualifiers[qual.prop]:
                    if self.bypassRedirect(s.getTarget()) == qual.itis:
                        return True
                    # else:
                    #    pywikibot.output(s.getTarget())
        return False

    def addQualifier(self, item, claim, qual, summary=None):
        """
        Check if a qualifier is present at the given claim, otherwise add it.

        Known issue: This will qualify an already referenced claim
            this must therefore be tested for before.

        @param item: itemPage to check
        @param claim: Claim to check
        @param qual: Qualifier to check
        @param summary: optional summary to append to auto-generated edit summary
        """
        # check if already present
        if self.hasQualifier(qual, claim):
            return False

        qClaim = self.make_simple_claim(qual.prop, qual.itis)

        try:
            claim.addQualifier(qClaim, summary=summary)  # writes to database
            pywikibot.output('Adding qualifier %s to %s in %s' %
                             (qual.prop, claim.getID(), item))
            return True
        except pywikibot.data.api.APIError, e:
            if e.code == u'modification-failed':
                pywikibot.output(u'modification-failed error: '
                                 u'qualifier to %s to %s in %s' %
                                 (qual.prop, claim.getID(), item))
                return False
            else:
                raise pywikibot.Error(
                    'Something went very wrong trying to add a qualifier: %s' %
                    e)

    def hasClaim(self, prop, itis, item):
        """
        Check if the claim already exists, if so returns that claim.

        @todo: does this correctly handle when the claim has qualifiers,
            https://www.wikidata.org/w/index.php?title=Q18575190&type=revision&diff=316829153&oldid=306752022
            indicates it does not.
            It returns the first matching claim (independent of qualifiers), as
            a result if the first has the wrong qualifiers it does not find a
            later claim with the correct qualifiers.
        @param prop: the property id for the claim, with "P" prefix
        @type prop: basestring
        @param itis: the target of the claim
        @type itis: object
        @param item: itemPage to check
        @type item: pywikibot.ItemPage
        @rtype: pywikibot.Claim|None
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
        """hasClaim() in the special case of 'somevalue' and 'novalue'."""
        if prop in item.claims.keys():
            for claim in item.claims[prop]:
                if claim.getSnakType() == snaktype:
                    return claim
        return None

    def addNewClaim(self, prop, statement, item, ref, summary=None):
        """
        Add a claim or source it if already existing.

        Known issues:
        * Only allows one qualifier to be added
        * Will source a claim with other qualifiers

        @param prop: property id, with "P" prefix
        @type prop: basestring
        @param statement: target statement for the claim
        @param statement: Statement
        @param item: the item being checked
        @type item: pywikibot.ItemPage
        @param ref: reference to add to the claim
        @type ref: Reference|None
        @param summary: optional summary to append to auto-generated edit summary
        @type summary: basestring|None
        """
        claim = pywikibot.Claim(self.repo, prop)
        summary = summary or self.edit_summary

        # handle special cases
        if statement.special:
            claim.setSnakType(statement.itis)
            priorClaim = self.hasSpecialClaim(prop, statement.itis, item)
        else:
            claim.setTarget(statement.itis)
            priorClaim = self.hasClaim(prop, statement.itis, item)

        # test reference (must be a Reference or explicitly missing)
        if not isinstance(ref, WikidataStuff.Reference) and ref is not None:
            raise pywikibot.Error('The provided reference was not a Reference '
                                  'object. Crashing')

        # test qualifier
        if priorClaim and statement.quals:
            # cannot add a qualifier to a previously sourced claim
            if not priorClaim.sources:
                # if unsourced
                for qual in statement.quals:
                    self.addQualifier(item, priorClaim, qual, summary=summary)
                self.addReference(item, priorClaim, ref, summary=summary)
            elif self.hasAllQualifiers(statement.quals, priorClaim):
                # if all qualifiers already present
                self.addReference(item, priorClaim, ref, summary=summary)
            elif statement.force:
                # if force is set
                for qual in statement.quals:
                    self.addQualifier(item, priorClaim, qual, summary=summary)
                self.addReference(item, priorClaim, ref, summary=summary)
            else:
                # add new qualified claim
                item.addClaim(claim, summary=summary)
                pywikibot.output('Adding %s claim to %s' % (prop, item))
                for qual in statement.quals:
                    self.addQualifier(item, claim, qual, summary=summary)
                self.addReference(item, claim, ref, summary=summary)
        elif priorClaim:
            self.addReference(item, priorClaim, ref, summary=summary)
        else:
            item.addClaim(claim, summary=summary)
            pywikibot.output('Adding %s claim to %s' % (prop, item))
            for qual in statement.quals:
                self.addQualifier(item, claim, qual, summary=summary)
            self.addReference(item, claim, ref, summary=summary)

    def bypassRedirect(self, item):
        """
        Check if an item is a Redirect, and if so returns the target item.

        This is needed for itis comparisons. Return the original item if not a
        redirect.

        Not that this should either be called before an
        item.exists()/item.get() call or a new one must be made afterwards

        @param item: item to investigate
        @type item: pywikibot.ItemPage
        @rtype pywikibot.ItemPage
        """
        # skip all non-ItemPage
        if not isinstance(item, pywikibot.ItemPage):
            return item

        if item.isRedirectPage():
            return item.getRedirectTarget()
        else:
            return item

    def compareWbTimeClaim(self, target, itis):
        """
        Compare if two WbTime claims are the same (regarding precision).

        Handles T107870.

        @todo implement as __cmp__ in __init__ T131453

        @param target: any Claim
        @param itis: a WbTime
        @raises: pywikibot.Error
        @rtype bool
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
        """
        Make a pywikibot.ItemPage given a Q-value.

        @param Q: the Q-id of the item (with or without "Q")
        @type Q: basestring|int
        @rtype pywikibot.ItemPage
        """
        return pywikibot.ItemPage(
            self.repo,
            u'Q%s' % str(Q).lstrip('Q'))

    def make_simple_claim(self, prop, target):
        """
        Make a pywikibot.Claim given a property and target.

        @param prop: the P-id of a property (with or without "P")
        @type prop: basestring|int
        @param target: the target of the Claim
        @type target: object
        @rtype: pywikibot.Claim
        """
        claim = pywikibot.Claim(self.repo, u'P%s' % str(prop).lstrip('P'))
        claim.setTarget(target)
        return claim

    def make_new_item(self, data, summary):
        """
        Make a new ItemPage given some data and an edit summary.

        @param data: data, correctly formatted, with which to create the item.
        @type data: dict
        @param summary: an edit summary for the action
        @type summary: basestring
        @rtype: pywikibot.ItemPage
        """
        identification = {}  # If empty this defaults to creating an entity
        result = self.repo.editEntity(identification, data, summary=summary)
        pywikibot.output(summary)  # afterwards in case an error is raised

        # return the new item
        return self.QtoItemPage(result.get(u'entity').get('id'))


# generic methods which are used already here and so could not be in helpers
# since that would cause a cyclical import
def list_to_lower(string_list):
    """
    Convert every string in a list to lower case.

    @param string_list: list of strings to convert
    @type string_list: list (of basestring)
    @rtype: list (of basestring)
    """
    lower_list = []
    for s in string_list:
        lower_list.append(s.lower())
    return lower_list


def listify(value):
    """
    Turn the given value, which might or might not be a list, into a list.

    @param value: The value to listify
    @rtype: list|None
    """
    if value is None:
        return None
    elif isinstance(value, list):
        return value
    else:
        return [value, ]
