#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Import and update test_data."""

from shutil import copyfile
import requests
import json
import codecs

# load new
#url = 'https://test.wikidata.org/wiki/Special:EntityData/Q27399.json'
url = 'https://test.wikidata.org/w/api.php?action=wbgetentities&format=json&ids=Q27399'
r = requests.get(url)
loaded_data = json.loads(r.text)

# back up original
filename = 'Q27399.json'
copyfile(filename, '%s.backup' % filename)

# output new
with codecs.open(filename, 'w', 'utf-8') as f:
    f.write(json.dumps(loaded_data, indent=4, ensure_ascii=False))
