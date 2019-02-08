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
from pywikibot.tools import deprecated, deprecated_args

import wikidataStuff.helpers as helpers
from wikidataStuff.reference import Reference


class WikidataStuff(object):
    """Useful methods for interacting with Wikidata using pywikibot."""

    # A hack to trigger deprecation warnings for a subclass is to defined
    # a static method with the same name
    @staticmethod
    @deprecated('wikidatastuff.reference.Reference', since='0.4')
    def Reference(*args, **kwargs):
        """DEPRECATED."""
        return Reference(*args, **kwargs)

    @staticmethod
    @deprecated('wikidatastuff.qualifier.Qualifier', since='0.4')
    def Qualifier(*args, **kwargs):
        """DEPRECATED."""
        from wikidatastuff.qualifier import Qualifier
        return Qualifier(*args, **kwargs)

    @staticmethod
    @deprecated('wikidatastuff.statement.Statement', since='0.4')
    def Statement(*args, **kwargs):
        """DEPRECATED."""
        from wikidatastuff.statement import Statement
        return Statement(*args, **kwargs)

    repo = None
    edit_summary = None

    def __init__(self, repo, edit_summary=None, no_wdss=False):
        """
        Initialise the WikidataStuff object with a data repository.

        @param repo: the WikiBase repository site
        @type repo: pywikibot.site.DataSite
        @param edit_summary: optional string to append to all automatically
            generated edit summaries
        @type edit_summary: basestring|None
        @param no_wdss: if WikidataStringSearch should be disabled even if
            running on Labs. Default: False.
        @type no_wdss: bool
        """
        self.repo = repo
        if edit_summary:
            self.edit_summary = edit_summary

        # check if I am running on labs, for WikidataStringSearch
        if no_wdss:
            self.onLabs = False
        else:
            self.onLabs = os.path.isfile(
                os.path.expanduser("~") +
                "/replica.my.cnf")
        if self.onLabs:
            from wikidataStuff.wikidata_string_search import WikidataStringSearch
            self.wdss = WikidataStringSearch()

    @deprecated('search_generator', since='0.4')
    def searchGenerator(self, text, language):
        """DEPRECATED."""
        return self.search_generator(text, language)

    def search_generator(self, text, language):
        """Contruct generator for WikidataStringSearch."""
        for q in self.wdss.search(text, language=language):
            yield self.q_to_itempage(q)

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
        data = {lang: description}
        self.add_multiple_descriptions(
            data, item, overwrite=overwrite, summary=summary)

    def add_multiple_descriptions(self, data, item, overwrite=False,
                                  summary=None):
        """
        Add multiple descriptions to the item in one edit.

        @param data: dictionary of language-description pairs
        @param item: the item to which the descriptions should be added
        @param overwrite: whether any pre-existing descriptions should be
            overwritten (when a new description is available in that language).
        @param summary: summary to append to auto-generated edit summary
        """
        item.exists()  # load contents

        summary = summary or self.edit_summary
        edit_summary = u'Added [{{lang}}] description to [[{qid}]]'.format(
            qid=item.title())
        if summary:
            edit_summary = u'{0}, {1}'.format(edit_summary, summary)

        new_descriptions = dict()

        for lang, desc in data.items():
            if (not item.descriptions or
                    lang not in item.descriptions or
                    overwrite):
                new_descriptions[lang] = desc

        if new_descriptions:
            edit_summary = edit_summary.format(
                lang=', '.join(sorted(new_descriptions.keys())))
            item.editDescriptions(new_descriptions, summary=edit_summary)
            pywikibot.output(edit_summary)

    @deprecated('add_label_or_alias', since='0.4')
    @deprecated_args(caseSensitive='case_sensitive', since='<0.4')
    def addLabelOrAlias(self, lang, name, item, summary=None,
                        case_sensitive=False):
        """DEPRECATED."""
        return self.add_label_or_alias(
            lang, name, item, summary, case_sensitive)

    def add_label_or_alias(self, lang, name, item, summary=None,
                           case_sensitive=False):
        """
        Add a name as either label (if none) or alias in the given language.

        @param lang: the language code
        @param name: the value to be added
        @param item: the item to which the label/alias should be added
        @param summary: summary to append to auto-generated edit summary
        @param case_sensitive: if the comparison is case sensitive
        """
        data = {lang: name}
        self.add_multiple_label_or_alias(
            data, item, case_sensitive=case_sensitive, summary=summary)

    def add_multiple_label_or_alias(self, data, item, case_sensitive=False,
                                    summary=None):
        """
        Add multiple labels or aliases to the item in one edit.

        Adds the name as either a label (if none) or an alias in the
        given language.

        If adding both a label and an alias in the same language (or multiple
        aliases) supply a list of names where the first will be used as label.

        @param data: dictionary of language-name pairs. The name can be either
            a single name or a list of names.
        @param item: the item to which the label/alias should be added
        @param summary: summary to append to auto-generated edit summary
        @param case_sensitive: if the comparison is case sensitive
        """
        item.exists()  # load contents

        summary = summary or self.edit_summary
        edit_summary = 'Added [{{lang}}] {{typ}} to [[{qid}]]'.format(
            qid=item.title())
        if summary:
            edit_summary = u'{0}, {1}'.format(edit_summary, summary)

        new_label_langs = []
        labels = item.labels or dict()
        new_alias_langs = []
        aliases = item.aliases or dict()

        for lang, names in data.items():
            for name in helpers.listify(names):
                if lang not in labels:
                    labels[lang] = name
                    new_label_langs.append(lang)
                elif (
                        (case_sensitive and name != labels[lang]) or
                        (not case_sensitive and
                            name.lower() != labels[lang].lower())):
                    if lang not in aliases:
                        aliases[lang] = [name, ]
                        new_alias_langs.append(lang)
                    elif (
                            (case_sensitive and name not in aliases[lang]) or
                            (not case_sensitive and
                                name.lower() not in helpers.list_to_lower(
                                    aliases[lang]))):
                        aliases[lang].append(name)
                        new_alias_langs.append(lang)

        new_label_langs = sorted(list(set(new_label_langs)))
        new_alias_langs = sorted(list(set(new_alias_langs)))

        if new_label_langs:
            label_summary = edit_summary.format(
                lang=', '.join(new_label_langs), typ='label')
            item.editLabels(labels, summary=label_summary)
            pywikibot.output(label_summary)

        if new_alias_langs:
            alias_summary = edit_summary.format(
                lang=', '.join(new_alias_langs), typ='alias')
            item.editAliases(aliases, summary=alias_summary)
            pywikibot.output(alias_summary)

    # some more generic Wikidata methods
    @deprecated('has_ref', since='0.4')
    def hasRef(self, prop, itis, claim):
        """DEPRECATED."""
        return self.has_ref(prop, itis, claim)

    def has_ref(self, prop, itis, claim):
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
                        if self.bypass_redirect(s.getTarget()) == itis:
                            return True
        return False

    @deprecated('add_reference', since='0.4')
    def addReference(self, item, claim, ref, summary=None):
        """DEPRECATED."""
        return self.add_reference(item, claim, ref, summary)

    def add_reference(self, item, claim, ref, summary=None):
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

        if any(self.has_ref(source.getID(), source.getTarget(), claim)
                for source in ref.source_test):
            return False

        try:
            # writes to database
            claim.addSources(ref.get_all_sources(), summary=summary)
            pywikibot.output('Adding reference claim to {0} in {1}'.format(
                claim.getID(), item))
            return True
        except pywikibot.data.api.APIError as e:
            if e.code == 'modification-failed':
                pywikibot.output(
                    'modification-failed error: ref to {0} in {1}'.format(
                        claim.getID(), item))
                return False
            else:
                raise pywikibot.Error(
                    'Something went very wrong trying to add '
                    'a source: {}'.format(e))

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
            if not self.has_qualifier(qual, claim):
                return (exact_match, has_all)
        has_all = True

        len_claim_quals = sum(len(v) for v in claim.qualifiers.values())
        if len(quals) == len_claim_quals:
            exact_match = True

        return (exact_match, has_all)

    @deprecated('has_qualifier', since='0.4')
    def hasQualifier(self, qual, claim):
        """DEPRECATED."""
        return self.has_qualifier(qual, claim)

    def has_qualifier(self, qual, claim):
        """
        Check if qualifier is already present.

        @param qual: Qualifier to look for
        @type qual: Qualifier
        @param claim: Claim to check
        @type claim: pywikibot.Claim
        """
        if claim.qualifiers and qual.prop in claim.qualifiers:
            for s in claim.qualifiers[qual.prop]:
                if self.bypass_redirect(s.getTarget()) == qual.itis:
                    return True
                # else:
                #    pywikibot.output(s.getTarget())
        return False

    @deprecated('add_qualifier', since='0.4')
    def addQualifier(self, item, claim, qual, summary=None):
        """DEPRECATED."""
        return self.add_qualifier(item, claim, qual, summary)

    def add_qualifier(self, item, claim, qual, summary=None):
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
                'Cannot call add_qualifier() without a qualifier.')
        # check if already present
        if self.has_qualifier(qual, claim):
            return False

        q_claim = self.make_simple_claim(qual.prop, qual.itis)

        try:
            claim.addQualifier(q_claim, summary=summary)  # writes to database
            pywikibot.output('Adding qualifier {0} to {1} in {2}'.format(
                qual.prop, claim.getID(), item))
            return True
        except pywikibot.data.api.APIError as e:
            if e.code == 'modification-failed':
                pywikibot.output(
                    'modification-failed error: '
                    'qualifier to {0} to {1} in {2}'.format(
                        qual.prop, claim.getID(), item))
                return False
            else:
                raise pywikibot.Error(
                    'Something went very wrong trying to '
                    'add a qualifier: {}'.format(e))

    @deprecated('has_claim', since='<0.4')
    def hasClaim(self, prop, itis, item):
        """DEPRECATED."""
        return self.has_claim(prop, itis, item)

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
                    if self.compare_wbtime_claim(claim.getTarget(), itis):
                        hits.append(claim)
                elif self.bypass_redirect(claim.getTarget()) == itis:
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

    @deprecated('add_new_claim', since='0.4')
    def addNewClaim(self, prop, statement, item, ref, summary=None):
        """DEPRECATED."""
        return self.add_new_claim(prop, statement, item, ref, summary)

    def add_new_claim(self, prop, statement, item, ref, summary=None):
        """
        Add a claim or source it if already existing.

        Known caveats:
        * Will source a claim with no qualifiers
        * Will not source a claim with only one of the qualifiers

        @param prop: property id, with "P" prefix
        @type prop: basestring
        @param statement: target statement for the claim
        @type statement: Statement
        @param item: the item being checked
        @type item: pywikibot.ItemPage
        @param ref: reference to add to the claim, overrides ref embedded in
            statement.
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

        # use ref embedded in statement unless external is explicitly provided
        if not ref and statement.ref:
            ref = statement.ref

        # test reference (must be a Reference or explicitly missing)
        if not isinstance(ref, Reference) and ref is not None:
            raise pywikibot.Error('The provided reference was not a Reference '
                                  'object. Crashing')

        # determine which, if any, prior_claim to source
        try:
            matching_claim = self.match_claim(
                prior_claims, statement.quals, statement.force)
        except pywikibot.Error as e:
            pywikibot.warning(
                "Problem adding {0} claim to {1}: {2}".format(prop, item, e))
            return

        if matching_claim:
            for qual in statement.quals:
                self.add_qualifier(item, matching_claim, qual, summary=summary)
            self.add_reference(item, matching_claim, ref, summary=summary)
        else:
            item.addClaim(claim, summary=summary)
            pywikibot.output('Adding {0} claim to {1}'.format(prop, item))
            for qual in statement.quals:
                self.add_qualifier(item, claim, qual, summary=summary)
            self.add_reference(item, claim, ref, summary=summary)

    @deprecated('bypass_redirect', since='0.4')
    def bypassRedirect(self, item):
        """DEPRECATED."""
        return self.bypass_redirect(item)

    def bypass_redirect(self, item):
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

    @deprecated('compare_wbtime_claim', since='0.4')
    def compareWbTimeClaim(self, target, itis):
        """DEPRECATED."""
        return self.compare_wbtime_claim(target, itis)

    def compare_wbtime_claim(self, target, itis):
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
                        if (itis.precision >= PRECISION['second'] and
                                itis.second != target.second):
                            return False
        return True

    @deprecated_args(Q='qid', since='0.4')
    @deprecated('q_to_itempage', since='0.4')
    def QtoItemPage(self, qid):
        """DEPRECATED."""
        return self.q_to_itempage(qid)

    def q_to_itempage(self, qid):
        """
        Make a pywikibot.ItemPage given a Q-value.

        @param qid: the Q-id of the item (with or without "Q")
        @type qid: basestring|int
        @rtype pywikibot.ItemPage
        """
        return pywikibot.ItemPage(
            self.repo,
            'Q{}'.format(str(qid).lstrip('Q')))

    def make_simple_claim(self, prop, target):
        """
        Make a pywikibot.Claim given a property and target.

        @param prop: the P-id of a property (with or without "P")
        @type prop: basestring|int
        @param target: the target of the Claim
        @type target: object
        @rtype: pywikibot.Claim
        """
        claim = pywikibot.Claim(self.repo, 'P{}'.format(str(prop).lstrip('P')))
        claim.setTarget(target)
        return claim

    def make_new_item(self, data, summary=None):
        """
        Make a new ItemPage given some data and an edit summary.

        @param data: data, correctly formatted, with which to create the item.
        @type data: dict
        @param summary: an edit summary for the action
        @type summary: basestring
        @rtype: pywikibot.ItemPage
        """
        summary = summary or self.edit_summary

        identification = dict()  # If empty this defaults to creating an entity
        result = self.repo.editEntity(identification, data, summary=summary)
        pywikibot.output(summary)  # afterwards in case an error is raised

        # return the new item
        return self.q_to_itempage(result.get('entity').get('id'))

    def make_new_item_from_page(self, page, summary=None):
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
        summary = summary or self.edit_summary

        result = self.repo.createNewItemFromPage(page, summary)
        pywikibot.output(summary)  # afterwards in case an error is raised

        # return the new item
        return result


@deprecated('wikidataStuff.helpers.listify', since='0.4')
def listify(value):
    """DEPRECATED."""
    return helpers.listify(value)


@deprecated('wikidataStuff.helpers.list_to_lower', since='0.4')
def list_to_lower(string_list):
    """DEPRECATED."""
    return helpers.list_to_lower(string_list)
