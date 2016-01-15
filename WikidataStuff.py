#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Generally useful functions for interacting with Wikidata using pywikibot

Author: Lokal_Profil
License: MIT
"""
import pywikibot

# Needed only for wdqLookup
import pywikibot.data.wikidataquery as wdquery

# Needed only for WikidataStringSearch
import os.path
from WikidataStringSearch import WikidataStringSearch


class WikidataStuff(object):
    """
    A framework of generally useful functions for interacting with
    Wikidata using pywikibot
    """
    repo = None

    class Reference(object):
        """
        A class for encoding contents of a reference
        @todo: should be done way more general
               esentially a list of claims to test (during comparison)
               esentially a list of claims not to test (during comparison)
        source_P: a sourcing property
        source: the source value, a valid claim
                e.g. pywikibot.ItemPage(repo, "Q6581097")
        time_P: a property which takes a time value
        time: must be a pywikibot.WbTime object
        """
        def __init__(self, source_P, source, time_P, time):
            """
            @todo
            """
            self.source_P = u'P%s' % source_P.lstrip('P')
            self.source = source
            self.time_P = u'P%s' % time_P.lstrip('P')
            self.time = time

        def __repr__(self):
            """Return a more complete string representation."""
            return u'WD.Reference(%s, %s, %s, %s)' % (
                self.source_P, self.source, self.time_P, self.time)

    class Qualifier(object):
        """
        A class for encoding contents of a qualifier
        @todo: redo as SimpleClaim
        @todo: throw exceptions instead
        """
        def __init__(self, P, itis):
            """
            Make a correctly formatted qualifier object for claims

            param P: string the property (with or without "P")
            param itis: an itis statement, for non itemPage claims
            """
            self.prop = u'P%s' % P.lstrip('P')
            self.itis = itis

        def __repr__(self):
            """Return a more complete string representation."""
            return u'WD.Qualifier(%s, %s)' % (self.prop, self.itis)

    class Statement(object):
        """
        A class for encoding contents of a statement meaning a value and
        optional qualifiers
        @todo: throw exceptions instead
        @todo: itis test
        """
        def __init__(self, itis, special=False):
            """
            Make a correctly formatted statement object for claims
            param itis: a valid claim e.g. pywikibot.ItemPage
            param special: bool if itis is actaually a snackvalue
            """
            if special:
                if itis not in ['somevalue', 'novalue']:
                    pywikibot.output(u'You tried to create a special'
                                     u'statement with a non-allowed snakvalue'
                                     u': %s' % itis)
                    exit(1)
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
                pywikibot.output('addQualifier was called with something '
                                 'other than a Qualifier|None object: %s' %
                                 qual)
                exit(1)

            # register qualifier
            self.quals.append(qual)
            if force:
                self.force = True
            return self

        def isNone(self):
            """
            Test if Statment was created with itis=None
            """
            return self.itis is None

        def __repr__(self):
            """Return a more complete string representation."""
            txt = u'WD.Statement(%s, %s, special:%s, force:%s)' % (
                self.itis, self.quals, self.special, self.force)
            return txt

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
                    if name.lower() in self.listToLower(item.aliases[lang]):
                        return None
                aliases = {lang: item.aliases[lang]}
                aliases[lang].append(name)
                item.editAliases(aliases, summary=summary)
                pywikibot.output(summary)

    def listToLower(self, stringList):
        """
        Converts a list of strings to a list of the same strings but
        lower case
        """
        lowList = []
        for s in stringList:
            lowList.append(s.lower())
        return lowList

    # some more generic Wikidata methods
    def hasRef(self, prop, itis, claim):
        """
        Checks if a given reference is already present at the given claim
        """
        if claim.sources:
            for i in range(0, len(claim.sources)):
                if prop in claim.sources[i].keys():
                    for s in claim.sources[i][prop]:
                        if self.bypassRedirect(s.getTarget()) == itis:
                            return True
                        # else:
                        #    pywikibot.output(s.getTarget())
        return False

    def addReference(self, item, claim, ref):
        """
        Add a reference with a source statement and a timestamp.
        Checks that no such source statement already exists (independent
        of timestamp)

        param item: the item on which all of this happens
        param claim: the pywikibot.Claim to be sourced
        ref: a Reference
        """
        statedin = pywikibot.Claim(self.repo, ref.source_P)
        statedin.setTarget(ref.source)

        # check if already present (with any date)
        if self.hasRef(ref.source_P, ref.source, claim):
            return False

        # if not then add
        retrieved = pywikibot.Claim(self.repo, ref.time_P)
        retrieved.setTarget(ref.time)

        try:
            claim.addSources([statedin, retrieved])  # writes to database
            pywikibot.output('Adding reference claim to %s in %s' %
                             (claim.getID(), item))
            return True
        except pywikibot.data.api.APIError, e:
            if e.code == u'modification-failed':
                pywikibot.output(u'modification-failed error: '
                                 u'ref to %s in %s' % (claim.getID(), item))
                return False
            else:
                pywikibot.output(e)
                exit(1)

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

        qClaim = pywikibot.Claim(self.repo, qual.prop)
        qClaim.setTarget(qual.itis)

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
                pywikibot.output(e)
                exit(1)

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

        # test reference and qualifier
        if not isinstance(ref, WikidataStuff.Reference):
            pywikibot.output(u'No reference was given when making a new '
                             u'claim. Crashing')
            exit(1)

        if priorClaim and len(statement.quals) > 0:
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
        """
        Compares if two WbTime claims are the same (regarding precision)
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
        """
        Wrapper for pywikibot.ItemPage()
        param Q: string the Q-item for value (with or without "Q")
        return pywikibot.ItemPage
        """
        return pywikibot.ItemPage(
            self.repo,
            u'Q%s' % Q.lstrip('Q'))
