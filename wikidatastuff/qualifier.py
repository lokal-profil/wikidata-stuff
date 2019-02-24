#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author: Lokal_Profil
# License: MIT
#
"""A class for encoding the contents of a qualifier."""
from __future__ import unicode_literals
from builtins import object

from wikidatastuff.helpers import std_p


class Qualifier(object):
    """
    A class for encoding the contents of a qualifier.

    Essentially pywikibot.Claim without having to provide an instantiated
    repo.

    @todo: redo as SimpleClaim (if so reuse in Reference) or
           retire in favor of pywikibot.Claim
    """

    def __init__(self, prop, itis):
        """
        Make a correctly formatted qualifier object for claims.

        @param prop: the property (with or without "P")
        @type prop: basestring
        @param itis: a valid claim target e.g. pywikibot.ItemPage
        @type itis: object
        """
        self.prop = std_p(prop)
        self.itis = itis

    def __repr__(self):
        """Return a more complete string representation."""
        return 'WD.Qualifier({0}, {1})'.format(self.prop, self.itis)

    def __eq__(self, other):
        """Implement equality comparison."""
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __ne__(self, other):
        """Implement non-equality comparison."""
        return not self.__eq__(other)

    def __hash__(self):
        """Implement hash to allow for e.g. sorting and sets."""
        return hash((self.prop, self.itis))
