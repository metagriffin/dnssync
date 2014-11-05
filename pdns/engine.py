# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2014/02/27
# copy: (C) Copyright 2014-EOT metagriffin -- see LICENSE.txt
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

import sys
import six
import dns.zone
import difflib
import re
import blessings
import subprocess
from aadict import aadict
import logging

from .i18n import _
from . import protocol

#------------------------------------------------------------------------------

log = logging.getLogger(__name__)

#------------------------------------------------------------------------------
class Error(Exception): pass
class DomainNotFound(Error): pass
class UnsupportedRecordType(Error): pass
class UnexpectedZoneState(Error): pass

RECORDFMTS = {
  '*'    : '{name} {ttl} IN {type} {content}',
  'MX'   : '{name} {ttl} IN {type} {priority} {content}',
}

dnsname_re = re.compile(
  # todo: ideally, use the following more general RE:
  #   each component: (?![0-9]+$)(?!-)[a-zA-Z0-9-]{1,63}(?<!-)
  r'''
  ^
  (?:
    (?![0-9]+\.)                # sld name components cannot be numbers-only
    (?!-)                       # name components cannot start with a dash
    [a-zA-Z0-9-]{1,63}          # at most 63 alpha-numeric + dash characters
    (?<!-)                      # name components cannot end with a dash
    \.
  )+
  (?![0-9]+$)                   # tld name components cannot be numbers-only
  (?![0-9]+\.)                  # tld name components cannot be numbers-only
  (?!-)                         # name components cannot start with a dash
  [a-zA-Z0-9-]{1,63}            # at most 63 alpha-numeric + dash characters
  (?<!-)                        # name components cannot end with a dash
  \.?                           # the final dot is optional
  $
''', re.VERBOSE | re.IGNORECASE)


#------------------------------------------------------------------------------
def absdom(domain):
  if not dnsname_re.match(domain):
    return domain
  domain = domain.lower()
  if not domain.endswith('.'):
    domain += '.'
  return domain

#------------------------------------------------------------------------------
def reldom(domain):
  if not dnsname_re.match(domain):
    return domain
  domain = domain.lower()
  if domain.endswith('.'):
    domain = domain[:-1]
  return domain

#------------------------------------------------------------------------------
def downloadZone(ctxt):
  # TODO: i should really be building this from dns.zone.* calls...
  #       but dnspython is *so* unintuitive! ugh.
  lines = []
  for record in ctxt.service.listRecords(ctxt.zoneid).Records.Record:
    fmt = RECORDFMTS.get(record.Type, RECORDFMTS.get('*'))
    record.Content = ' '.join([
      absdom(comp) for comp in record.Content.split()])
    lines.append(fmt.format(
      name     = absdom(record.Name),
      ttl      = record.TimeToLive,
      type     = record.Type,
      priority = record.Priority,
      content  = record.Content,
    ))
  data = '\n'.join(lines)
  return dns.zone.from_text(data, origin=ctxt.domain, relativize=False)

#------------------------------------------------------------------------------
def download(ctxt):
  zone = downloadZone(ctxt)
  with open(ctxt.zonefile, 'wb') as fp:
    fp.write('$ORIGIN {domain}\n'.format(domain=ctxt.domain))
    zone.to_file(fp, relativize=False)
  return 0

