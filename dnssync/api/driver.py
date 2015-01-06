# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2015/01/01
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

from .record import Record
from . import error

#------------------------------------------------------------------------------

log = logging.getLogger(__name__)

#------------------------------------------------------------------------------
class Driver(object):

  # todo: implement this concept...
  # #----------------------------------------------------------------------------
  # @staticmethod
  # def config():
  #   '''
  #   Returns a list of available configurations for this Driver
  #   subclass.
  #   '''
  #   raise NotImplementedError()

  #----------------------------------------------------------------------------
  @property
  def name(self):
    raise NotImplementedError()

  #----------------------------------------------------------------------------
  def __init__(self, params, *args, **kw):
    '''
    Creates a new instance of a subclass of :class:`.Driver` with the
    specified parameters `params`, which is a dict with attributes set
    to the current configuration values.
    '''
    super(Driver, self).__init__(*args, **kw)
    self.params = params

  #----------------------------------------------------------------------------
  def list(self):
    '''
    Fetches the list of zones maintained under the current account on
    the current hosted DNS provider.
    '''
    raise NotImplementedError()

  #----------------------------------------------------------------------------
  def get(self, name):
    '''
    Fetches the zone named `name` (an absolute domain name) from the
    current hosted DNS provider.
    '''
    # TODO: i should really be building this from dns.zone.* calls...
    #       but dnspython is *so* unintuitive! ugh.
    #       ==> well, one of the reasons that this is useful is that
    #           the record in getRecords() have id's, which are used
    #           during updating.
    lines = []
    for record in self.getRecords(name):
      lines.append(record.toText())
    data = '\n'.join(lines)
    return dns.zone.from_text(data, origin=name, relativize=False)

  #----------------------------------------------------------------------------
  def getRecords(self, name):
    '''
    Fetches the DNS records in the zone named `name` (an absolute
    domain name) from the current hosted DNS provider and returns
    an array of :class:`dnssync.api.Record` objects.
    '''
    raise NotImplementedError()

  #----------------------------------------------------------------------------
  def makePutContext(self, name, zone):
    return aadict(
      name       = name,
      zone       = zone,
      records    = self.getRecords(name),
      newrecords = [Record.from_rdata(rdata) for rdata in zone.iterate_rdatas()],
    )

  #----------------------------------------------------------------------------
  def put(self, name, zone):
    '''
    Updates the zone named `name` (an absolute domain name) to the
    specification in `zone` on the current hosted DNS provider.

    Returns the stats on how many records were added/updated/deleted
    by returning an object with numeric `created`, `updated`, and
    `deleted` attributes.
    '''
    res = aadict(created=0, updated=0, deleted=0)
    context = self.makePutContext(name, zone)
    for record in context.newrecords:
      match  = self._matchRecord(context, record)
      if not match:
        log.info('adding %s record: %s (%s)', record.type, record.name, record.content)
        self.createRecord(context, record)
        res.created += 1
      else:
        context.records.remove(match)
        if match.ttl == record.ttl \
            and match.content == record.content \
            and match.priority == record.priority:
          # todo: anything else?...
          continue
        if match.type == 'SOA':
          mseq = int(match.content.split(' ')[2])
          useq = int(record.content.split(' ')[2])
          if useq < mseq:
            log.error(
              'refusing to update SOA record (serial %r is less than %r)', useq, mseq)
            continue
            log.info('updating %s record: %s (%s)', record.type, record.name, record.content)
        self.updateRecord(context, record, match)
        res.updated += 1
    for record in context.records:
      log.info('deleting %s record: %s (%s)', record.type, record.name, record.content)
      self.deleteRecord(context, record)
      res.deleted += 1
    return res

  #----------------------------------------------------------------------------
  def _matchRecord(self, context, record):
    if not context.records:
      return None
    records = [rec
               for rec in context.records
               if rec.rclass == record.rclass
                 and rec.type == record.type
                 and rec.priority == record.priority
                 and rec.name == record.name]
    if len(records) > 1:
      # todo: are MX and NS records really the only ones that can be multiple?...
      if record.type not in ('MX', 'NS'):
        raise error.UnexpectedZoneState(
          _('multiple records found for type "{type}"', type=record.type))
      records = [rec for rec in records if rec.content == record.content]
    if not records:
      return None
    if len(records) == 1:
      return records[0]
    raise error.UnexpectedZoneState(
      _('multiple records found for type "{type}" with same content "{content}"',
        type=record.type, content=record.content))

  #----------------------------------------------------------------------------
  def createRecord(self, context, record):
    raise NotImplementedError()

  #----------------------------------------------------------------------------
  def updateRecord(self, context, record, oldrecord):
    raise NotImplementedError()

  #----------------------------------------------------------------------------
  def deleteRecord(self, context, record):
    raise NotImplementedError()

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
