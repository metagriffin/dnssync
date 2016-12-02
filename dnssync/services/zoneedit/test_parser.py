# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2016/09/29
# copy: (C) Copyright 2016-EOT metagriffin -- see LICENSE.txt
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

  ASSET_DATA_DIR = 'dnssync:services/zoneedit/test_data/'

  #----------------------------------------------------------------------------
  def getData(self, name):
    return asset.load(self.ASSET_DATA_DIR + name).read()

  #----------------------------------------------------------------------------
  def test_extract_domains(self):
    html = self.getData('domains.html')
    self.assertEqual(
      parser.extract_domains(html),
      ['example.com', 'example2.com'])

  #----------------------------------------------------------------------------
  def test_extract_authdata(self):
    html = self.getData('authdata.html')
    self.assertEqual(
      parser.extract_authdata(html),
      dict(csrf_token='12345098734509876', login_chal='8983nhohtnthn789978'))

  #----------------------------------------------------------------------------
  def test_extract_records(self):
    html = self.getData('records.html')
    self.assertEqual(
      parser.extract_records(html),
      [
        # SOA
        {'rtype': 'SOA', 'EXPIRE AFTER': '1 week', 'DEFAULT TIME TO LIVE': '1 hour'},
        # NS
        {'rtype': 'NS', 'HOST': 'example.com', 'NAME SERVER(S)': 'LOCAL', 'TTL': 'default'},
        # MX
        {'rtype': 'MX', 'MAIL FOR ZONE': 'example.com', 'MAIL SERVER': 'mail.example.com',
         'PREF': '10', 'TTL': '14400'},
        # A
        {'rtype': 'A', 'HOST': 'example.com', 'IP ADDRESS': '1.2.3.4', 'TTL': '14400'},
        {'rtype': 'A', 'HOST': 'www.example.com', 'IP ADDRESS': '1.2.3.5', 'TTL': '600'},
        # AAAA
        {'rtype': 'AAAA', 'HOST': 'localhost.example.com', 'IPV6 ADDRESS': '::1', 'TTL': '14400'},
        # dynamic
        # TODO
        # {'rtype': 'dynamic', 'HOST': '??', 'CURRENT IP ADDRESS': '1.2.3.6', 'TTL': '??'},
        # CNAME
        {'rtype': 'CNAME', 'HOST': 'other1.example.com', 'ADDRESS': 'www.example.com', 'TTL': '14400'},
        {'rtype': 'CNAME', 'HOST': 'other2.example.com', 'ADDRESS': 'example.com', 'TTL': '600'},
        # SRV
        # TODO
        # {'rtype': 'SRV', 'SERVICE': '??', 'PROTO': '??', 'HOST': '??', 'PRI': '??', 'WGT': '??', 'PORT': '??', 'TARGET': '??', 'TTL': '??'},
        # TXT
        {'rtype': 'TXT', 'HOST': 'example.com', 'TEXT': 'v=spf1 a mx ~all', 'TTL': '14400'},
        # NAPTR
        # TODO
        # {'rtype': 'NAPTR', 'HOST': '??', 'ORDER': '??', 'PREF': '??', 'FLAGS': '??', 'SERVICENAME': '??', 'REGEX': '??', 'REPLACEMENT': '??', 'TTL': '??'},
      ])

  #----------------------------------------------------------------------------
  def test_extract_editparams(self):
    self.assertEqual(
      parser.extract_editparams(self.getData('edit-a.html')),
      {
        'MODE'                  : 'edit',
        'csrf_token'            : '1234567890',
        'next.x'                : '40',
        'next.y'                : '9',
        'A::0::host'            : '@',
        'A::0::ip'              : 'PARK',
        'A::0::ttl'             : '',
        'A::0::del'             : '1',
        'A::0::revoked'         : '0',
        'A::0::zone_id'         : '11409347',
        'A::1::host'            : 'localhost',
        'A::1::ip'              : '127.0.0.1',
        'A::1::ttl'             : '',
        'A::1::del'             : '1',
        'A::1::revoked'         : '0',
        'A::1::zone_id'         : '11410061',
      })
    self.assertEqual(
      parser.extract_editparams(self.getData('edit-soa.html')),
      {
        'MODE'                  : 'edit',
        'csrf_token'            : '1234567890',
        'next.x'                : '40',
        'next.y'                : '9',
        'SOA::refresh'          : '3600',
        'SOA::retry'            : '600',
        'SOA::expire'           : '604800',
        'SOA::ttl'              : '300',
      })
    self.assertEqual(
      parser.extract_editparams(self.getData('edit-srv.html')),
      {
        'MODE'                  : 'edit',
        'csrf_token'            : '1234567890',
        'next.x'                : '40',
        'next.y'                : '9',
      })

  #----------------------------------------------------------------------------
  def test_extract_confirmparams(self):
    self.assertEqual(
      parser.extract_editparams(self.getData('confirm-a.html')),
      {
        'csrf_token'            : '1234567890',
        'NEW_A'                 : '0987654321',
      })

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
