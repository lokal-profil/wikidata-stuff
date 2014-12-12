#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
A database hookup (to be run from labs) for doing text string searches
(SQL LIKE style) in lables, aliases and descriptions of items

TODO:   Throw errors from inputTest
        Wrap executes in try to deal with fails
"""
import MySQLdb


class WikidataStringSearch:
    def __init__(self, verbose=False):
        """
        Sets up connection and fetches allowed languages and types
        param verbose: outputs queries if true (default: False)
        """
        # Make one d/b connection for all queries - more efficient I believe
        self.conn = MySQLdb.connect(read_default_file="~/replica.my.cnf",
                                    host="wikidatawiki.labsdb",
                                    db="wikidatawiki_p",
                                    )
        self.cursor = self.conn.cursor()
        self.term_types = ()
        self.languages = ()
        self.verbose = verbose

        # get types
        self.cursor.execute("SELECT DISTINCT term_type FROM wb_terms;")
        for t in self.cursor.fetchall():
            self.term_types += t
        if self.verbose:
            print 'found %d term_types' % len(self.term_types)

        # get languages
        self.cursor.execute("SELECT DISTINCT term_language FROM wb_terms;")
        for l in self.cursor.fetchall():
            self.languages += l
        if self.verbose:
            print 'found %d languages' % len(self.languages)

    def close_connection(self):
        self.conn.close()

    def testInput(self, text, language, term_type=None, entities=None):
        """
        Test that the user input makes sense
        """
        # test text
        if len(text.strip()) == 0:
            print 'You cannot send stringSearch an empty string'
            return False

        # test lanugage
        if language not in self.languages:
            print '%s is not a recognised language' % language
            return False

        # test term_type
        if term_type:
            if term_type not in self.term_types:
                print '%s is not a recognised term_type' % term_type
                return False

        # test list of entities
        if entities:
            if not isinstance(entities, (tuple, list)) or len(entities) == 0:
                print 'Entities must be a non-zero list'
                return False

            # Check each is correctly formated
            if not all(e.startswith('Q') and
                       isinstance(e, (str, unicode)) and
                       WikidataStringSearch.is_int(e[1:])
                       for e in entities):
                print 'Each entity must be a string like Q<integer>'
                return False

        # nothing flagged
        return True

    def searchGenerator(self, text, language='sv', term_type=None):
        for q in self.search(text, language=language, term_type=term_type):
            yield q

    def search(self, text, language='sv', term_type=None):
        """
        Search for a given
        term_type defaults to ('label', 'alias')
        """
        if not self.testInput(text,
                              language,
                              term_type=term_type):
            return None

        # set default term_type
        if term_type is None:
            term_type = ('label', 'alias')
        else:
            term_type = (term_type, )

        # construct and execute query
        query = """#==Search on string in a given language==
SELECT CONCAT('Q',term_entity_id), term_text, term_type FROM wb_terms
WHERE term_entity_type='item' AND term_type IN ('%s') AND term_language=%%s
AND term_text LIKE %%s
LIMIT 100;""" % "', '".join(term_type)
        self.cursor.execute(query, (language, text))
        if self.verbose:
            print self.cursor._last_executed

        qs = []
        for q, t, tt in self.cursor.fetchall():
            qs.append(q)

        return qs

    def searchInEntities(self, text, entities, language='sv', term_type=None):
        """
        As above but limit results to a set list of entitites
        term_type defaults to ('label', 'alias')
        """
        if not self.testInput(text,
                              language,
                              term_type=term_type,
                              entities=entities):
            return None

        # set default term_type
        if term_type is None:
            term_type = ('label', 'alias')
        else:
            term_type = (term_type, )

        # convert to a list of int strings
        tmp = []
        for e in entities:
            tmp.append(int(e[1:]))
        entities = tmp

        # construct and execute query
        query = """#==Search on string in a given language==
SELECT CONCAT('Q',term_entity_id), term_text, term_type FROM wb_terms
WHERE term_entity_type='item' AND term_type IN ('%s') AND term_language=%%s
AND term_entity_id IN %%s
AND term_text LIKE %%s
LIMIT 100;""" % "', '".join(term_type)
        self.cursor.execute(query, (language, entities, text))
        if self.verbose:
            print self.cursor._last_executed

        qs = []
        for q, t, tt in self.cursor.fetchall():
            qs.append(q)

        return qs

    @staticmethod
    def is_int(s):
        try:
            int(s)
            return True
        except (ValueError, TypeError):
            return False
