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

import logging
import dns.rdata
import dns.zone
from aadict import aadict

from dnssync import api
from dnssync.api.util import absdom, reldom
from dnssync.api.i18n import _

from .protocol import Client

#------------------------------------------------------------------------------

log = logging.getLogger(__name__)

#------------------------------------------------------------------------------
class Driver(api.Driver):

  name = 'powerdns'

  # todo: implement this concept...
  # #----------------------------------------------------------------------------
  # @staticmethod
  # def config():
  #   return [
  #     ??? FORMAT ??? (name, required, validation, description)
  #     ('apikey', True, None, _('the PowerDNS API "ApiKey" parameter')),
  #   ]

  #----------------------------------------------------------------------------
  def __init__(self, *args, **kw):
    super(Driver, self).__init__(*args, **kw)
    self.client = Client(self.params.apikey)
    if not self.params.apikey:
      raise api.ConfigurationError(_('required parameter "apikey" missing'))

  #----------------------------------------------------------------------------
  def _zones(self):
    return dict((absdom(zone.Name), zone.Id)
                for zone in self.client.service.listZones().Zones.Zone)

  #----------------------------------------------------------------------------
  def list(self):
    return self._zones().keys()

  #----------------------------------------------------------------------------
  def getRecords(self, name):
    # TODO: i should really be building this from dns.zone.* calls...
    #       but dnspython is *so* unintuitive! ugh.
    zid     = self._zones()[name]
    records = []
    for record in self.client.service.listRecords(zid).Records.Record:
      if record.Type is None:
        # todo: should this really just be ignored? what *is* this??
        continue
      content = ' '.join([
        absdom(comp) for comp in record.Content.split()])
      arec = api.Record(
        id       = record.Id,
        name     = absdom(record.Name),
        ttl      = record.TimeToLive,
        rclass   = 'IN',
        type     = str(record.Type),
        content  = content,
      )
      if arec.type == 'MX':
        # todo: are MX records really the only ones that can have priorities?...
        arec.priority = record.Priority
      records.append(arec)
    return records

  #----------------------------------------------------------------------------
  def makePutContext(self, name, zone):
    ret = super(Driver, self).makePutContext(name, zone)
    ret.zoneid = self._zones()[name]
    for name, ttl, rdata in zone.iterate_rdatas():
      if dns.rdataclass.to_text(rdata.rdclass) != 'IN':
        raise api.UnsupportedRecordType(
          _('PowerdDNS does not support non-"IN" record classes: {!r}',
            (name, ttl, rdata)))
    return ret

  #----------------------------------------------------------------------------
  def createRecord(self, context, record):

    # PowerDNS does not seem to support absolute DNS names... ugh.
    name    = reldom(record.name)
    content = ' '.join([reldom(comp) for comp in record.content.split(' ')])

    resp = self.client.service.addRecordToZone(
      context.zoneid, name, record.type, content, record.ttl, record.priority or 0)
    if resp.code != 100:
      raise api.DriverError(
        _('could not add record {}/{}: {}', record.name, record.type, resp.description))

  #----------------------------------------------------------------------------
  def updateRecord(self, context, record, oldrecord):

    # PowerDNS does not seem to support absolute DNS names... ugh.
    name    = reldom(record.name)
    content = ' '.join([reldom(comp) for comp in record.content.split(' ')])

    resp = self.client.service.updateRecord(
      oldrecord.id, name, record.type, content, record.ttl, record.priority or 0)
    if resp.code != 100:
      raise api.DriverError(
        _('could not update record {}/{}: {}', record.name, record.type, resp.description))

  #----------------------------------------------------------------------------
  def deleteRecord(self, context, record):
    resp = self.client.service.deleteRecordById(record.id)
    if resp.code != 100:
      raise api.DriverError(
        _('could not delete record {}/{}: {}', record.name, record.type, resp.description))

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
