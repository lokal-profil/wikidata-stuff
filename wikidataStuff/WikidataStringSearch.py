# -*- coding: utf-8 -*-
"""Database hookup for doing text string searches.

Must be run from labs and does these (SQL LIKE style) in
labels, aliases and descriptions of items.
"""
from __future__ import unicode_literals
from builtins import object
import MySQLdb

from pywikibot import output
import wikidataStuff.helpers as helpers


class WikidataStringSearch(object):
    """Run string searches on Wikidata from labs."""

    def __init__(self, verbose=False):
        """
        Set up connection and fetches allowed languages and types.

        @param verbose: if output (errors, queries) should be printed
            (default: False)
        @type verbose: bool
        """
        # Make one d/b connection for all queries - more efficient I believe
        self.conn = MySQLdb.connect(read_default_file="~/replica.my.cnf",
                                    host="wikidatawiki.labsdb",
                                    db="wikidatawiki_p",
                                    charset='utf8'
                                    )
        self.cursor = self.conn.cursor()
        self.term_types = ()
        self.languages = ()
        self.verbose = verbose

        # get types
        self.cursor.execute("SELECT DISTINCT term_type FROM wb_terms;")
        for row in self.cursor.fetchall():
            self.term_types += WikidataStringSearch._type_fixed_row(row)
        self._print('found %d term_types' % len(self.term_types))

        # get languages
        self.cursor.execute("SELECT DISTINCT term_language FROM wb_terms;")
        for row in self.cursor.fetchall():
            self.languages += WikidataStringSearch._type_fixed_row(row)
        self._print('found %d languages' % len(self.languages))

    def close_connection(self):
        """Close database connection."""
        self.conn.close()

    def testInput(self, text, language=None, term_type=None, entities=None):
        """
        Test that the user input is valid.

        @param text: the text to search for
        @type text: basestring
        @param language: the language to search in, defaults to None=any
        @type language: basestring or None
        @param entities: the language to search in, defaults to None=any
        @type entities: list (of basestring), or None
        @param term_type: field to search in, defaults
            to None=['label', 'alias']
        @type term_type: basestring or None
        @return: if input is valid
        @rtype: bool
        """
        # test text
        if not text.strip():
            self._print('You cannot send stringSearch an empty string')
            return False

        # test language
        if language and language not in self.languages:
            self._print('%s is not a recognised language' % language)
            return False

        # test term_type
        if term_type and term_type not in self.term_types:
            self._print('%s is not a recognised term_type' % term_type)
            return False

        # test list of entities
        if entities:
            if not isinstance(entities, (tuple, list)):
                self._print('Entities must be a non-zero list')
                return False

            # Check each is correctly formatted
            if not all(e.startswith('Q') and
                       helpers.is_str(e) and
                       WikidataStringSearch.is_int(e[1:])
                       for e in entities):
                self._print('Each entity must be a string like Q<integer>')
                return False

        # nothing flagged
        return True

    def search(self, text, language='sv', term_type=None):
        """
        Search for a given string in a specified language and field.

        Deprecated.
        Calls basic_search with entities=None and language defaulting to 'sv'
        """
        return self.basic_search(text,
                                 language=language,
                                 entities=None,
                                 term_type=term_type)

    def searchInEntities(self, text, entities, language='sv', term_type=None):
        """
        search() but limit results to a provided list of entities.

        Deprecated.
        Calls basic_search with language defaulting to 'sv'
        """
        return self.basic_search(text,
                                 language=language,
                                 entities=entities,
                                 term_type=term_type)

    def basic_search(self, text, language=None, entities=None, term_type=None):
        """
        Search for a given string through exact match or SQL like wild-cards.

        Results can be limited to a specific language, a certain field or
        to within a list of entities.

        @param text: the text to search for
        @type text: basestring
        @param language: the language to search in, defaults to None=any
        @type language: basestring or None
        @param entities: the language to search in, defaults to None=any
        @type entities: list (of basestring), or None
        @param term_type: field to search in, defaults
            to None=['label', 'alias']
        @type term_type: basestring or None
        @return: list of matching Q values
        @rtype: list (of str)
        """
        # validate input
        if not self.testInput(text, language, term_type, entities):
            return None

        # set default term_type
        if term_type is None:
            term_type = ['label', 'alias']
        else:
            term_type = [term_type, ]

        # prepare entities by converting to a list of int strings
        if entities:
            tmp = []
            for e in entities:
                tmp.append(int(e[1:]))
            entities = tmp

        # construct query
        params = []
        query = "SELECT CONCAT('Q',term_entity_id), term_text, term_type " \
                "FROM wb_terms " \
                "WHERE term_entity_type='item' "
        params += term_type
        query += "AND term_type IN %s " % \
                 WikidataStringSearch.sql_in_format(term_type)
        if language:
            params.append(language)
            query += "AND term_language=%s "
        if entities:
            params += entities
            query += "AND term_entity_id IN %s " % \
                     WikidataStringSearch.sql_in_format(entities)
        params.append(text)
        query += "AND term_text LIKE %s " \
                 "LIMIT 100;"

        # execute query
        self.cursor.execute(query, tuple(params))
        self._print(self.cursor._last_executed)

        # handle response
        qs = []
        for q, t, tt in self.cursor.fetchall():
            qs.append(q)

        return qs

    def _print(self, s):
        """
        Output text if verbose.

        @param s: text to output
        @type s: basestring
        """
        if self.verbose:
            output(s)

    @staticmethod
    def _type_fixed_row(row):
        """Ensure byte strings are converted to str, unicode as appropriate."""
        return tuple([el.decode('utf-8') if isinstance(el, bytes) else el for el in row])

    @staticmethod
    def sql_in_format(l):
        """
        Given a list of parameters output an sql compatible list of args.

        @param l: value to test
        @type l: list or tuple
        @return: sql compatible list of args
        @rtype: string
        """
        string_format = ', '.join(['%s'] * len(l))
        return '(%s)' % string_format

    @staticmethod
    def is_int(s):
        """
        Check if value is an int.

        @param s: value to test
        @type s: any
        @return: if value can be interpreted as an integer
        @rtype: bool
        """
        try:
            int(s)
            return True
        except (ValueError, TypeError):
            return False
