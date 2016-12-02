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
import logging

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

#----------------------------------------------------------------------------

log = logging.getLogger(__name__)

#------------------------------------------------------------------------------
def md5(text):
  return hashlib.md5(text).hexdigest()

#------------------------------------------------------------------------------
def dur2sec(text):
  if text in (None, '', 'default'):
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
  try:
    sio = StringIO('nameserver ' + socket.gethostbyname('dns0.zoneedit.com.'))
    res = dns.resolver.Resolver(sio)
    ans = res.query(name, rdtype='SOA', rdclass='IN')
    return ans.response.answer[0].items[0].serial
  except dns.resolver.NoNameservers:
    return None

#------------------------------------------------------------------------------
# ZoneEdit record attributes:
#   standard records:
#     SOA     refresh, retry, expire, ttl
#     NS      host, ttl, server
#     MX      host, ttl, pref, server
#     A       host, ttl, ip, revoked
#     IPV6    host, ttl, ip
#       NOTE: the standard rdtype for zoneedit's "IPV6" is "AAAA"
#     CNAME   host, ttl, alias
#     TXT     host, ttl, txt
#    *SRV     host, ttl, port, pri, service, proto, targ, weight
#    *NAPTR   host, ttl, flags, order, preference, regex, replacement, service
#   non-standard records:
#    *DYN     host, ttl, ip
#    *URL     host, ttl, prio, url
#    *STEALTH host, ttl, url
#   some existing records also have (at least NS, MX, A, CNAME):
#     zone_id, del, revoked
#
#   * == currently not supported (TODO)
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def ze2api(record, name):
  if not record.host or record.host == '@':
    record.host = absdom(name)
  else:
    record.host = absdom(record.host + '.' + name)
  ret = api.Record(
    name=record.host, rclass='IN', type=record.rtype, ttl=dur2sec(record.ttl))
  if record.zone_id:
    ret.zoneedit_id = record.zone_id
  if record.rtype == api.Record.TYPE_SOA:
    return ret.update(
      ttl     = 3600,
      content = 'dns0.zoneedit.com. zone.zoneedit.com. {serial} {refresh} {retry} {expire} {minttl}'.format(
        serial  = zeGetSerial(name) or int(time.time()),
        refresh = dur2sec(record.refresh),
        retry   = dur2sec(record.retry),
        expire  = dur2sec(record.expire),
        minttl  = dur2sec(record.ttl),
      ))
  if record.rtype == api.Record.TYPE_NS:
    if record.server == 'LOCAL':
      record.server = 'local.zoneedit.'
    return ret.update(content=record.server)
  if record.rtype == api.Record.TYPE_MX:
    if record.server == 'LOCAL':
      record.server = 'local.zoneedit.'
    return ret.update(priority=dur2sec(record.pref), content=absdom(record.server))
  if record.rtype == api.Record.TYPE_A:
    if record.ip == 'PARK':
      record.ip = '0.0.0.0'
    return ret.update(content=record.ip)
  if record.rtype == api.Record.TYPE_AAAA:
    if record.ip == 'PARK':
      record.ip = '::0'
    return ret.update(content=record.ip)
  if record.rtype == api.Record.TYPE_CNAME:
    return ret.update(content=absdom(record.alias))
  if record.rtype == api.Record.TYPE_TXT:
    return ret.update(content=record.txt)
  raise ValueError(
    _('unknown/unexpected/unimplemented ZoneEdit record type "{}"', record.rtype))

