#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author: Lokal_Profil
# License: MIT
#
"""A representation of a statement (value, qualifiers, references)."""
from __future__ import unicode_literals
from builtins import object

import pywikibot
from pywikibot.tools import deprecated, deprecated_args

import wikidataStuff.helpers as helpers
from wikidataStuff.reference import Reference
from wikidataStuff.qualifier import Qualifier


class Statement(object):
    """A representation of a statement (value, qualifiers, references)."""

    def __init__(self, itis, special=False):
        """
        Make a correctly formatted statement object for claims.

        @todo: itis test

        @param itis: a valid claim target e.g. pywikibot.ItemPage
        @type itis: object
        @param special: if itis is actually a snakvalue
        @type special: bool
        """
        if special and itis not in ['somevalue', 'novalue']:
            raise pywikibot.Error(
                'You tried to create a special statement with a '
                'non-allowed snakvalue: %s' % itis)
        self.itis = itis
        self._quals = set()
        self.ref = None
        self.special = special
        self.force = False

    @deprecated('addQualifier', since='0.4')
    def add_qualifier(self, qual, force=False):
        """
        Add qualifier to the statement if not None or already present.

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
        elif not isinstance(qual, Qualifier):
            raise pywikibot.Error(
                'add_qualifier was called with something other '
                'than a Qualifier|None object: %s' % qual)

        # register qualifier
        self._quals.add(qual)
        if force:
            self.force = True
        return self

    def add_reference(self, ref):
        """
        Add a Reference to the statement.

        Returns self to allow chaining.

        @param ref: the reference to add
        @type ref: Reference
        @raises: pywikibot Error if a reference is already present or if
            the provided value is not a Reference.
        """
        # test input
        if self.ref is not None:
            raise pywikibot.Error(
                'add_reference was called when the statement already had '
                'a reference assigned to it.')
        elif not isinstance(ref, Reference):
            raise pywikibot.Error(
                'add_reference was called with something other '
                'than a Reference object: %s' % ref)
        else:
            self.ref = ref

        return self

    @deprecated('isNone', since='0.4')
    def is_none(self):
        """Test if Statement was created with itis=None."""
        return self.itis is None

    @property
    def quals(self):
        """Return the list of qualifiers."""
        return list(self._quals)

    def __repr__(self):
        """Return a more complete string representation."""
        return ('WD.Statement('
                'itis:{}, quals:{}, ref:{}, special:{}, force:{})'.format(
                    self.itis, self.quals, self.ref, self.special,
                    self.force))

    def __eq__(self, other):
        """Two Statements are equal if same up to qualifier order."""
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __hash__(self):
        """Implement hash to allow for e.g. sorting and sets."""
        return hash((self.itis, frozenset(self._quals), self.ref,
                     self.special, self.force))

    def __ne__(self, other):
        """Implement non-equality comparison."""
        return not self.__eq__(other)


@deprecated('wikidataStuff.helpers.add_start_end_qualifiers', since='0.4')
@deprecated_args(startVal='start_val', endVal='end_val', since='0.4')
def add_start_end_qualifiers(statement, start_val, end_val):
    """
    Add start/end qualifiers to a statement if non-None, or return None.

    @param statement: The statement to decorate
    @type statement: Statement
    @param start_val: An ISO date string for the starting point
    @type start_val: basestring or None
    @param end_val: An ISO date string for the end point
    @type end_val: basestring or None
    @return: A statement decorated with start/end qualifiers
    @rtype: Statement, or None
    """
    if not isinstance(statement, Statement):
        raise pywikibot.Error('Non-statement recieved: %s' % statement)
    if statement.is_none():
        return None

    # add qualifiers
    quals = []
    if start_val:
        quals.append(
            Qualifier(
                P=helpers.START_P,
                itis=helpers.iso_to_WbTime(start_val)))
    if end_val:
        quals.append(
            Qualifier(
                P=helpers.END_P,
                itis=helpers.iso_to_WbTime(end_val)))
    for q in quals:
        statement.add_qualifier(q)
    return statement
