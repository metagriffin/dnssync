# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2015/01/04
# copy: (C) Copyright 2015-EOT metagriffin -- see LICENSE.txt
#------------------------------------------------------------------------------
# This software is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.
#------------------------------------------------------------------------------

import unittest
import six
import asset
import yaml

from . import parser

#------------------------------------------------------------------------------
class TestParser(unittest.TestCase):

  maxDiff = None

  ASSET_DATA_DIR = 'dnssync:domainmonster/test_data/'

  #----------------------------------------------------------------------------
  def getData(self, name):
    return asset.load(self.ASSET_DATA_DIR + name).read()

  #----------------------------------------------------------------------------
  def test_extractDnsRecords_01(self):
    html = self.getData('extract-dns-records-01.html')
    chk  = yaml.load(self.getData('extract-dns-records-01-output.yaml'))
    self.assertEqual(
      [r.toDict() for r in parser.extractDnsRecords(html)],
      chk)

  # TODO: replace `requests` library with a fake request/response re-enacter
  #       and test all of the `Driver.put` methods...

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
