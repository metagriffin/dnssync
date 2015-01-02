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

RECORDFMTS = {
  '*'    : '{name} {ttl} IN {type} {content}',
  'MX'   : '{name} {ttl} IN {type} {priority} {content}',
}

#------------------------------------------------------------------------------
def escapeContent(text):
  if not text:
    return text
  # todo: `dns.rdata._escapify` should really be doing this detection for me...
  if ';' not in text and ' ' not in text and '"' not in text:
    return text
  return '"' + dns.rdata._escapify(text) + '"'

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
  def _get(self, name):
    # TODO: i should really be building this from dns.zone.* calls...
    #       but dnspython is *so* unintuitive! ugh.
    zid   = self._zones()[name]
    lines = []
    for record in self.client.service.listRecords(zid).Records.Record:
      fmt = RECORDFMTS.get(record.Type) or RECORDFMTS.get('*')
      record.Content = ' '.join([
        absdom(comp) for comp in record.Content.split()])
      # todo: is TXT really the only record type?...
      if record.Type == 'TXT':
        record.Content = escapeContent(record.Content)
      lines.append(fmt.format(
        name     = absdom(record.Name),
        ttl      = record.TimeToLive,
        type     = record.Type,
        priority = record.Priority,
        content  = record.Content,
      ))
    data = '\n'.join(lines)
    return dns.zone.from_text(data, origin=name, relativize=False)

  #----------------------------------------------------------------------------
  def get(self, name):
    return self._get(name)

  #----------------------------------------------------------------------------
  def _matchRecord(self, records, record):
    if not records:
      return None
    records = [rec
               for rec in records
               if rec.Type == record.Type and rec.Priority == record.Priority
                 and rec.Name == record.Name]
    if len(records) > 1:
      # todo: are MX and NS records really the only ones that can be multiple?...
      if record.Type not in ('MX', 'NS'):
        raise api.UnexpectedZoneState(
          _('multiple records found for type "{type}"', type=record.Type))
      records = [rec for rec in records if rec.Content == record.Content]
    if not records:
      return None
    if len(records) == 1:
      return records[0]
    raise api.UnexpectedZoneState(
      _('multiple records found for type "{type}" with same content "{content}"',
        type=record.Type, content=record.Content))

  #----------------------------------------------------------------------------
  def _updateRecord(self, zoneid, records, record, result):

    update = aadict(
      Name       = record.name.to_text(),
      Type       = dns.rdatatype.to_text(record.rdata.rdtype),
      Priority   = 0,
      TimeToLive = record.ttl,
      Content    = record.rdata.to_text(),
    )

    if update.Type == 'MX':
      update.Priority = record.rdata.preference
      update.Content  = record.rdata.exchange.to_text()

    if update.Type == 'TXT':
      # todo: is this how they should all be done?...
      update.Content = ' '.join(record.rdata.strings)

    # PowerDNS does not seem to support absolute DNS names... ugh.
    update.Name    = reldom(update.Name)
    update.Content = ' '.join([reldom(comp) for comp in update.Content.split(' ')])

    match = self._matchRecord(records, update)

    if not match:
      log.info('adding %s record: %s (%s)', update.Type, update.Name, update.Content)
      resp = self.client.service.addRecordToZone(
        zoneid, update.Name, update.Type, update.Content,
        update.TimeToLive, update.Priority)
      if resp.code != 100:
        raise api.DriverError(
          _('could not add record {}/{}: {}', update.Name, update.Type, resp.description))
      result.created += 1
      return

    records.remove(match)

    if match.TimeToLive == update.TimeToLive and match.Content == update.Content:
      # todo: check priorities...
      # todo: anything else?...
      return

    if match.Type == 'SOA':
      mseq = int(match.Content.split(' ')[2])
      useq = int(update.Content.split(' ')[2])
      if useq < mseq:
        log.error(
          'refusing to update SOA record (serial %r is less than %r)', useq, mseq)
        return

    log.info('updating %s record: %s (%s)', update.Type, update.Name, update.Content)
    resp = self.client.service.updateRecord(
      match.Id, update.Name, update.Type, update.Content,
      update.TimeToLive, update.Priority)
    if resp.code != 100:
      raise api.DriverError(
        _('could not update record {}/{}: {}', update.Name, update.Type, resp.description))
    result.updated += 1
    return

  #----------------------------------------------------------------------------
  def put(self, name, zone):
    res = aadict(created=0, updated=0, deleted=0)
    zid = self._zones()[name]
    records = list(self.client.service.listRecords(zid).Records.Record)
    for name, ttl, rdata in zone.iterate_rdatas():
      if dns.rdataclass.to_text(rdata.rdclass) != 'IN':
        raise api.UnsupportedRecordType(
          _('PowerdDNS does not support non-"IN" record classes: {!r}',
            (name, ttl, rdata)))
    for name, ttl, rdata in zone.iterate_rdatas():
      self._updateRecord(zid, records, aadict(name=name, ttl=ttl, rdata=rdata), res)
    for record in records:
      log.info('deleting %s record: %s (%s)', record.Type, record.Name, record.Content)
      resp = self.client.service.deleteRecordById(record.Id)
      if resp.code != 100:
        raise api.DriverError(
          _('could not delete record {}/{}: {}', record.Name, record.Type, resp.description))
      # todo: check response...
      res.deleted += 1
    return res


#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