#------------------------------------------------------------------------------
def renderDiff(lines):
  from blessings import Terminal
  if not Terminal().is_a_tty:
    for line in lines:
      print line
    return
  try:
    proc = subprocess.Popen(
      'colordiff', shell=True, close_fds=True,
      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, errput = proc.communicate('\n'.join(lines))
    if errput:
      for line in lines:
        print line
      return
    print output
  except Exception as err:
    for line in lines:
      print line

#------------------------------------------------------------------------------
def diff(ctxt):
  # todo: sort by: type => name => priority
  pzone = downloadZone(ctxt)
  lzone = dns.zone.from_file(ctxt.zonefile, origin=ctxt.domain, relativize=False)
  pbuf  = six.StringIO()
  lbuf  = six.StringIO()
  pzone.to_file(pbuf, relativize=False)
  lzone.to_file(lbuf, relativize=False)
  pbuf = sorted(pbuf.getvalue().split('\n'))
  lbuf = sorted(lbuf.getvalue().split('\n'))
  count = 0
  lines = [line.rstrip() for line in difflib.unified_diff(
    pbuf, lbuf,
    fromfile = _('{domain} <PowerDNS>', domain=ctxt.domain, zonefile=ctxt.zonefile),
    tofile   = _('{domain} <zonefile "{zonefile}">', domain=ctxt.domain, zonefile=ctxt.zonefile))
  ]
  if lines:
    renderDiff(lines)
  return len(lines)

#------------------------------------------------------------------------------
def matchRecord(records, record):
  if not records:
    return None
  records = [rec 
             for rec in records
             if rec.Type == record.Type and rec.Priority == record.Priority
               and rec.Name == record.Name]
  if len(records) > 1:
    # todo: are MX and NS records really the only ones that can be multiple?...
    if record.Type not in ('MX', 'NS'):
      raise UnexpectedZoneState(
        _('multiple records found for type "{type}"', type=record.Type))
    records = [rec for rec in records if rec.Content == record.Content]
  if not records:
    return None
  if len(records) == 1:
    return records[0]
  raise UnexpectedZoneState(
    _('multiple records found for type "{type}" with same content "{content}"',
      type=record.Type, content=record.Content))

#------------------------------------------------------------------------------
def updateRecord(ctxt, records, record):

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

  # PowerDNS does not seem to support absolute DNS names... ugh.
  update.Name    = reldom(update.Name)
  update.Content = ' '.join([reldom(comp) for comp in update.Content.split(' ')])

  match = matchRecord(records, update)

  if not match:
    log.info('adding %s record: %s (%s)', update.Type, update.Name, update.Content)
    resp = ctxt.service.addRecordToZone(
      ctxt.zoneid, update.Name, update.Type, update.Content,
      update.TimeToLive, update.Priority)
    # todo: check response...
    ctxt.created += 1
    return

  records.remove(match)

  if match.TimeToLive == update.TimeToLive and match.Content == update.Content:
    return

  if match.Type == 'SOA':
    mseq = int(match.Content.split(' ')[2])
    useq = int(update.Content.split(' ')[2])
    if useq < mseq:
      log.error(
        'refusing to update SOA record (serial %r is less than %r)', useq, mseq)
      return

  log.info('updating %s record: %s (%s)', update.Type, update.Name, update.Content)
  resp = ctxt.service.updateRecord(
    match.Id, update.Name, update.Type, update.Content,
    update.TimeToLive, update.Priority)
  # todo: check response...
  ctxt.updated += 1

  return

#------------------------------------------------------------------------------
def upload(ctxt):
  lzone = dns.zone.from_file(ctxt.zonefile, origin=ctxt.domain, relativize=False)
  records = list(ctxt.service.listRecords(ctxt.zoneid).Records.Record)
  ctxt.created = 0
  ctxt.updated = 0
  ctxt.deleted = 0
  for name, ttl, rdata in lzone.iterate_rdatas():
    if dns.rdataclass.to_text(rdata.rdclass) != 'IN':
      raise UnsupportedRecordType(
        _('PowerdDNS does not support non-"IN" record classes: {!r}',
          (name, ttl, rdata)))
    updateRecord(ctxt, records, aadict(name=name, ttl=ttl, rdata=rdata))
  for record in records:
    log.info('deleting %s record: %s (%s)', record.Type, record.Name, record.Content)
    resp = ctxt.service.deleteRecordById(record.Id)
    # todo: check response...
    ctxt.deleted += 1
  print _(
    '{created} record(s) created, {updated} record(s) updated, and {deleted} record(s) deleted.',
    created=ctxt.created, updated=ctxt.updated, deleted=ctxt.deleted)
  return 0

#------------------------------------------------------------------------------
def run(command, apikey, domain, zonefile):
  client = protocol.Client(apikey)
  zoneid = None
  domain = absdom(domain)
  for zone in client.service.listZones().Zones.Zone:
    if absdom(zone.Name) == domain:
      zoneid = zone.Id
      break
  else:
    raise DomainNotFound(domain)
  client.domain = domain
  client.zoneid = zoneid
  client.zonefile = zonefile
  if command == 'download':
    return download(client)
  if command == 'upload':
    return upload(client)
  if command == 'diff':
    return diff(client)
  raise Exception(_('no such command "{}"', command))

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
