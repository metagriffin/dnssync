# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2015/01/03
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

import re
from aadict import aadict
import HTMLParser

from dnssync import api
from dnssync.api.util import absdom

#------------------------------------------------------------------------------

class HtmlScrapingError(api.DriverError): pass

origin_cre  = re.compile(r'>([^ ]+) Control Panel<', re.IGNORECASE)
section_cre = re.compile(r'<div[^>]*?\s+id="rec([A-Z]+)"')
record_cre  = {
  '*'       : re.compile(
    '''
      <tr>.*?
      <td\s+class="host">(?P<name>[^<]*)</td>.*?
      <input.*?\s+id="dns_content_(?P<id>\d+)"\s+value="(?P<content>[^"]+)"
    ''',
    re.VERBOSE | re.IGNORECASE | re.DOTALL),
  'MX'       : re.compile(
    '''
      <tr>.*?
      <td\s+class="host">(?P<name>[^<]*)</td>.*?
      <input.*?\s+id="dns_content_(?P<id>\d+)"\s+value="(?P<content>[^"]+)".*?
      <option\s+value="(?P<priority>\d+)"\s+selected>
    ''',
    re.VERBOSE | re.IGNORECASE | re.DOTALL),
  'SRV'      : re.compile(
    '''
      <tr>.*?
      <td\s+class="host">(?P<name>[^<]*)</td>.*?
      <input.*?\s+id="dns_content_(?P<id>\d+)"\s+value="(?P<content>[^"]+)".*?
      <option\s+value="(?P<priority>\d+)"\s+selected>.*?
      <option\s+value="(?P<weight>\d+)"\s+selected>.*?
      <input.*?\s+id="dns_port_(?P=id)"\s+value="(?P<port>[^"]+)"
    ''',
    re.VERBOSE | re.IGNORECASE | re.DOTALL),
}
error_cre   = re.compile(r'>error:\s+([^<]+)<', re.IGNORECASE)

#------------------------------------------------------------------------------
def extractDnsRecords(html):
  records  = []
  origin   = absdom(origin_cre.search(html).group(1))
  sections = section_cre.split(html)[1:]
  sections = [(sections[idx*2], sections[idx*2+1]) for idx in range(len(sections) / 2)]
  if len(sections) != 7:
    raise HtmlScrapingError(
      'unexpected number of record type sections (%r instead of 7)' % (len(sections),))
  for rdtype, section in sections:
    cre = record_cre.get(rdtype) or record_cre.get('*')
    for match in cre.finditer(section):
      rec = api.Record(
        id      = match.group('id'),
        name    = match.group('name') + '.' + origin if match.group('name') else origin,
        type    = rdtype,
        content = match.group('content'),
      )
      if len(match.groups()) > 3:
        rec.priority = int(match.group('priority'))
      if len(match.groups()) > 5:
        rec.weight   = int(match.group('weight'))
        rec.port     = int(match.group('port'))
      records.append(rec)
  return records

#------------------------------------------------------------------------------
def htmlUnescape(html):
  return HTMLParser.HTMLParser().unescape(html)

#------------------------------------------------------------------------------
def evaluateResponse(html):
  match = error_cre.search(html)
  if not match:
    return aadict(code=200)
  return aadict(code=400, message=htmlUnescape(match.group(1)))


#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
