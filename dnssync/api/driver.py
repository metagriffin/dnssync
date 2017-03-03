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
from dns.exception import SyntaxError
from aadict import aadict

from .i18n import _
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
  def __init__(self, extend, params, *args, **kw):
    '''
    Creates a new instance of a subclass of :class:`.Driver` with the
    specified parameters `params`, which is a dict with attributes set
    to the current configuration values.

    During driver plugin loading, `extend` is the previous plugin's
    constructed `Driver` object. Since the default driver does not
    know how to handle multi-plugin drivers, it throws an error. So,
    if your subclass knows what to do, it should handle it and set it
    to None before calling super.
    '''
    if extend is not None:
      raise Value
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
    try:
      return dns.zone.from_text(data, origin=name, relativize=False)
    except SyntaxError as err:
      log.exception(
        'failed while trying to parse zonefile:\n  %s',
        '\n  '.join(data.split('\n')))
      raise

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
    context = self.makePutContext(name, zone)
    creates = []
    updates = {}
    deletes = []
    records = context.records[:]
    for record in context.newrecords:
      match  = self._matchRecord(context, record)
      if not match:
        creates.append(record)
      else:
        records.remove(match)
        if not self._recordChanged(match, record):
          continue
        if match.type == 'SOA':
          mseq = int(match.content.split(' ')[2])
          useq = int(record.content.split(' ')[2])
          if useq < mseq:
            log.error(
              'refusing to update SOA record (serial %r is less than %r)', useq, mseq)
            continue
        updates[match] = record
    for record in records:
      deletes.append(record)
    return self.putChanges(context, creates, updates, deletes)

  #----------------------------------------------------------------------------
  def putChanges(self, context, creates, updates, deletes):
    types = {}
    for record in creates:
      if record.type not in types:
        types[record.type] = aadict(creates=[], updates={}, deletes=[])
      types[record.type].creates.append(record)
    for record, newrecord in updates.items():
      if record.type not in types:
        types[record.type] = aadict(creates=[], updates={}, deletes=[])
      types[record.type].updates[record] = newrecord
    for record in deletes:
      if record.type not in types:
        types[record.type] = aadict(creates=[], updates={}, deletes=[])
      types[record.type].deletes.append(record)
    for rtype, params in types.items():
      self.putChangesByType(context, rtype, **params)
    return aadict(
      created=len(creates), updated=len(updates), deleted=len(deletes))

  #----------------------------------------------------------------------------
  def putChangesByType(self, context, rtype, creates, updates, deletes):
    for record in creates:
      log.info('creating %s record: %s (%s)', record.type, record.name, record.content)
      self.createRecord(context, record)
    for record, newrecord in updates.items():
      log.info('updating %s record: %s (%s)', record.type, record.name, newrecord.content)
      self.updateRecord(context, record, newrecord)
    for record in deletes:
      log.info('deleting %s record: %s (%s)', record.type, record.name, record.content)
      self.deleteRecord(context, record)

  #----------------------------------------------------------------------------
  def _matchRecord(self, context, record):
    if not context.records:
      return None
    records = [rec
               for rec in context.records
               if rec.rclass == record.rclass
                 and rec.type == record.type
                 and rec.priority == record.priority
                 and rec.name == record.name
               # todo: what about SRV and NAPTR records... add more?...
    ]
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
  def _recordChanged(self, record, newrecord):
    if record.ttl == newrecord.ttl \
        and record.content == newrecord.content \
        and record.priority == newrecord.priority:
      # todo: anything else?... eg. for SRV and NAPTR records...
      #       ie. weight, proto, port, etc.
      return False
    return True

  #----------------------------------------------------------------------------
  def createRecord(self, context, record):
    raise NotImplementedError()

  #----------------------------------------------------------------------------
  def updateRecord(self, context, record, newrecord):
    raise NotImplementedError()

  #----------------------------------------------------------------------------
  def deleteRecord(self, context, record):
    raise NotImplementedError()


#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
