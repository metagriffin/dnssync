# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2015/01/02
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

# TODO: the NS records can actually be fetched from the Name Server section...
#       (instead of being faked, as here)

import logging
import dns.rdata
import dns.zone
from aadict import aadict
import requests
import time
from six.moves.urllib import parse as urlparse

from dnssync import api
from dnssync.api.util import absdom, reldom
from dnssync.api.i18n import _

from . import parser

#------------------------------------------------------------------------------

log = logging.getLogger(__name__)

#------------------------------------------------------------------------------
class Driver(api.Driver):

  name = 'domainmonster'

  BASEURL = 'https://www.domainmonster.com'

  #----------------------------------------------------------------------------
  def __init__(self, *args, **kw):
    super(Driver, self).__init__(*args, **kw)
    for attr in ('username', 'password'):
      if not self.params.get(attr):
        raise api.ConfigurationError(_('required parameter "{}" missing', attr))
    self.session = requests.Session()
    resp = self.session.post(
      self.BASEURL + '/login/',
      data = {
        'action'   : 'dologin',
        'username' : self.params.username,
        'password' : self.params.password,
      })
    # todo: check response...

  #----------------------------------------------------------------------------
  def _zones(self):
    resp = self.session.get(self.BASEURL + '/members/domainlist/js/')
    return dict((absdom(zname), int(zid))
                for zid, zname in
                [zone.split(':', 1) for zone in resp.text.split('|')])

  #----------------------------------------------------------------------------
  def _switchToZone(self, name):
    zones = self._zones()
    if name not in zones:
      raise api.DomainNotFound(name)
    zid = zones[name]
    resp = self.session.post(self.BASEURL + '/members/manage/', data=dict(
      setdm    = '1',
      d        = zid,
      frompop  = '0',
      gons     = '0',
      goar     = '0',
      golk     = '0',
      gopr     = '0',
    ))
    # todo: check response...
    return zid

  #----------------------------------------------------------------------------
  def list(self):
    return self._zones().keys()

  #----------------------------------------------------------------------------
  def _makeSerial(self, prev=None):
    if not prev:
      return time.strftime('%Y%m%d01')
    new = int(self._makeSerial())
    cur = int(prev)
    if new > cur:
      return str(new)
    return str(cur + 1)

  #----------------------------------------------------------------------------
  def getRecords(self, name):
    zid     = self._switchToZone(name)
    resp    = self.session.get(self.BASEURL + '/members/managedns/')
    records = parser.extractDnsRecords(resp.text)
    serial  = self._makeSerial()

    for record in records:
      # todo: unfortunately, the TTL and RDCLASS fields need to be faked...
      record.ttl     = 14400
      record.rclass  = 'IN'
      # making use of the work-around record...
      if record.type == 'TXT' and record.name == '_dnssync.' + name:
        serial = dict(urlparse.parse_qsl(record.content)).get('s', serial)

    # todo: unfortunately, the SOA and NS records need to be faked...
    records = [
      api.Record(
        name=name, ttl=14400, rclass='IN', type='SOA', 
        content='ns1.domainmonster.com. hostmaster.' + name
                + ' ' + serial + ' 7200 1800 1209600 7200'
      ),
      api.Record(name=name, ttl=14400, rclass='IN', type='NS', content='ns1.domainmonster.com.'),
      api.Record(name=name, ttl=14400, rclass='IN', type='NS', content='ns2.domainmonster.com.'),
      api.Record(name=name, ttl=14400, rclass='IN', type='NS', content='ns3.domainmonster.com.'),
    ] + records

    return records

  #----------------------------------------------------------------------------
  def _bumpSerial(self, record):
    if not record:
      data = dict(s=self._makeSerial())
    else:
      data = dict(urlparse.parse_qsl(record.content))
      data['s'] = self._makeSerial(data.get('s'))
    return urlparse.urlencode(data)

  #----------------------------------------------------------------------------
  def makePutContext(self, name, zone):
    ret = super(Driver, self).makePutContext(name, zone)
    ret.zoneid = self._switchToZone(name)
    for record in ret.newrecords:
      if record.rclass != 'IN':
        raise api.UnsupportedRecordType(
          _('DomainMonster does not support non-"IN" record classes: {!r}',
            (record,)))
      if record.ttl != 14400:
        raise api.UnsupportedRecordType(
          _('DomainMonster does not support non-4 hour TTLs: {!r}',
            (record,)))
    # update the faked serial-tracking record...
    # TODO: it should only do this if there were actual changes...
    srec = None
    for record in ret.records:
      if record.type == 'TXT' and record.name == '_dnssync.' + ret.name:
        srec = record
        break
    for record in ret.newrecords:
      if record.type == 'TXT' and record.name == '_dnssync.' + ret.name:
        if srec is not None and record.content == srec.content:
          record.content = self._bumpSerial(record)
        break
    else:
      ret.newrecords.append(api.Record(
        name='_dnssync.' + ret.name, ttl=14400, rclass='IN', type='TXT',
        content=self._bumpSerial(srec)))
    return ret

  #----------------------------------------------------------------------------
  def createRecord(self, context, record):
    subhost = record.name[: - len(context.name) - 1]
    data = dict(
      action           = 'adddns',
      lines            = '1',
      add_recordType1  = record.type,           # ALL
      add_Host1        = subhost,               # A/AAAA/MX/TXT
      add_Alias1       = subhost,               # CNAME
      add_Zone1        = subhost,               # NS
      add_SRVProto1    = subhost,               # SRV
      add_ipAddress1   = record.content,        # A/AAAA
      add_Address1     = record.content,        # CNAME/MX/NS/SRV
      add_Comment1     = record.content,        # TXT
      add_pref1        = record.priority,       # MX/SRV
      add_weight1      = record.weight,         # SRV
      add_port1        = record.port,           # SRV
    )
    self._postDnsAction(record, 'create', data)

  #----------------------------------------------------------------------------
  def _postDnsAction(self, record, action, data):
    resp = self.session.post(self.BASEURL + '/members/managedns/', data=data)
    ret  = parser.evaluateResponse(resp.text)
    if ret.code != 200:
      raise api.DriverError(
        _('could not {} record {}/{}: {}', action, record.name, record.type, ret.message))

  #----------------------------------------------------------------------------
  def updateRecord(self, context, record, oldrecord):
    rid  = str(oldrecord.id)
    data = dict(action='updatedns')
    data['dns_content_' + rid]  = record.content
    if record.type in ('MX', 'SRV'):
      data['dns_pref_' + rid]   = record.priority
    if record.type == 'SRV':
      data['dns_weight_' + rid] = record.weight
      data['dns_port_' + rid]   = record.port
    self._postDnsAction(record, 'update', data)

  #----------------------------------------------------------------------------
  def deleteRecord(self, context, record):
    data = dict(action='updatedns', remove=record.id)
    self._postDnsAction(record, 'delete', data)

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
