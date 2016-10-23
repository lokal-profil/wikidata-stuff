#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about River Basin Districts.

Author: Lokal_Profil
License: MIT

@todo: Follow up creation by ensuring that each CA has the corresponding RBD
    as it's P2541

usage:
    python WFD/RBD.py [OPTIONS]

&params;
"""
from WikidataStuff import WikidataStuff as WD
import pywikibot
import wdqsLookup
import helpers

parameter_help = u"""\
RBDbot options (may be omitted):
-new               if present new items are created on Wikidata, otherwise
                   only updates are processed.
-in_file           path to the data file
-mappings          path to the mappings file (if not "mappings.json")
-cutoff            number items to process before stopping (if not then all)

Can also handle any pywikibot options. Most importantly:
-simulate          don't write to database
-dir               directory in which user_config is located
-help              output all available options
"""
docuReplacements = {'&params;': parameter_help}
EDIT_SUMMARY = u'import using #WFDdata'


class RBD():
    """Bot to enrich/create info on Wikidata for RBD objects."""

    def __init__(self, mappings, new=False, cutoff=None):
        self.repo = pywikibot.Site().data_repository()
        self.wd = WD(self.repo, EDIT_SUMMARY)
        self.new = new
        self.cutoff = cutoff

        self.dataset_q = 'Q27074294'
        self.rbd_q = 'Q132017'
        self.eu_rbd_p = 'P2965'
        self.area_unit = 'http://www.wikidata.org/entity/Q712226'
        self.area_error = 1  # until I figure something better out

        self.langs = ('en', 'sv')  # languages for which we require translations
        self.countries = mappings['countryCode']
        self.competent_authorities = mappings['CompetentAuthority']
        self.descriptions = mappings['descriptions']
        self.rbd_id_items = self.load_existing_rbd()

    def load_existing_rbd(self):
        """Load existing RBD items and check all have unique ids."""
        item_ids = wdqsLookup.make_claim_wdqs_search(
            'P31', q_value=self.rbd_q, optional_props=[self.eu_rbd_p, ])

        # invert and check existence and uniqueness
        rbd_id_items = {}
        for q_id, values in item_ids.iteritems():
            eu_rbd_code = values.get(self.eu_rbd_p)
            if not eu_rbd_code:
                raise pywikibot.Error(
                    'Found an RBD without euRBDCode: %s' % q_id)
            elif eu_rbd_code in rbd_id_items.keys():
                raise pywikibot.Error(
                    'Found an two RBDs with same euRBDCode: %s & %s' % (
                        q_id, rbd_id_items[eu_rbd_code]))
            rbd_id_items[eu_rbd_code] = q_id
        return rbd_id_items

    def check_all_descriptions(self):
        """Check that the description are available for all langauges."""
        diff_national = set(self.langs) - \
            set(self.descriptions.get('national').keys())
        diff_international = set(self.langs) - \
            set(self.descriptions.get('international').keys())
        diff = diff_national.union(diff_international)

        if diff:
            raise pywikibot.Error(
                "The following languages need a description: %s" %
                ', '.join(diff))

    def check_all_competent_authorities(self, data, country):
        """Check that all competent authorities are mapped.

        :param data: dict of all the rbds in the country with euRBDCode as keys
        :param country: name of the country
        """
        found_ca = []
        for d in data:
            found_ca.append(d['primeCompetentAuthority'])

        diff = set(found_ca)-set(self.competent_authorities.keys())
        if diff:
            country_en = self.countries.get(country).get('en')
            raise pywikibot.Error("The following competent authroities should "
                                  "be created before processing %s: %s"
                                  % (country_en, ', '.join(diff)))

    def check_country(self, country):
        """Check that the country is mapped and that languages are available.

        :param country: name of the country
        """
        country_data = self.countries.get(country)
        if not country_data:
            raise pywikibot.Error("The country code \"%s\" was not mapped."
                                  % country)
        if not country_data.get('qId'):
            raise pywikibot.Error("The country code \"%s\" was not mapped "
                                  "to Wikidata." % country)

        diff = set(self.langs)-set(country_data.keys())
        if diff:
            raise pywikibot.Error("The following languages should be mapped "
                                  "for country %s before continuing: %s"
                                  % (country, ', '.join(diff)))

    def process_country_rbd(self, country, data, reference=None):
        """Handle the RBDs of a single country.

        :param country: the country code as a string
        :param data: dict of all the rbds in the country with euRBDCode as keys
        :param reference: WD.Reference object to be associated to all claims
        """
        # check if CA in self.competent_authorities else raise error
        self.check_country(country)
        self.check_all_competent_authorities(data, country)

        # identify euRBDCode and check if it is in self.rbd_id_items
        count = 0
        for entry_data in data:
            if self.cutoff and count >= self.cutoff:
                break
            rbd_code = entry_data.get('euRBDCode')
            item = None
            if rbd_code in self.rbd_id_items.keys():
                item = self.wd.QtoItemPage(self.rbd_id_items[rbd_code])
            elif self.new:
                item = self.create_new_rbd_item(entry_data, country)
            else:
                # skip non existant if not self.new
                continue
            item.exists()

            labels = self.make_labels(entry_data, with_alias=True)
            protoclaims = self.make_protoclaims(
                entry_data, self.countries.get(country).get('qId'))
            self.commit_labels(labels, item)
            self.commit_claims(protoclaims, item, reference)

            # increment counter
            count += 1

    def create_new_rbd_item(self, entry_data, country):
        """Make a new rbd item.

        :param entry_data: dict with the data for the rbd
        :param country: country code
        """
        data = {
            'labels': {},
            'descriptions': {}}

        data['labels'] = self.make_labels(entry_data)
        data['descriptions'] = self.make_descriptions(entry_data, country)

        # print data
        # create new empty item and request Q-number
        summary = u'Creating new RBD item with #WFDdata'
        item = None
        try:
            item = self.wd.make_new_item(data, summary)
        except pywikibot.data.api.APIError, e:
            raise pywikibot.Error(u'Error during item creation: %s' % e)

        return item

    def make_labels(self, entry_data, with_alias=False):
        """Make a label object from the available info.

        rbdName always gives the english names.
        internationalRBDName is sometimes in english, sometimes NULL and
        sometimes a comment.

        The output is a dict with lang as key and a dict as value where that
        dict in turn has a language and a value key. Both of these have string
        values. Unless with_alias is provided.

        @todo Figure out how to handle internationalRBDName (which can be in
              other languages, or a duplicate, or different english).

        :param entry_data: dict with the data for the rbd
        :param with_alias: change the value to a list of all allowed labels.
        """
        labels = {}
        labels['en'] = {'language': 'en', 'value': entry_data.get('rbdName')}

        if with_alias:
            labels['en']['value'] = [labels.get('en').get('value'),
                                     entry_data.get('euRBDCode')]
        return labels

    def make_descriptions(self, entry_data, country):
        """Make a description object from the available info.

        @todo lookup country name through country mappings.
              but store so that only one lookup (per language) is needed
        :param entry_data: dict with the data for the rbd
        :param country: country code
        """
        description_type = self.descriptions.get('national')
        if entry_data.get('internationalRBD') == 'Yes':
            description_type = self.descriptions.get('international')

        descriptions = {}
        for lang in self.langs:
            desc = description_type.get(lang) % self.countries.get(country).get(lang)
            descriptions[lang] = {'language': lang, 'value': desc}
        return descriptions

    def make_protoclaims(self, entry_data, country_q):
        """Construct potential claims for an entry.

        Expects that entry_data is a dict like:
        {
            "euRBDCode": "SE5101",
            "internationalRBD": "Yes",
            "internationalRBDName": "5. Skagerrak and Kattegat (International drainage basin Glomma - Sweden)",
            "primeCompetentAuthority": "SE5",
            "otherCompetentAuthority": "SEHAV",
            "rbdArea": "990",
            "rbdAreaExclCW": "Data is missing",
            "rbdName": "5. Skagerrak and Kattegat (International drainage basin Glomma - Sweden)",
            "subUnitsDefined": "No"
        }

        :param entry_data: dict with the data for the rbd per above
        :param country_q: q_id for the coutnry
        """
        protoclaims = {}
        #   P31: self.rbd_q
        protoclaims[u'P31'] = WD.Statement(
            self.wd.QtoItemPage(self.rbd_q))
        #   self.eu_rbd_p: euRBDCode
        protoclaims[self.eu_rbd_p] = WD.Statement(
            entry_data[u'euRBDCode'])
        #   P17: country (via self.countries)
        protoclaims[u'P17'] = WD.Statement(
            self.wd.QtoItemPage(country_q))
        #   P137: primeCompetentAuthority (via self.competent_authorities)
        protoclaims[u'P137'] = WD.Statement(
            self.wd.QtoItemPage(
                self.competent_authorities[
                    entry_data[u'primeCompetentAuthority']]))
        #   P2046: rbdArea + self.area_unit (can I set unknown accuracy)
        protoclaims[u'P2046'] = WD.Statement(
            pywikibot.WbQuantity(entry_data[u'rbdArea'],
                                 error=self.area_error,
                                 entity=self.area_unit))
        return protoclaims

    def commit_labels(self, labels, item):
        """Add labels and aliases to item."""
        if not labels:
            return
        for lang, data in labels.iteritems():
            values = helpers.listify(data['value'])
            for value in values:
                self.wd.addLabelOrAlias(lang, value, item,
                                        caseSensitive=False)

    def commit_claims(self, protoclaims, item, ref):
        """
        Add each claim (if new) and source it.

        :param protoclaims: a dict of claims with
            key: Prop number
            val: Statement|list of Statements
        :param item: the target entity
        :param ref: WD.Reference
        """
        for pc_prop, pc_value in protoclaims.iteritems():
            if pc_value:
                if isinstance(pc_value, list):
                    pc_value = set(pc_value)  # eliminate potential duplicates
                    for val in pc_value:
                        # check if None or a Statement(None)
                        if (val is not None) and (not val.isNone()):
                            self.wd.addNewClaim(
                                pc_prop, val, item, ref)
                            # reload item so that next call is aware of changes
                            item = self.wd.QtoItemPage(item.title())
                            item.exists()
                elif not pc_value.isNone():
                    self.wd.addNewClaim(
                        pc_prop, pc_value, item, ref)

    def process_all_rbd(self, data):
        """Handle every single RBD in a datafile.

        @todo: Adapt to multi country data
        """
        # Check that all descriptions are present
        self.check_all_descriptions()

        # Make a Reference (or possibly one per country)
        ref = self.make_ref(data)

        # Find the country code in mappings (skip if not found)
        country = data.get('countryCode')
        #language = data.get('@language') # per schema "Code of the language of the file" but it isn't

        # Send rbd data for the country onwards
        self.process_country_rbd(
            country, helpers.listify(data.get('RBD')), ref)

    def make_ref(self, data):
        """Make a Reference object for the dataset.

        Contains 4 parts:
        * P248: Stated in <the WFD2016 dataset>
        * P577: Publication date <from creation date of the document>
        * P854: Reference url <using the input url>
        * P813: Retrieval date <current date>
        """
        creation_date = helpers.iso_to_WbTime(data['@creationDate'])
        ref = WD.Reference(
            source_test=[
                self.wd.make_simple_claim(
                    'P248',
                    self.wd.QtoItemPage(self.dataset_q)),
                self.wd.make_simple_claim(
                    'P854',
                    data['source_url'])],
            source_notest=[
                self.wd.make_simple_claim(
                    'P577',
                    creation_date),
                self.wd.make_simple_claim(
                    'P813',
                    helpers.today_as_WbTime())
            ]
        )
        return ref

    @staticmethod
    def load_xml_url_data(url):
        """Load the data from an url to an xml file.

        @todo: dump to a local json file (if wanted)
        """
        import requests
        import xmltodict
        import datetime
        r = requests.get(url)
        data = xmltodict.parse(
            r.text.encode(r.encoding),
            encoding='utf-8').get('RBDSUCA')
        data['source_url'] = url
        data['retrieval_date'] = datetime.date.today().isoformat()
        return data

    @staticmethod
    def load_data(in_file):
        """Load the data from the in_file.

        Needs to be adapted if the fileformat changes
        """
        if in_file.partition('://')[0] in ('http', 'https'):
            return RBD.load_xml_url_data(in_file)
        return helpers.load_json_file(in_file)

    @staticmethod
    def main(*args):
        """Command line entry point."""
        mappings = 'mappings.json'
        force_path = __file__
        in_file = None
        new = False
        cutoff = None

        # Load pywikibot args and handle local args
        for arg in pywikibot.handle_args(args):
            option, sep, value = arg.partition(':')
            if option == '-in_file':
                in_file = value
            elif option == '-mappings':
                mappings = value
                force_path = None
            elif option == '-new':
                new = True
            elif option == '-cutoff':
                cutoff = int(value)

        # require in_file
        if not in_file:
            raise pywikibot.Error('An in_file must be specified')

        # load mappings and initialise RBD object
        mappings = helpers.load_json_file(mappings, force_path)
        data = RBD.load_data(in_file)
        rbd = RBD(mappings, new=new, cutoff=cutoff)

        rbd.process_all_rbd(data)

if __name__ == "__main__":
    RBD.main()
