#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author: Lokal_Profil
# License: MIT
#
"""A class for encoding the contents of a reference."""
from __future__ import unicode_literals
from builtins import object

import pywikibot

import wikidatastuff.helpers as helpers


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
        self.source_test = helpers.listify(source_test)
        self.source_notest = helpers.listify(source_notest)

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
        return 'WD.Reference(test: {0}, no_test: {1})'.format(
            self.source_test, self.source_notest)