#------------------------------------------------------------------------------
def api2ze(record, name):
  ret = aadict(host=record.name, ttl=str(record.ttl))
  if ret.host == name:
    ret.host = '@'
  elif ret.host.endswith('.' + name):
    ret.host = ret.host[:- len(name) - 1]
  if record.type == api.Record.TYPE_SOA:
    return aadict(
      zip(['refresh', 'retry', 'expire', 'ttl'], record.content.split()[-4:]))
  if record.type == api.Record.TYPE_NS:
    ret.update(server=record.content)
    if ret.server == 'local.zoneedit.':
      ret.server = 'LOCAL'
    return ret
  if record.type == api.Record.TYPE_MX:
    ret.update(server=record.content, pref=record.priority)
    if ret.server == 'local.zoneedit.':
      ret.server = 'LOCAL'
    return ret
  if record.type in (api.Record.TYPE_A, api.Record.TYPE_AAAA):
    ret.update(ip=record.content)
    if ret.ip == '0.0.0.0':
      ret.ip = 'PARK'
    return ret
  if record.type == api.Record.TYPE_CNAME:
    return ret.update(alias=record.content)
  if record.type == api.Record.TYPE_TXT:
    return ret.update(txt=record.content)
  raise ValueError(
    _('unknown/unexpected/unimplemented ZoneEdit record type "{}"', record.type))

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
    for rtype in api.Record.TYPES:
      records += self.getRecordsByType(name, rtype)
    soa = [r for r in records if r.type == api.Record.TYPE_SOA][0]
    for record in records:
      if record.type != api.Record.TYPE_SOA and record.ttl is None:
        record.ttl = int(soa.content.split()[-1])
    return records

  #----------------------------------------------------------------------------
  def _getTypePath(self, rtype):
    path = rtype.lower()
    if path == 'aaaa':
      path = 'ipv6'
    return self.BASEURL + '/manage/domains/' + path

  #----------------------------------------------------------------------------
  def getRecordsByType(self, name, rtype):
    resp = self.session.get(self._getTypePath(rtype) + '/edit.php')
    resp.raise_for_status()
    params = parser.extract_editparams(resp.text)
    recs = {}
    for key, val in params.items():
      if '::' not in key:
        continue
      if rtype == api.Record.TYPE_SOA:
        ktyp, kname = key.split('::', 1)
        kidx = '0'
      else:
        ktyp, kidx, kname = key.split('::', 2)
      if kidx not in recs:
        recs[kidx] = aadict(rtype=rtype)
      recs[kidx][kname] = val
    return [ze2api(rec, name) for rec in recs.values()]

  #----------------------------------------------------------------------------
  def putChangesByType(self, context, rtype, creates, updates, deletes):
    resp = self.session.get(self._getTypePath(rtype) + '/edit.php')
    resp.raise_for_status()
    params = {k: v
              for k, v in parser.extract_editparams(resp.text).items()
              if '::' not in k}
    recidx = 0
    pfx = rtype if rtype != api.Record.TYPE_AAAA else 'IPV6'
    for record in context.records:
      if record.type != rtype:
        continue
      if rtype == api.Record.TYPE_SOA:
        rpfx = pfx + '::'
      else:
        rpfx = pfx + '::' + str(recidx) + '::'
        recidx += 1
      zerec = api2ze(record, context.name)
      for key, val in zerec.items():
        params[rpfx + key] = str(val)
      if getattr(record, 'zoneedit_id', None) is not None:
        params[rpfx + 'zone_id'] = record.zoneedit_id
        params[rpfx + 'revoked'] = '0'
      if record in deletes:
        log.info('deleting %s record: %s (%s)', record.type, record.name, record.content)
        params[rpfx + 'del'] = '1'
      elif record in updates:
        newrecord = updates[record]
        log.info('updating %s record: %s (%s)', record.type, record.name, newrecord.content)
        newzerec = api2ze(newrecord, context.name)
        for key, val in newzerec.items():
          params[rpfx + key] = str(val)
    for record in creates:
      log.info('creating %s record: %s (%s)', record.type, record.name, record.content)
      zerec = api2ze(record, context.name)
      rpfx = pfx + '::' + str(recidx) + '::'
      recidx += 1
      for key, val in zerec.items():
        params[rpfx + key] = str(val)
    # todo: i should prolly just go straight for the generation of "NEW_A"... eg:
    #   NEW_A = a%3A2%3A%7Bs%3A1%3A%22%40%22%3Ba%3A1%3A%7Bi%3A0%3Ba%3A6%3A%7Bs%3A5%3A%22rdata%22%3Bs%3A4%3A%22PARK%22%3Bs%3A3%3A%22ttl%22%3Bi%3A300%3Bs%3A7%3A%22zone_id%22%3Bs%3A8%3A%2211409347%22%3Bs%3A10%3A%22geozone_id%22%3Bi%3A0%3Bs%3A7%3A%22revoked%22%3Bi%3A0%3Bs%3A3%3A%22del%22%3Bi%3A1%3B%7D%7Ds%3A2%3A%22lh%22%3Ba%3A1%3A%7Bi%3A0%3Ba%3A6%3A%7Bs%3A5%3A%22rdata%22%3Bs%3A9%3A%22166.1.1.1%22%3Bs%3A10%3A%22geozone_id%22%3Bi%3A0%3Bs%3A3%3A%22ttl%22%3Bi%3A300%3Bs%3A7%3A%22zone_id%22%3Bi%3A0%3Bs%3A7%3A%22revoked%22%3Bi%3A0%3Bs%3A4%3A%22hash%22%3Bs%3A32%3A%228d3a99930022b801814734c79721367d%22%3B%7D%7D%7D
    #   == a:2:{
    #        s:1:"@";
    #        a:1:{
    #          i:0;
    #          a:6:{
    #            s:5:"rdata";
    #            s:4:"PARK";
    #            s:3:"ttl";
    #            i:300;
    #            s:7:"zone_id";
    #            s:8:"11409347";
    #            s:10:"geozone_id";
    #            i:0;
    #            s:7:"revoked";
    #            i:0;
    #            s:3:"del";
    #            i:1;
    #          }
    #        }
    #        s:2:"lh";
    #        a:1:{
    #          i:0;
    #          a:6:{
    #            s:5:"rdata";
    #            s:9:"166.1.1.1";
    #            s:10:"geozone_id";
    #            i:0;
    #            s:3:"ttl";
    #            i:300;
    #            s:7:"zone_id";
    #            i:0;
    #            s:7:"revoked";
    #            i:0;
    #            s:4:"hash";
    #            s:32:"8d3a99930022b801814734c79721367d";
    #          }
    #        }
    #      }
    resp = self.session.post(self._getTypePath(rtype) + '/edit.php', data=params)
    resp.raise_for_status()
    params = parser.extract_editparams(resp.text)
    resp = self.session.post(self._getTypePath(rtype) + '/confirm.php', data=params)
    resp.raise_for_status()
    return


#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
