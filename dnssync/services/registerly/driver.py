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
  if ret.type == api.Record.TYPE_SOA:
    # there's stuff missing!... content form should be:
    #   {root} {contact} {serial} {refresh} {retry} {expire} {minttl}
    # but is comming back as:
    #   ns1.libyanspider.com support.libyanspider.com 0
    # so fetching from DNS... ugh.
    return ret.update(content = regGetSoaContent(name))
  if ret.type == api.Record.TYPE_MX:
    return ret.update(priority = record.prio, content = absdom(ret.content))
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
    resp = self.session.get(self.BASEURL + '/clientarea.php?action=domains')
    data = aadict(parser.extract_limitdata(resp.text)).update({
      'itemlimit' : 'all',
    })
    resp = self.session.post(
      self.BASEURL + '/clientarea.php?action=domains', data=dict(data))
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
    resp  = self.session.get(self.BASEURL + '/domaintools.php?domainid=' + domid)
    return [reg2api(rec, name) for rec in parser.extract_records(resp.text)]


#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
