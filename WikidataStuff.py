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
    A freamwork of generally useful functions for interacting with
    Wikidata using pywikibot
    """
    repo = None

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
            yield pywikibot.ItemPage(self.repo, q)

    def addLabelOrAlias(self, lang, name, item, prefix=None):
        """
        Adds a name as either a label (if none) or an alias
        in the given language

        param lang: the language code
        param name: the value to be added
        param item: the item to which the label/alias should be added
        param prefix: a prefix for the edit summary
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
            summary %= 'alias'
            if not item.aliases or lang not in item.aliases.keys():
                aliases = {lang: [name, ]}
                item.editAliases(aliases, summary=summary)
                pywikibot.output(summary)
            elif name not in item.aliases[lang]:
                aliases = {lang: item.aliases[lang]}
                aliases[lang].append(name)
                item.editAliases(aliases, summary=summary)
                pywikibot.output(summary)

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
        ref: a dict with the folowing key-values
             source_P: a sourcing property
             source: the source value, a valid claim
                          e.g. pywikibot.ItemPage(repo, "Q6581097")
             time_P: a property which takes a time value
             time: must be a pywikibot.WbTime object
        """
        statedin = pywikibot.Claim(self.repo, ref[u'source_P'])
        statedin.setTarget(ref[u'source'])

        # check if already present (with any date)
        if self.hasRef(ref[u'source_P'], ref[u'source'], claim):
            return False

        # if not then add
        retrieved = pywikibot.Claim(self.repo, ref[u'time_P'])
        retrieved.setTarget(ref[u'time'])

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

    def hasQualifier(self, prop, itis, claim):
        """
        Checks if qualifier is already present
        """
        if claim.qualifiers:
            if prop in claim.qualifiers.keys():
                for s in claim.qualifiers[prop]:
                    if self.bypassRedirect(s.getTarget()) == itis:
                        return True
                    # else:
                    #    pywikibot.output(s.getTarget())
        return False

    def addQualifier(self, item, claim, prop, itis):
        """
        Check if a qualifier is present at the given claim,
        otherwise add it

        Known issue: This will qualify an already referenced claim
            this must therefore be tested before
        """
        # check if already present
        if self.hasQualifier(prop, itis, claim):
            return False

        qClaim = pywikibot.Claim(self.repo, prop)
        qClaim.setTarget(itis)

        try:
            claim.addQualifier(qClaim)  # writes to database
            pywikibot.output('Adding qualifier to %s in %s' % (prop, item))
            return True
        except pywikibot.data.api.APIError, e:
            if e.code == u'modification-failed':
                pywikibot.output(u'modification-failed error: '
                                 u'qualifier to %s in %s' % (prop, item))
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
                if self.bypassRedirect(claim.getTarget()) == itis:
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

    def addNewClaim(self, prop, itis, item, ref, qual=None, snaktype=None):
        """
        Given an item, a property and a claim (in the itis format) this
        either adds the sourced claim, or sources it if already existing

        Known issues:
        * Only allows one qualifier to be added
        * Will source a claim with other qualifiers

        prop: a PXX code, unicode
        itis: a valid claim e.g. pywikibot.ItemPage(repo, "Q6581097")
        item: the item being checked
        ref: a referenc dict. see addReference() for requirements
        qual: optional qualifier to add to claim, dict{prop, itis, force}
            prop and itis: are formulated as those for the claim
            force: (bool) add even to a sourced claim
        snaktype: somevalue/novalue
            (should only ever be set through addNewSpecialClaim)
        """
        claim = pywikibot.Claim(self.repo, prop)

        # handle special cases
        if snaktype is None:
            claim.setTarget(itis)
            priorClaim = self.hasClaim(prop, itis, item)
        else:
            claim.setSnakType(snaktype)
            priorClaim = self.hasSpecialClaim(prop, snaktype, item)

        # test reference and qualifier
        if self.validReference(ref) is None:
            pywikibot.output(u'No reference was given when making a new '
                             u'claim. Crashing')
            exit(1)
        validQualifier = self.validQualifier(qual) is not None

        if priorClaim and validQualifier:
            # cannot add a qualifier to a previously sourced claim
            if not priorClaim.sources:
                # if unsourced
                self.addQualifier(item, priorClaim,
                                  qual[u'prop'], qual[u'itis'])
                self.addReference(item, priorClaim, ref)
            elif self.hasQualifier(qual[u'prop'], qual[u'itis'], priorClaim):
                # if qualifier already present
                self.addReference(item, priorClaim, ref)
            elif qual[u'force']:
                # if force is set
                self.addQualifier(item, priorClaim,
                                  qual[u'prop'], qual[u'itis'])
                self.addReference(item, priorClaim, ref)
            else:
                # add new qualified claim
                item.addClaim(claim)
                pywikibot.output('Adding %s claim to %s' % (prop, item))
                self.addQualifier(item, claim, qual[u'prop'], qual[u'itis'])
                self.addReference(item, claim, ref)
        elif priorClaim:
            self.addReference(item, priorClaim, ref)
        else:
            item.addClaim(claim)
            pywikibot.output('Adding %s claim to %s' % (prop, item))
            if validQualifier:
                self.addQualifier(item, claim, qual[u'prop'], qual[u'itis'])
            self.addReference(item, claim, ref)

    def addNewSpecialClaim(self, prop, snaktype, item, ref, qual=None):
        """
        addNewClaim() but for the special 'somevalue' and 'novalue'
        """
        if snaktype not in ['somevalue', 'novalue']:
            pywikibot.output(u'You passed a non-allowed snakvalue to '
                             u'addNewSpecialClaim(): %s' % snaktype)
            exit(1)

        # pass it on to addNewClaim with itis=None
        self.addNewClaim(
            prop,
            None,
            item,
            ref,
            qual=qual,
            snaktype=snaktype)

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

    def validQualifier(self, qual):
        """
        Tests that a given qualifier object exists and if so that it is valid
        """
        if qual is None:
            return None
        elif isinstance(qual, dict) and \
                set(qual.keys()) == set(['prop', 'itis', 'force']):
            return True
        else:
            pywikibot.output(u'The qualifier was not formatted correctly: %s'
                             % qual)
            exit(1)

    def validReference(self, ref):
        """
        Tests that a given ref object exists and if so that it is valid
        """
        if ref is None:
            return None
        elif isinstance(ref, dict) and \
                set(ref.keys()) == set(['source_P', 'source',
                                        'time_P', 'time']):
            return True
        else:
            pywikibot.output(u'The reference was not formatted correctly: %s'
                             % ref)
            exit(1)
