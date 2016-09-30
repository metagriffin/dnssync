# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2016/09/28
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

import time
import hashlib
import socket

from aadict import aadict
import requests
import asset
import dns.resolver
from six.moves import StringIO

from dnssync import api
from dnssync.api.util import absdom, reldom
from dnssync.api.i18n import _
from dnssync.api.duration import asdur

from . import parser

#------------------------------------------------------------------------------
def md5(text):
  return hashlib.md5(text).hexdigest()

#------------------------------------------------------------------------------
def dur2sec(text):
  if text in (None, 'default'):
    return None
  try:
    return int(text)
  except ValueError:
    pass
  text = text.replace(' ', '')
  for lng in ('minute', 'hour', 'day', 'week'):
    text = text.replace(lng + 's', lng[0]).replace(lng, lng[0])
  return asdur(text)

#------------------------------------------------------------------------------
def zeGetSerial(name):
  sio = StringIO('nameserver ' + socket.gethostbyname('dns0.zoneedit.com.'))
  res = dns.resolver.Resolver(sio)
  ans = res.query(name, rdtype='SOA', rdclass='IN')
  return ans.response.answer[0].items[0].serial

#------------------------------------------------------------------------------
def ze2api(rawrec, name):
  ret = api.Record(name=name, rclass='IN', type=rawrec.rtype, ttl=dur2sec(rawrec.TTL))
  # TODO: handle type in 'dynamic', 'SRV', 'NAPTR'
  if rawrec.rtype == 'SOA':
    # {'rtype': 'SOA', 'Expire after': '1 week', 'Minimum time to live': '1 hour'}
    ret.update(
      ttl     = 3600,
      content = 'dns0.zoneedit.com. zone.zoneedit.com. {serial} {refresh} {retry} {expire} {minttl}'.format(
        serial  = zeGetSerial(name) or int(time.time()),
        refresh = 3600,
        retry   = 600,
        expire  = dur2sec(rawrec['Expire after']),
        minttl  = dur2sec(rawrec['Minimum time to live']),
      ))
    return [ret]
  if rawrec.rtype == 'NS':
    # {'rtype': 'NS', 'HOST': 'example.com', 'NAME SERVER(S)': 'LOCAL', 'TTL': 'default'}
    if rawrec['NAME SERVER(S)'] == 'LOCAL' and rawrec.TTL == 'default':
      return [
        api.Record(name=name, rclass='IN', type='NS', ttl=3600, content='dns1.zoneedit.com.'),
        api.Record(name=name, rclass='IN', type='NS', ttl=3600, content='dns2.zoneedit.com.'),
        api.Record(name=name, rclass='IN', type='NS', ttl=3600, content='dns3.zoneedit.com.'),
      ]
  if rawrec.rtype == 'MX':
    # {'rtype': 'MX', 'MAIL FOR ZONE': 'example.com', 'MAIL SERVER': 'mail.example.com',
    #  'PREF': '10', 'TTL': '14400'}
    return [ret.update(
      name     = absdom(rawrec['MAIL FOR ZONE']),
      priority = dur2sec(rawrec['PREF']),
      content  = absdom(rawrec['MAIL SERVER']),
    )]
  if rawrec.rtype == 'A':
    # {'rtype': 'A', 'HOST': 'example.com', 'IP ADDRESS': '1.2.3.4', 'TTL': '14400'}
    return [ret.update(name=absdom(rawrec['HOST']), content=rawrec['IP ADDRESS'])]
  if rawrec.rtype == 'AAAA':
    # {'rtype': 'AAAA', 'HOST': 'localhost.example.com', 'IPv6 ADDRESS': '::1', 'TTL': '14400'}
    return [ret.update(name=absdom(rawrec['HOST']), content=rawrec['IPv6 ADDRESS'])]
  if rawrec.rtype == 'CNAME':
    # {'rtype': 'CNAME', 'HOST': 'other2.example.com', 'ADDRESS': 'example.com', 'TTL': '600'}
    return [ret.update(name=absdom(rawrec['HOST']), content=absdom(rawrec['ADDRESS']))]
  if rawrec.rtype == 'TXT':
    # {'rtype': 'TXT', 'HOST': 'example.com', 'TEXT': 'v=spf1 a mx ~all', 'TTL': '14400'}
    return [ret.update(name=absdom(rawrec['HOST']), content=rawrec['TEXT'])]
  raise ValueError('unknown/unexpected/unimplemented ZoneEdit record type %r' % (rawrec.rtype,))

#------------------------------------------------------------------------------
@asset.plugin('dnssync.services.plugins', 'zoneedit')
class Driver(api.Driver):

  name = 'zoneedit'

  BASEURL = 'https://cp.zoneedit.com'

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
    resp = self._session.get(self.BASEURL + '/login.php')
    data = aadict(parser.extract_authdata(resp.text)).update({
      'login.x'      : '27',
      'login.y'      : '8',
      'login_user'   : self.params.username,
      'login_pass'   : self.params.password,
    })
    data.login_hash = md5(data.login_user + md5(data.login_pass) + data.login_chal)
    resp = self._session.post(
      self.BASEURL + '/home/', allow_redirects=False, data=dict(data))
    if not resp.is_redirect \
        or resp.headers['location'] != self.BASEURL + '/manage/domains/':
      if 'Invalid username-password combination' in resp.text:
        raise api.AuthenticationError(
          _('invalid ZoneEdit account username and/or password'))
      raise api.AuthenticationError(
        _('unknown/unexpected login response'))

  #----------------------------------------------------------------------------
  def _zones(self):
    resp = self.session.get(self.BASEURL + '/manage/domains/')
    return [absdom(name) for name in parser.extract_domains(resp.text)]

  #----------------------------------------------------------------------------
  def _switchToZone(self, name):
    if name not in self._zones():
      raise api.DomainNotFound(
        _('this ZoneEdit account does not manage domain "{}"', name))
    resp = self.session.get(
      self.BASEURL + '/manage/domains/zone/index.php',
      params=dict(LOGIN=reldom(name)))
    if not resp.status_code == 200 \
        or not resp.url.startswith(self.BASEURL + '/manage/domains/zone/index.php?'):
      raise api.DriverError(_('unknown/unexpected switch-zone response'))
    return resp.text

  #----------------------------------------------------------------------------
  def list(self):
    return self._zones()

  #----------------------------------------------------------------------------
  def getRecords(self, name):
    text = self._switchToZone(name)
    records = []
    for rawrec in parser.extract_records(text):
      records.extend(ze2api(rawrec, name))
    return records


#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
