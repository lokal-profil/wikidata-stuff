#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Import and update test_data."""
from __future__ import unicode_literals
from builtins import open
from shutil import copyfile
import requests
import json

# load new
api_endpoint = 'https://test.wikidata.org/w/api.php?'
url = '%saction=wbgetentities&format=json&ids=Q27399' % api_endpoint
r = requests.get(url)
loaded_data = json.loads(r.text)

# back up original
filename = 'Q27399.json'
copyfile(filename, '%s.backup' % filename)

# output new
with open(filename, 'w', encoding='utf-8') as f:
    f.write(json.dumps(loaded_data, indent=4, ensure_ascii=False))
