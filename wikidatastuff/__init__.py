# -*- coding: utf-8 -*-
"""The initialization file for the WikidataStuff framework."""
#
# (C) Pywikibot team, 2008-2018
#
# Distributed under the terms of the MIT license.
#
from __future__ import unicode_literals

import pywikibot


# extend pywikibot.Claim with a __repr__ method
def new_repr(self):
    """Override the normal representation of pywikibot.Claim."""
    return 'WD.Claim({0}: {1})'.format(self.getID(), self.getTarget())


pywikibot.Claim.__repr__ = new_repr
