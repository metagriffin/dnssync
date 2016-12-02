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
import bs4

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
  # todo: use bs4...
  return {match.group(1): match.group(2)
          for match in _authdata_cre.finditer(text)}

#------------------------------------------------------------------------------
def extract_domains(text):
  # todo: use bs4...
  return [match.group(1) for match in _domains_cre.finditer(text)]

#------------------------------------------------------------------------------
def extract_records(text):
  soup = bs4.BeautifulSoup(text, 'html.parser')
  records = []
  for section in soup.select('.tableStart'):
    rtype = section.select('.tableTitle2, .tableTitle1')[0].string
    if not rtype or rtype.string in (
        'subdomains', 'dynamic records', 'URL forwarding', 'stealth forwarding'):
      continue
    rtype = str(rtype.split()[0]).upper()
    if rtype == 'SOA':
      section = section.find('tr', valign='top')
      cols = [
        str(el.string).strip().split(':')[0].upper()
        for el in section.find_all('td', align='right')]
      cells = [str(el.string).strip() for el in section.find_all('b')]
      rec = aadict(zip(cols, cells), rtype=rtype)
      records.append(rec)
      continue
    if rtype in ('NS', 'MX', 'A', 'AAAA', 'CNAME', 'SRV', 'TXT', 'NAPTR'):
      cols = [
        str(el.string).strip().upper()
        for el in section.find('tr', valign='top').find_all('small')]
      rows = list(section.find_all('tr', valign='baseline', bgcolor=None))
      for record in rows:
        cells = [str(el.string).strip() for el in record.find_all(['b', 'i'])]
        if len(cells) == 1 and len(rows) == 1 and len(cols) != 1:
          # todo: double check that it says something linke:
          #         "No {RECTYPE} records defined for {DOMAIN}."
          continue
        if rtype == 'A':
          cells.insert(1, str(record.select('td:nth-of-type(2)')[0].string).strip())
        if len(cols) != len(cells):
          raise ScrapeError(
            _('fields did not match columns for "{}" record type', rtype))
        rec = aadict(zip(cols, cells), rtype=rtype)
        records.append(rec)
      continue
    raise ScrapeError(_('unknown record type: "{}"', rtype))
  return records

#------------------------------------------------------------------------------
def extract_editparams(text):
  soup = bs4.BeautifulSoup(text, 'html5lib')
  params = {}
  for tag in soup.find_all('input'):
    if tag['name'] == 'next':
      params['next.x'] = '40'
      params['next.y'] = '9'
      continue
    if tag['name'] == 'confirm':
      continue
    if '::' not in tag['name']:
      params[str(tag['name'])] = str(tag['value'])
      continue
    if tag.get('value') is None:
      continue
    params[str(tag['name'])] = str(tag['value'])
  for tag in soup.find_all('select'):
    opt = tag.select('option[selected]')
    if opt:
      params[str(tag['name'])] = str(opt[0]['value'])
  return params

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
