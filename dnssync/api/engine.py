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
import difflib
import subprocess
import logging
import socket

import six
import dns.zone
import dns.resolver
from aadict import aadict
from six.moves import StringIO

from .i18n import _
from .util import absdom, reldom
from .error import *
from .record import Record

#------------------------------------------------------------------------------

log = logging.getLogger(__name__)

#------------------------------------------------------------------------------
def writeZone(ctxt, zone, fp):
  fp.write(';; -*- coding: utf-8{config} -*-\n'.format(
    config=( ( '; dnssync-config: ' + ctxt.config )
             if ctxt.config else '' )))
  fp.write('$ORIGIN {domain}\n'.format(domain=ctxt.domain))
  zone.to_file(fp, relativize=False)

#------------------------------------------------------------------------------
def cmd_download(ctxt):
  zone = ctxt.driver.get(ctxt.domain)
  if ctxt.zonefile is None:
    writeZone(ctxt, zone, sys.stdout)
  else:
    with open(ctxt.zonefile, 'wb') as fp:
      writeZone(ctxt, zone, fp)
  return 0

#------------------------------------------------------------------------------
def renderDiff(lines, fp=None):
  fp = fp or sys.stdout
  from blessings import Terminal
  if not Terminal().is_a_tty:
    for line in lines:
      fp.write(line + '\n')
    return
  try:
    proc = subprocess.Popen(
      'colordiff', shell=True, close_fds=True,
      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, errput = proc.communicate('\n'.join(lines))
    if errput:
      for line in lines:
        fp.write(line + '\n')
      return
    fp.write(output + '\n')
  except Exception as err:
    for line in lines:
      fp.write(line + '\n')

#------------------------------------------------------------------------------
def zonediff(zoneA, zoneB, labelA, labelB, fp=None):
  pbuf  = six.StringIO()
  lbuf  = six.StringIO()
  zoneA.to_file(pbuf, relativize=False)
  zoneB.to_file(lbuf, relativize=False)
  pbuf = sorted(pbuf.getvalue().split('\n'))
  lbuf = sorted(lbuf.getvalue().split('\n'))
  count = 0
  lines = [line.rstrip() for line in difflib.unified_diff(
    pbuf, lbuf, fromfile=labelA, tofile=labelB)]
  if lines:
    renderDiff(lines, fp)
  return len(lines)

#------------------------------------------------------------------------------
def cmd_diff(ctxt):
  # todo: sort by: type => name => priority
  pzone = ctxt.driver.get(ctxt.domain)
  lzone = dns.zone.from_file(ctxt.zonefile, origin=ctxt.domain, relativize=False)
  return zonediff(pzone, lzone,
    _('{domain} <service "{service}">', domain=ctxt.domain, service=ctxt.driver.name),
    _('{domain} <zonefile "{zonefile}">', domain=ctxt.domain, zonefile=ctxt.zonefile))

#------------------------------------------------------------------------------
def cmd_upload(ctxt):
  lzone = dns.zone.from_file(ctxt.zonefile, origin=ctxt.domain, relativize=False)
  res   = ctxt.driver.put(ctxt.domain, lzone)
  if res and 'created' in res:
    print _(
      '{created} record(s) created, {updated} record(s) updated, and {deleted} record(s) deleted.',
      created=res.created, updated=res.updated, deleted=res.deleted)
  return 0

#------------------------------------------------------------------------------
def cmd_list(ctxt):
  for zname in sorted(ctxt.driver.list()):
    sys.stdout.write(reldom(zname) + '\n')
  return 0

#------------------------------------------------------------------------------
def getDnsRecords(record, resolver):
  try:
    ans = resolver.query(record.name, rdtype=record.type, rdclass=record.rclass)
  except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
    return []
  rdset = ans.response.answer[0].to_rdataset()
  # todo: is there a better place to get this TTL from?...
  return [Record.from_rdata([ans.qname, record.ttl, rdat]) for rdat in rdset]

#------------------------------------------------------------------------------
def cmd_verify(ctxt):
  lzone    = dns.zone.from_file(ctxt.zonefile, origin=ctxt.domain, relativize=False)
  server   = ctxt.options.server
  resolver = dns.resolver
  if server:
    sio = StringIO('nameserver ' + socket.gethostbyname(server))
    resolver = dns.resolver.Resolver(sio)

  # TODO: i should really be building this from dns.zone.* calls...
  #       but dnspython is *so* unintuitive! ugh.
  records = dict()
  for rdata in lzone.iterate_rdatas():
    record = Record.from_rdata(rdata)
    if record.name not in records:
      records[record.name] = dict()
    if record.type in records[record.name]:
      continue
    records[record.name][record.type] = getDnsRecords(record, resolver)
  data = '\n'.join(rec.toText()
                   for name, types in records.items()
                   for recs in types.values()
                   for rec in recs)
  dzone = dns.zone.from_text(data, origin=ctxt.domain, relativize=False)
  # /TODO

  return zonediff(lzone, dzone,
    _('{domain} <zonefile "{zonefile}">', domain=ctxt.domain, zonefile=ctxt.zonefile),
    _('{domain} <DNS "{server}">', domain=ctxt.domain, server=server or 'default'))

#------------------------------------------------------------------------------
def run(command, driver, options):

  context = aadict(
    options  = options,
    config   = options.config,
    driver   = driver,
    domain   = absdom(options.domain) if options.domain else None,
    zonefile = getattr(options, 'zonefile', None),
  )

  if command != 'list':
    if not context.domain:
      raise Error(_('required parameter "domain" not specified'))

  cmd = globals().get('cmd_' + command)
  if not cmd:
    raise Exception(_('no such command "{}"', command))

  return cmd(context)

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
