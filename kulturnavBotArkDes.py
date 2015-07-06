#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about Architects in KulturNav.

usage:
    python kulturnavBotArkDes.py [OPTIONS]

Author: Lokal_Profil
License: MIT

Options (may be omitted):
  -cutoff:INT       number of entries to process before terminating
  -maxHits:INT      number of items to request at a time from Kulturnav
                    (default 250)
"""
import pywikibot
from kulturnavBot import KulturnavBot

# KulturNav based
EDIT_SUMMARY = 'KulturnavBot'
DATASET_ID = '2b7670e1-b44e-4064-817d-27834b03067c'
ENTITY_TYPE = 'Person'
MAP_TAG = 'entity.sameAs_s'
DATASET_Q = '17373699'


class KulturnavBotArkDes(KulturnavBot):
    """
    A bot to enrich and create information on Wikidata based on KulturNav info
    """
    ARCHITECT_Q = '42973'

    def run(self, cutoff=None):
        """
        Starts the robot
        param cutoff: if present limits the number of records added in one go
        """
        count = 0
        for architect in self.generator:
            # print count, cutoff
            if cutoff and count >= cutoff:
                break
            # Valuesworth searching for
            values = {# u'deathPlace': None,
                      u'deathDate': None,
                      # u'birthPlace': None,
                      u'birthDate': None,
                      u'firstName': None,
                      u'gender': None,
                      u'lastName': None,
                      u'name': None,
                      u'identifier': None,
                      u'modified': None,
                      u'seeAlso': None,
                      u'sameAs': None,
                      # not expected
                      u'wikidata': None,
                      u'libris-id': None}

            # populate values
            problemFree = True
            for entries in architect[u'@graph']:
                for k, v in entries.iteritems():
                    if k in values.keys():
                        if values[k] is None:
                            values[k] = v
                        else:
                            pywikibot.output(u'duplicate entries for %s' % k)
                            problemFree = False

            # dig into sameAs and seeAlso
            # each can be either a list or a str/unicode
            if isinstance(values[u'sameAs'], (str, unicode)):
                values[u'sameAs'] = [values[u'sameAs'], ]
            if values[u'sameAs'] is not None:
                for sa in values[u'sameAs']:
                    if u'wikidata' in sa:
                        values[u'wikidata'] = sa.split('/')[-1]
                    elif u'libris.kb.se/auth/' in sa:
                        values[u'libris-id'] = sa.split('/')[-1]
            # we only care about seeAlso if we didn't find a Wikidata link
            if values[u'wikidata'] is None:
                if isinstance(values[u'seeAlso'], (str, unicode)):
                    values[u'seeAlso'] = [values[u'seeAlso'], ]
                for sa in values[u'seeAlso']:
                    if u'wikipedia' in sa:
                        pywikibot.output(u'Found a Wikipedia link but no '
                                         u'Wikidata link: %s %s' %
                                         (sa, values[u'identifier']))
                problemFree = False

            if not problemFree:
                # continue with next architect
                pywikibot.output(u'Found an issue with %s (%s), skipping' %
                                 (values['identifier'], values['wikidata']))
                continue

            # for k, v in values.iteritems(): print k, ' : ', v

            # convert these to potential claims
            protoclaims = {
                u'P31': pywikibot.ItemPage(self.repo, u'Q5'),
                u'P106': pywikibot.ItemPage(
                    self.repo,
                    u'Q%s' % self.ARCHITECT_Q),
                u'P20': None,
                u'P570': None,
                u'P19': None,
                u'P569': None,
                u'P735': None,
                u'P21': None,
                u'P734': None,
                # u'P1477': None,
                u'P1248': None,
                u'P906': None}

            # if values[u'deathPlace']:
            #    protoclaims[u'P20'] = self.dbpedia2Wikidata(values[u'deathPlace'])
            if values[u'deathDate']:
                protoclaims[u'P570'] = self.dbDate(values[u'deathDate'])
            # if values[u'birthPlace']:
            #    protoclaims[u'P19'] = self.dbpedia2Wikidata(values[u'birthPlace'])
            if values[u'birthDate']:
                protoclaims[u'P569'] = self.dbDate(values[u'birthDate'])
            if values[u'firstName']:
                protoclaims[u'P735'] = self.dbName(values[u'firstName'],
                                                   u'firstName')
            if values[u'gender']:
                protoclaims[u'P21'] = self.dbGender(values[u'gender'])
            if values[u'lastName']:
                protoclaims[u'P734'] = self.dbName(values[u'lastName'],
                                                   u'lastName')
            if values[u'libris-id']:
                protoclaims[u'P906'] = values[u'libris-id']
            if values[u'identifier']:
                protoclaims[u'P%s' % self.KULTURNAV_ID_P] = values[u'identifier']

            # print values[u'wikidata']
            # for k, v in protoclaims.iteritems(): print k, ' : ', v

            # get the "last modified" timestamp
            date = self.dbDate(values[u'modified'])

            # find the matching wikidata item
            # check Wikidata first, then kulturNav
            architectItem = None
            if values[u'identifier'] in self.itemIds:
                architectItemTitle = u'Q%s' % \
                    (self.itemIds.get(values[u'identifier']),)
                if values[u'wikidata'] != architectItemTitle:
                    # this may be caused by either being a redirect
                    wd = pywikibot.ItemPage(self.repo, values[u'wikidata'])
                    wi = pywikibot.ItemPage(self.repo, architectItemTitle)
                    if wd.isRedirectPage() and wd.getRedirectTarget() == wi:
                        pass
                    elif wi.isRedirectPage() and wi.getRedirectTarget() == wd:
                        pass
                    else:
                        pywikibot.output(
                            u'Identifier missmatch (skipping): '
                            u'%s, %s, %s' % (values[u'identifier'],
                                             values[u'wikidata'],
                                             architectItemTitle))
                        continue
            else:
                architectItemTitle = values[u'wikidata']

            # create ItemPage, bypassing any redirect
            architectItem = self.bypassRedirect(
                pywikibot.ItemPage(
                    self.repo,
                    architectItemTitle))
            # in case of redirect
            architectItemTitle = architectItem.title()
            values[u'wikidata'] = architectItem.title()

            # Add information if a match was found
            if architectItem and architectItem.exists():

                # make sure it is not matched to a group of people
                if self.hasClaim('P%s' % self.IS_A_P,
                                 pywikibot.ItemPage(self.repo, u'Q16334295'),
                                 architectItem):
                    pywikibot.output(u'%s is matched to a group of people, '
                                     u'FIXIT' % values[u'wikidata'])
                    continue

                # add name as label/alias
                # since order is last, first create a local rearranged copy
                if values[u'name']:
                    hitlist = []
                    if isinstance(values[u'name'], dict):
                        s = KulturnavBotArkDes.shuffleNames(values[u'name'])
                        if s is not None:
                            hitlist.append(s)
                    elif isinstance(values[u'name'], list):
                        for n in values[u'name']:
                            s = KulturnavBotArkDes.shuffleNames(n)
                            if s is not None:
                                hitlist.append(s)
                    else:
                        pywikibot.output(u'unexpectedly formatted name'
                                         u'object: %s' % values[u'name'])
                    if len(hitlist) > 0:
                        self.addLabelOrAlias(hitlist, architectItem)

                # add each property (if new) and source it
                for pcprop, pcvalue in protoclaims.iteritems():
                    if pcvalue:
                        if isinstance(pcvalue, unicode) and \
                                pcvalue in (u'somevalue', u'novalue'):
                            # special cases
                            self.addNewSpecialClaim(pcprop, pcvalue,
                                                    architectItem, date)
                        elif pcprop == u'P%s' % self.KULTURNAV_ID_P:
                            qual = {
                                u'prop': u'P%s' % self.CATALOG_P,
                                u'itis': pywikibot.ItemPage(
                                    self.repo,
                                    u'Q%s' % self.DATASET_Q),
                                u'force': True}
                            self.addNewClaim(pcprop, pcvalue, architectItem,
                                             date, qual=qual)
                        else:
                            self.addNewClaim(pcprop, pcvalue,
                                             architectItem, date)
            # allow for limited runs
            count += 1

        # done
        pywikibot.output(u'Went over %d entries' % count)

    @classmethod
    def main(cls, *args):
        cls.setVariables(
            dataset_q=DATASET_Q,
            dataset_id=DATASET_ID,
            entity_type=ENTITY_TYPE,
            map_tag=MAP_TAG,
            edit_summary=EDIT_SUMMARY
        )
        super(KulturnavBotArkDes, cls).main(*args)


if __name__ == "__main__":
    KulturnavBotArkDes.main()
