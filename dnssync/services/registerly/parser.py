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

from six.moves.urllib.parse import parse_qsl
from aadict import aadict
import bs4

from dnssync import api

#------------------------------------------------------------------------------
class ScrapeError(api.DriverError): pass

#------------------------------------------------------------------------------
def extract_authdata(text):
  data = dict()
  soup = bs4.BeautifulSoup(text, 'html.parser')
  for record in soup.select('input'):
    if record['name'] != 'rememberme':
      data[record['name']] = record.get('value')
  return data

#------------------------------------------------------------------------------
def extract_domains(text):
  doms = dict()
  soup = bs4.BeautifulSoup(text, 'html.parser')
  for record in soup.select('tbody tr'):
    doms[record.select('input[type=checkbox]')[0]['value']] = \
      record.select('a[target=_blank]')[0].string
  return doms

#------------------------------------------------------------------------------
def _extract_formdata(form):
  data = dict()
  for record in form.select('input'):
    data[record['name']] = record.get('value')
  for record in form.select('select'):
    data[record['name']] = record.select('option[selected]')[0]['value']
  return data

#------------------------------------------------------------------------------
def extract_limitdata(text):
  data = dict()
  soup = bs4.BeautifulSoup(text, 'html.parser')
  for form in soup.select('form'):
    if form.get('class') or form.get('id'):
      continue
    data.update(_extract_formdata(form))
  return data

#------------------------------------------------------------------------------
def extract_records(text):
  soup = bs4.BeautifulSoup(text, 'html.parser')
  recs = []
  form = soup.select('form.client-form')[0]
  data = _extract_formdata(form)
  for key,val in data.items():
    if not key.endswith('[rid]'):
      continue
    rid = val
    rec = dict(rid=rid, domainid=str(data['domainid']))
    for key,val in data.items():
      if not key.startswith('record[' + rid + ']['):
        continue
      rec[str(key.split('][', 1)[1].split(']', 1)[0])] = str(val).strip()
    recs.append(rec)
  if not recs:
    raise ScrapeError(_(
      'no records found... hm... seems registerly changed their DOM structure. SORRY!'))
  for rec in form.select('tbody tr'):
    if rec.select('td:nth-of-type(3)')[0].string == 'SOA':
      udat = dict(parse_qsl(rec.select('a')[0]['href'].split('?', 1)[1]))
      recs.append(dict(
        rid       = udat['id'],
        zid       = udat['domain'],
        domainid  = udat['domainid'],
        type      = 'SOA',
        name      = str(rec.select('td:nth-of-type(2)')[0].string),
        content   = str(rec.select('td:nth-of-type(4)')[0].string),
        ttl       = str(rec.select('td:nth-of-type(6)')[0].string),
      ))
  return recs

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
