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

import socket
import logging

from aadict import aadict
import requests
import asset
import dns.resolver
from six.moves import StringIO
from six.moves.urllib import parse as urlparse
import morph

from dnssync import api
from dnssync.api.util import absdom, reldom
from dnssync.api.i18n import _

from . import parser

#----------------------------------------------------------------------------

log = logging.getLogger(__name__)

#------------------------------------------------------------------------------
def regGetSoaContent(name):
  try:
    sio = StringIO('nameserver ' + socket.gethostbyname('ns1.libyanspider.com.'))
    res = dns.resolver.Resolver(sio)
    ans = res.query(name, rdtype='SOA', rdclass='IN')
    return ans.response.answer[0].items[0].to_text()
  except dns.resolver.NoNameservers as err:
    # todo: perhaps return a bogus value? eg.:
    #   return 'ns1.libyanspider.com. support.libyanspider.com. 0 0 0 0 0'
    return None

#------------------------------------------------------------------------------
def reg2api(record, name):
  record = aadict(record)
  # reg: {'rid':'55026','zid':'4442','domainid':'12345','type':'A',
  #       'name':'fh3.example.ly','ttl':'14400','content':'10.11.12.237',}
  ret = api.Record(
    name    = absdom(record.name),
    rclass  = 'IN',
    ttl     = int(record.ttl),
    **morph.pick(record, 'rid', 'zid', 'domainid', 'type', 'content'))
  if ret.type not in api.Record.TYPES:
    raise api.DriverError(
      _('unknown/unexpected Registerly record type: "{}"', ret.type))
  if ret.type in (api.Record.TYPE_MX, api.Record.TYPE_CNAME, api.Record.TYPE_NS):
    ret.update(content = absdom(ret.content))
  if ret.type == api.Record.TYPE_SOA:
    # there's stuff missing!... content form should be:
    #   {root} {contact} {serial} {refresh} {retry} {expire} {minttl}
    # but is comming back as:
    #   ns1.libyanspider.com support.libyanspider.com 0
    # so fetching from DNS... ugh.
    return ret.update(content = regGetSoaContent(name))
  if ret.type == api.Record.TYPE_MX:
    return ret.update(priority = int(record.prio))
  if ret.type == api.Record.TYPE_CNAME:
    return ret.update(content = absdom(ret.content))
  # TODO: verify api.Record.TYPE_SRV...
  # TODO: verify api.Record.TYPE_NAPTR...
  # todo: Registerly also supports "PTR" and "URL" records... hm...
  return ret

#------------------------------------------------------------------------------
@asset.plugin('dnssync.services.plugins', 'registerly')
class Driver(api.Driver):

  name = 'registerly'

  BASEURL = 'https://my.register.ly'

  #----------------------------------------------------------------------------
  def __init__(self, *args, **kw):
    super(Driver, self).__init__(*args, **kw)
    for attr in ('username', 'password'):
      if not self.params.get(attr):
        raise api.ConfigurationError(_('required parameter "{}" missing', attr))
    self._session = None

  #----------------------------------------------------------------------------
  @property
  def session(self):
    if self._session is None:
      self._session = requests.Session()
      self._login()
    return self._session

  #----------------------------------------------------------------------------
  def urlget(self, url):
    res = self.session.get(self.BASEURL + url)
    res.raise_for_status()
    return res

  #----------------------------------------------------------------------------
  def urlpost(self, url, data):
    res = self.session.post(self.BASEURL + url, data=data)
    res.raise_for_status()
    return res

  #----------------------------------------------------------------------------
  def _login(self):
    resp = self._session.get(self.BASEURL + '/clientarea.php')
    data = aadict(parser.extract_authdata(resp.text)).update({
      'username'   : self.params.username,
      'password'   : self.params.password,
    })
    resp = self._session.post(
      self.BASEURL + '/dologin.php', allow_redirects=False, data=dict(data))
    if not resp.is_redirect \
        or resp.headers['location'] != '/clientarea.php':
      if 'incorrect' in resp.headers['location']:
        raise api.AuthenticationError(
          _('invalid Registerly account username and/or password'))
      raise api.AuthenticationError(
        _('unknown/unexpected login response'))

  #----------------------------------------------------------------------------
  def _zones(self):
    resp = self.urlget('/clientarea.php?action=domains')
    data = aadict(parser.extract_limitdata(resp.text)).update({
      'itemlimit' : 'all',
    })
    resp = self.urlpost('/clientarea.php?action=domains', dict(data))
    return {
      did : absdom(domain)
      for did, domain in parser.extract_domains(resp.text).items()}

  #----------------------------------------------------------------------------
  def list(self):
    return self._zones().values()

  #----------------------------------------------------------------------------
  def _getDomainID(self, name):
    for key, val in self._zones().items():
      if val == name:
        return key
    raise api.DomainNotFound(
      _('this Registerly account does not manage domain "{}"', name))

  #----------------------------------------------------------------------------
  def getRecords(self, name):
    name  = absdom(name)
    domid = self._getDomainID(name)
    resp  = self.urlget('/domaintools.php?domainid=' + domid)
    recs  = [reg2api(rec, name) for rec in parser.extract_records(resp.text)]
    for page in parser.extract_pages(resp.text):
      resp  = self.urlget('/domaintools.php?domainid=' + domid + '&start=' + str(page))
      recs  += [reg2api(rec, name) for rec in parser.extract_records(resp.text)]
    return recs

  #----------------------------------------------------------------------------
  def createRecord(self, context, record):
    soa = [r for r in context.records if r.type == api.Record.TYPE_SOA][0]
    params = urlparse.urlencode({
      'id'        : soa.zid,
      'domainid'  : soa.domainid,
      'ac'        : '3',      ## 3 == CREATE
    })
    resp  = self.urlget('/domaintools.php?' + params)
    token = parser.extract_formdata(resp.text)['token']
    data  = {
      'token'     : token,
      'domain'    : soa.zid,
      'name'      : reldom(record.name, to=context.name),
      'ttl'       : record.ttl,
      'type'      : record.type,
      'content'   : record.content,
      'commit'    : '',
    }
    if record.type in (api.Record.TYPE_MX, api.Record.TYPE_SRV):
      data['prio'] = record.priority
    resp = self.urlpost('/domaintools.php?' + params, data)

  #----------------------------------------------------------------------------
  def updateRecord(self, context, record, newrecord):
    # TODO: registerly supports BATCH UPDATES! USE THAT!
    params = urlparse.urlencode({
      'domain'    : record.zid,
      'domainid'  : record.domainid,
      'id'        : record.rid,
      'ac'        : '1',      ## 1 == UPDATE
    })
    resp  = self.urlget('/domaintools.php?' + params)
    token = parser.extract_formdata(resp.text)['token']
    data  = {
      'token'     : token,
      'zid'       : record.zid,
      'rid'       : record.rid,
      'name'      : reldom(record.name, to=context.name),
      'ttl'       : newrecord.ttl,
      'type'      : newrecord.type,
      'content'   : newrecord.content,
      'commit'    : '',
    }
    if record.type in (api.Record.TYPE_MX, api.Record.TYPE_SRV):
      data['prio'] = newrecord.priority
    resp = self.urlpost('/domaintools.php?' + params, data)

  #----------------------------------------------------------------------------
  def deleteRecord(self, context, record):
    params = urlparse.urlencode({
      'domain'    : record.zid,
      'domainid'  : record.domainid,
      'id'        : record.rid,
      'ac'        : '2',      ## 2 == DELETE
      'confirm'   : '1',
    })
    self.urlget('/domaintools.php?' + params)


#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
