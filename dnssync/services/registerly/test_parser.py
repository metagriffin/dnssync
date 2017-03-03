# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2017/01/06
# copy: (C) Copyright 2017-EOT metagriffin -- see LICENSE.txt
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

  ASSET_DATA_DIR = 'dnssync:services/registerly/test_data/'

  #----------------------------------------------------------------------------
  def getData(self, name):
    return asset.load(self.ASSET_DATA_DIR + name).read()

  #----------------------------------------------------------------------------
  def test_extract_authdata(self):
    html = self.getData('login-form.html')
    self.assertEqual(
      parser.extract_authdata(html),
      dict(
        username = '',
        password = None,
        token    = '8c0a9ce1aa8e4a62b7bf450118fe9c8218fe9c82'))

  #----------------------------------------------------------------------------
  def test_extract_domains(self):
    html = self.getData('domains.html')
    self.assertEqual(
      parser.extract_domains(html),
      {'1234': 'example.ly', '1235': 'example2.ly'})

  #----------------------------------------------------------------------------
  def test_extract_limitdata(self):
    html = self.getData('domains.html')
    self.assertEqual(
      parser.extract_limitdata(html),
      {'token': 'TOKLIMIT', 'itemlimit': '10'})

  #----------------------------------------------------------------------------
  def test_extract_records(self):
    html = self.getData('records.html')
    self.assertEqual(
      sorted(parser.extract_records(html), key=lambda r: r['rid']),
      sorted([
        {'rid': 'IDA', 'zid': '4442', 'domainid': '12345', 'type': 'SOA',     'name': 'example.ly',             'ttl': '0',     'content': 'ns1.libyanspider.com support.libyanspider.com 0', },
        {'rid': 'IDB', 'zid': '4442', 'domainid': '12345', 'type': 'CNAME',   'name': '*.example.ly',           'ttl': '0',     'content': 'example.ly',                                      },
        {'rid': 'IDC', 'zid': '4442', 'domainid': '12345', 'type': 'A',       'name': 'example.ly',             'ttl': '0',     'content': '10.11.12.199',                                    },
        {'rid': 'IDD', 'zid': '4442', 'domainid': '12345', 'type': 'MX',      'name': 'example.ly',             'ttl': '14400', 'content': 'mail.example.ly.',       'prio': '10',            },
        {'rid': 'IDE', 'zid': '4442', 'domainid': '12345', 'type': 'CNAME',   'name': 'imap.example.ly',        'ttl': '14400', 'content': 'fh1.example.ly.',                                 },
        {'rid': 'IDF', 'zid': '4442', 'domainid': '12345', 'type': 'CNAME',   'name': 'smtp.example.ly',        'ttl': '14400', 'content': 'fh1.example.ly.',                                 },
        {'rid': 'IDG', 'zid': '4442', 'domainid': '12345', 'type': 'A',       'name': 'mail.example.ly',        'ttl': '14400', 'content': '10.11.12.247',                                    },
        {'rid': 'IDH', 'zid': '4442', 'domainid': '12345', 'type': 'NS',      'name': 'example.ly',             'ttl': '0',     'content': 'ns1.libyanspider.com',                            },
        {'rid': 'IDI', 'zid': '4442', 'domainid': '12345', 'type': 'NS',      'name': 'example.ly',             'ttl': '0',     'content': 'ns2.libyanspider.com',                            },
        {'rid': 'IDJ', 'zid': '4442', 'domainid': '12345', 'type': 'NS',      'name': 'example.ly',             'ttl': '0',     'content': 'ns3.libyanspider.com',                            },
        {'rid': 'IDK', 'zid': '4442', 'domainid': '12345', 'type': 'NS',      'name': 'example.ly',             'ttl': '0',     'content': 'ns4.libyanspider.com',                            },
        {'rid': 'IDL', 'zid': '4442', 'domainid': '12345', 'type': 'NS',      'name': 'example.ly',             'ttl': '0',     'content': 'ns5.libyanspider.com',                            },
        {'rid': 'IDM', 'zid': '4442', 'domainid': '12345', 'type': 'NS',      'name': 'example.ly',             'ttl': '0',     'content': 'ns6.libyanspider.com',                            },
        {'rid': 'IDN', 'zid': '4442', 'domainid': '12345', 'type': 'A',       'name': 'fh1.example.ly',         'ttl': '14400', 'content': '10.11.12.134',                                    },
        {'rid': 'IDO', 'zid': '4442', 'domainid': '12345', 'type': 'A',       'name': 'fh2.example.ly',         'ttl': '14400', 'content': '10.11.12.199',                                    },
        {'rid': 'IDP', 'zid': '4442', 'domainid': '12345', 'type': 'A',       'name': 'fh3.example.ly',         'ttl': '14400', 'content': '10.11.12.237',                                    },
        {'rid': 'IDQ', 'zid': '4442', 'domainid': '12345', 'type': 'CNAME',   'name': 'demo.example.ly',        'ttl': '14400', 'content': 'prod.example.ly.',                                },
        {'rid': 'IDR', 'zid': '4442', 'domainid': '12345', 'type': 'CNAME',   'name': 'chat.example.ly',        'ttl': '14400', 'content': 'fh1.example.ly.',                                 },
        {'rid': 'IDS', 'zid': '4442', 'domainid': '12345', 'type': 'A',       'name': 'localhost.example.ly',   'ttl': '14400', 'content': '127.0.0.1',                                       },
        {'rid': 'IDT', 'zid': '4442', 'domainid': '12345', 'type': 'AAAA',    'name': 'localhost.example.ly',   'ttl': '14400', 'content': '::1',                                             },
        {'rid': 'IDU', 'zid': '4442', 'domainid': '12345', 'type': 'TXT',     'name': 'example.ly',             'ttl': '14400', 'content': 'v=spf1 a mx -all',                                },
      ], key=lambda r: r['rid']))

  #----------------------------------------------------------------------------
  def test_extract_pages(self):
    html = self.getData('records.html')
    self.assertEqual(parser.extract_pages(html), [2, 3])


#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
