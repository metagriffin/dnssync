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

import re

from aadict import aadict
from six.moves import html_parser

from dnssync import api

#------------------------------------------------------------------------------

_authdata_cre = re.compile(
  '<input\\s+[^>]*name="(csrf_token|login_chal)"\\s+value="([^"]*)"',
  flags=re.IGNORECASE)

_domains_cre = re.compile(
  re.escape('https://cp.zoneedit.com/manage/domains/zone/index.php?LOGIN=')
  # todo: i *could* use a better domain regex...
  + '([a-z0-9.-]+)',
  flags=re.IGNORECASE)

#------------------------------------------------------------------------------
class ScrapeError(api.DriverError): pass

#------------------------------------------------------------------------------
def extract_authdata(text):
  return {match.group(1): match.group(2)
          for match in _authdata_cre.finditer(text)}

#------------------------------------------------------------------------------
def extract_domains(text):
  return [match.group(1) for match in _domains_cre.finditer(text)]

#------------------------------------------------------------------------------
class MyRecordsParser(html_parser.HTMLParser):

  # TODO: wouldn't this be better executed via xpath?...

  def __init__(self, *args, **kw):
    html_parser.HTMLParser.__init__(self, *args, **kw)
    # super(MyRecordsParser, self).__init__(*args, **kw)
    self.records = []
    self.cursor  = []
    self.curdat  = aadict()

  def handle_starttag(self, tag, attrs):
    attrs = dict(attrs)
    if self.cursor == []:
      if tag == 'td' and attrs == dict(align='left', width='395'):
        self.cursor.append('section')
        self.curdat.clear()
        return
      if tag == 'tr' and attrs == dict(valign='baseline', bgcolor='#e7e7e7'):
        self.cursor.append('columns')
        self.curdat.columns = []
        return
      if tag == 'tr' and attrs == dict(valign='baseline'):
        self.cursor.append('record')
        self.curdat.record = []
        return
    if self.cursor == ['section']:
      if tag == 'font' and attrs == {'class': 'tableTitle1'}:
        self.cursor.append('title1')
        return
      if tag == 'font' and attrs == {'class': 'tableTitle2'}:
        self.cursor.append('title2')
        return
    if self.cursor == ['columns'] and tag == 'small':
      self.cursor.append('name')
      return
    if self.cursor == ['record'] and tag == 'td' and 'colspan' in attrs:
      self.cursor.append('no-value')
      return
    if self.cursor == ['record'] and tag == 'td' \
        and self.curdat.rtype == 'SOA' and attrs.get('align') == 'right':
      self.cursor.append('name')
      return
    if self.cursor == ['record'] and tag == 'td' \
        and self.curdat.rtype == 'A' and len(self.curdat.record) == 1:
      self.cursor.append('value')
      return
    if self.cursor == ['record'] and tag in ('b', 'i'):
      self.cursor.append('value')
      return

  def handle_data(self, data):
    if self.cursor in [
        ['section', 'title1'],
        ['section', 'title2'],
        ['columns', 'name'],
        ['record', 'name'],
        ['record', 'value'],
      ]:
      self.curdat.text = ( self.curdat.text or '' ) + data

  def handle_endtag(self, tag):
    if self.cursor == ['section'] and tag == 'td':
      self.cursor.pop()
      if not self.curdat.title1 or not self.curdat.title1.endswith(' records'):
        self.curdat.title1 = self.curdat.title2
      if self.curdat.title1 and self.curdat.title1.endswith(' records'):
        self.curdat.rtype = self.curdat.title1.rsplit(' ', 1)[0]
      del self.curdat.text
      del self.curdat.title1
      del self.curdat.title2
      return
    if self.cursor == ['section', 'title1'] and tag == 'font':
      self.curdat.title1 = self.curdat.text
      del self.curdat.text
      self.cursor.pop()
      return
    if self.cursor == ['section', 'title2'] and tag == 'font':
      self.curdat.title2 = self.curdat.text
      del self.curdat.text
      self.cursor.pop()
      return
    if self.cursor == ['columns'] and tag == 'tr':
      self.cursor.pop()
      return
    if self.cursor == ['columns', 'name'] and tag == 'small':
      self.cursor.pop()
      self.curdat.columns.append(self.curdat.text)
      del self.curdat.text
      return
    if self.cursor == ['record'] and tag == 'tr':
      self.cursor.pop()
      if self.curdat.rtype and self.curdat.record:
        rec = aadict(
          zip(self.curdat.columns, [r.strip() for r in self.curdat.record]),
          rtype=self.curdat.rtype)
        if rec.rtype == 'SOA' and self.records and self.records[-1].rtype == 'SOA':
          self.records[-1].update(rec)
        else:
          self.records.append(rec)
        del self.curdat.record
      return
    if ( self.cursor == ['record', 'value'] and tag in ('b', 'i') ) or \
          ( self.cursor == ['record', 'value'] and tag == 'td'
            and self.curdat.rtype == 'A' and len(self.curdat.record) == 1 ) or \
          ( self.cursor == ['record', 'name'] and tag == 'td'
            and self.curdat.rtype == 'SOA' ):
      if self.cursor == ['record', 'name']:
        self.curdat.columns = [self.curdat.text.strip().split(':', 1)[0]]
      else:
        self.curdat.record.append(self.curdat.text)
      self.cursor.pop()
      del self.curdat.text
      return
    if self.cursor == ['record', 'no-value'] and tag == 'td':
      self.cursor.pop()
      return

#------------------------------------------------------------------------------
def extract_records(text):
  parser = MyRecordsParser()
  parser.feed(text)
  return parser.records

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
