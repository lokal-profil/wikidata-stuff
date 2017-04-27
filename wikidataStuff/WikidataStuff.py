#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author: Lokal_Profil
# License: MIT
#
"""Generally useful methods for interacting with Wikidata using pywikibot."""
from __future__ import unicode_literals
from builtins import dict, str, object
import os.path  # Needed for WikidataStringSearch

import pywikibot
from pywikibot.tools import deprecated


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
            return 'WD.Reference(test: %s, no_test: %s)' % (
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
            self.prop = 'P%s' % P.lstrip('P')
            self.itis = itis

        def __repr__(self):
            """Return a more complete string representation."""
            return 'WD.Qualifier(%s, %s)' % (self.prop, self.itis)

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
            return 'WD.Statement(itis:%s, quals:%s, special:%s, force:%s)' % (
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
            from wikidataStuff.WikidataStringSearch import WikidataStringSearch
            self.wdss = WikidataStringSearch()

        # extend pywikibot.Claim with a __repr__ method
        def new_repr(self):
            return 'WD.Claim(%s: %s)' % (self.getID(), self.getTarget())
        pywikibot.Claim.__repr__ = new_repr

    def searchGenerator(self, text, language):
        """Contruct generator for WikidataStringSearch."""
        for q in self.wdss.search(text, language=language):
            yield self.QtoItemPage(q)

    # TODO: Add function allowing multiple descriptions at once
    def add_description(self, lang, description, item, overwrite=False,
                        summary=None):
        """
        Add a description to the item in the given language.

        @param lang: the language code
        @param description: the value to be added, set to an empty string to,
            remove an existing description.
        @param item: the item to which the description should be added
        @param overwrite: whether any pre-existing description should be
            overwritten.
        @param summary: summary to append to auto-generated edit summary
        """
        summary = summary or self.edit_summary
        edit_summary = u'Added [%s] description to [[%s]]' % (
            lang, item.title())
        if summary:
            edit_summary = u'%s, %s' % (edit_summary, summary)

        if not item.descriptions or lang not in item.descriptions or overwrite:
            payload = {lang: description}
            item.editDescriptions(payload, summary=edit_summary)
            pywikibot.output(edit_summary)

    def addLabelOrAlias(self, lang, name, item, summary=None,
                        caseSensitive=False):
        """
        Add a name as either label (if none) or alias in the given language.

        @param lang: the language code
        @param name: the value to be added
        @param item: the item to which the label/alias should be added
        @param summary: summary to append to auto-generated edit summary
        @param caseSensitive: if the comparison is case sensitive
        """
        summary = summary or self.edit_summary

        edit_summary = 'Added [%s] %s to [[%s]]' % (lang, '%s', item.title())
        if summary:
            edit_summary = '%s, %s' % (edit_summary, summary)

        # look at label
        if not item.labels or lang not in item.labels:
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
            if not item.aliases or lang not in item.aliases:
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
                if prop in source:
                    for s in source[prop]:
                        if self.bypassRedirect(s.getTarget()) == itis:
                            return True
        return False

    def addReference(self, item, claim, ref, summary=None):
        """
        Add a reference if not already present.

        If a source contains the claims in WD.Reference AND additional claims,
        it will not be sourced.

        @param item: the item on which all of this happens
        @param claim: the pywikibot.Claim to be sourced
        @param ref: the WD.Reference to add
        @param summary: summary to append to auto-generated edit summary
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
        except pywikibot.data.api.APIError as e:
            if e.code == 'modification-failed':
                pywikibot.output('modification-failed error: '
                                 'ref to %s in %s' % (claim.getID(), item))
                return False
            else:
                raise pywikibot.Error(
                    'Something went very wrong trying to add a source: %s' % e)

    def has_all_qualifiers(self, quals, claim):
        """
        Check if all qualifiers are already present.

        Note that this checks if the supplied qualifiers are in the provided
        claim and if the provided claim has any other qualifiers.

        @param quals: Qualifiers to look for
        @type quals: list of Qualifier
        @param claim: Claim to check
        @type claim: pywikibot.Claim
        @return: Tuple of bools. First indicates an exact match of qualifiers,
            the second that all the provided qualifiers are present.
        @rtype: (bool, bool)
        """
        has_all = False
        exact_match = False
        for qual in quals:
            if not self.hasQualifier(qual, claim):
                return (exact_match, has_all)
        has_all = True

        len_claim_quals = sum(len(v) for v in claim.qualifiers.values())
        if len(quals) == len_claim_quals:
            exact_match = True

        return (exact_match, has_all)

    def hasQualifier(self, qual, claim):
        """
        Check if qualifier is already present.

        @param qual: Qualifier to look for
        @type qual: Qualifier
        @param claim: Claim to check
        @type claim: pywikibot.Claim
        """
        if claim.qualifiers:
            if qual.prop in claim.qualifiers:
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
        @param summary: summary to append to auto-generated edit summary
        """
        if not qual:
            raise pywikibot.Error(
                'Cannot call addQualifier() without a qualifier.')
        # check if already present
        if self.hasQualifier(qual, claim):
            return False

        qClaim = self.make_simple_claim(qual.prop, qual.itis)

        try:
            claim.addQualifier(qClaim, summary=summary)  # writes to database
            pywikibot.output('Adding qualifier %s to %s in %s' %
                             (qual.prop, claim.getID(), item))
            return True
        except pywikibot.data.api.APIError as e:
            if e.code == 'modification-failed':
                pywikibot.output('modification-failed error: '
                                 'qualifier to %s to %s in %s' %
                                 (qual.prop, claim.getID(), item))
                return False
            else:
                raise pywikibot.Error(
                    'Something went very wrong trying to add a qualifier: %s' %
                    e)

    @deprecated('hasClaim')
    def has_claim(self, prop, itis, item):
        """
        Check if the claim already exists, if so returns any matching claim.

        This only compares the target value and ignores any qualifiers.

        @param prop: the property id for the claim, with "P" prefix
        @type prop: basestring
        @param itis: the target of the claim
        @type itis: object
        @param item: itemPage to check
        @type item: pywikibot.ItemPage
        @return: list of matching claims
        @rtype: list of pywikibot.Claim
        """
        hits = []
        if prop in item.claims:
            for claim in item.claims[prop]:
                if isinstance(itis, pywikibot.WbTime):
                    # WbTime compared differently
                    if self.compareWbTimeClaim(claim.getTarget(), itis):
                        hits.append(claim)
                elif self.bypassRedirect(claim.getTarget()) == itis:
                    hits.append(claim)
        return hits

    def has_special_claim(self, prop, snaktype, item):
        """
        has_claim() in the special case of 'somevalue' and 'novalue'.

        This only compares the target value and ignores any qualifiers.

        @param prop: the property id for the claim, with "P" prefix
        @type prop: basestring
        @param snaktype: the target of the claim
        @type snaktype: basestring
        @param item: itemPage to check
        @type item: pywikibot.ItemPage
        @return: list of matching claims
        @rtype: list of pywikibot.Claim
        """
        hits = []
        if prop in item.claims:
            for claim in item.claims[prop]:
                if claim.getSnakType() == snaktype:
                    hits.append(claim)
        return hits

    def addNewClaim(self, prop, statement, item, ref, summary=None):
        """
        Add a claim or source it if already existing.

        Known caveats:
        * Will source a claim with no qualifiers
        * Will not source a claim with only one of the qualifiers

        @param prop: property id, with "P" prefix
        @type prop: basestring
        @param statement: target statement for the claim
        @param statement: Statement
        @param item: the item being checked
        @type item: pywikibot.ItemPage
        @param ref: reference to add to the claim
        @type ref: Reference|None
        @param summary: summary to append to auto-generated edit summary
        @type summary: basestring|None
        """
        claim = pywikibot.Claim(self.repo, prop)
        summary = summary or self.edit_summary

        # handle special cases
        if statement.special:
            claim.setSnakType(statement.itis)
            prior_claims = self.has_special_claim(prop, statement.itis, item)
        else:
            claim.setTarget(statement.itis)
            prior_claims = self.has_claim(prop, statement.itis, item)

        # test reference (must be a Reference or explicitly missing)
        if not isinstance(ref, WikidataStuff.Reference) and ref is not None:
            raise pywikibot.Error('The provided reference was not a Reference '
                                  'object. Crashing')

        # determine which, if any, prior_claim to source
        try:
            matching_claim = self.match_claim(
                prior_claims, statement.quals, statement.force)
        except pywikibot.Error as e:
            pywikibot.warning(
                "Problem adding %s claim to %s: %s" % (prop, item, e))
            return

        if matching_claim:
            for qual in statement.quals:
                self.addQualifier(item, matching_claim, qual, summary=summary)
            self.addReference(item, matching_claim, ref, summary=summary)
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

    def match_claim(self, claims, qualifiers, force):
        """
        Determine which claim is the best match for some given qualifiers.

        Selection is done in the following order:
        0. no claims: None selected
        1. many exact matches: raise error (means duplicates on Wikidata)
        2. one exact: select this
        3. many has_all: raise error (likely means duplicates on Wikidata)
        4. one has_all: select this
        5. if many claims: None selected
        6. if only one claim: see below
        6.1. if claim unsourced and unqualified: select this
        6.2. if sourced and unqualified and force: select this
        6.3. else: None selected

        @param claims: claims to attempt matching against
        @type claims: list of pywikibot.Claims
        @param qualifiers: qualifiers to match with
        @type qualifiers: list of Qualifier
        @param force: if sourced (but unqualified) claims should get qualified
        @type force: bool
        @return: Matching claim or None
        @rtype pywikibot.Claim|None
        """
        # case 0
        if not claims:
            return None

        # close matches for qualifiers case 1-4
        exact_matches = []
        has_all_matches = []
        for claim in claims:
            exact, has_all = self.has_all_qualifiers(qualifiers, claim)
            if exact:
                exact_matches.append(claim)
            if has_all:
                has_all_matches.append(claim)
        if exact_matches:
            if len(exact_matches) > 1:
                raise pywikibot.Error("Multiple identical claims")
            return exact_matches[0]
        elif has_all_matches:
            if len(has_all_matches) > 1:
                raise pywikibot.Error("Multiple semi-identical claims")
            return has_all_matches[0]

        # weak matches case 5-6
        if len(claims) > 1:
            return None
        claim = claims[0]
        if not claim.sources and not claim.qualifiers:
            return claim
        elif not claim.qualifiers and force:
            return claim
        else:
            return None

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
                'Comparison cannot be done if precision is more coarse '
                'than a year')
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
            'Q%s' % str(Q).lstrip('Q'))

    def make_simple_claim(self, prop, target):
        """
        Make a pywikibot.Claim given a property and target.

        @param prop: the P-id of a property (with or without "P")
        @type prop: basestring|int
        @param target: the target of the Claim
        @type target: object
        @rtype: pywikibot.Claim
        """
        claim = pywikibot.Claim(self.repo, 'P%s' % str(prop).lstrip('P'))
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
        identification = dict()  # If empty this defaults to creating an entity
        result = self.repo.editEntity(identification, data, summary=summary)
        pywikibot.output(summary)  # afterwards in case an error is raised

        # return the new item
        return self.QtoItemPage(result.get('entity').get('id'))

    def make_new_item_from_page(self, page, summary):
        """
        Make a new ItemPage given a Page object and an edit summary.

        Largely a wrapper around pywikibot.site.createNewItemFromPage()
        but enforcing a summary and reusing the repo object.

        @param page: the page from which the item should be created
        @type page: pywikibot.Page
        @param summary: an edit summary for the action
        @type summary: basestring
        @rtype: pywikibot.ItemPage
        """
        result = self.repo.createNewItemFromPage(page, summary)
        pywikibot.output(summary)  # afterwards in case an error is raised

        # return the new item
        return result


# generic methods which are used already here and so could not be in helpers
# since that would cause a cyclical import
def list_to_lower(string_list):
    """
    Convert every string in a list to lower case.

    @param string_list: list of strings to convert
    @type string_list: list (of basestring)
    @rtype: list (of basestring)
    """
    return [s.lower() for s in string_list]


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
