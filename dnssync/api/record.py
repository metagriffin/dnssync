# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2015/01/05
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

import dns.rdataclass
from aadict import aadict

#------------------------------------------------------------------------------

FORMATS = {
  '*'    : '{name} {ttl} {rclass} {type} {content}',
  'MX'   : '{name} {ttl} {rclass} {type} {priority} {content}',
  'SRV'  : '{name} {ttl} {rclass} {type} {priority} {weight} {port} {content}',
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
class Record(object):

  #----------------------------------------------------------------------------
  def __init__(self, id=None,
               name=None, ttl=None, rclass=None, type=None, content=None,
               priority=None, weight=None, port=None,
               *args, **kw):
    super(Record, self).__init__(*args, **kw)
    self.id       = id
    self.name     = name
    self.ttl      = ttl
    self.rclass   = rclass
    self.type     = type
    self.priority = priority
    self.weight   = weight
    self.port     = port
    self.content  = content

  #----------------------------------------------------------------------------
  @staticmethod
  def from_rdata(rdata):
    ret = Record(
      name     = rdata[0].to_text(),
      ttl      = rdata[1],
      rclass   = dns.rdataclass.to_text(rdata[2].rdclass),
      type     = str(dns.rdatatype.to_text(rdata[2].rdtype)),
      priority = getattr(rdata[2], 'preference', None),
      # TODO: weight?...
      # TODO: port?...
      content  = rdata[2].to_text(),
    )
    if ret.type == 'MX':
      ret.content = rdata[2].exchange.to_text()
    elif ret.type == 'TXT':
      # todo: is this how they should all be done?...
      ret.content = ' '.join(rdata[2].strings)
    return ret

  #----------------------------------------------------------------------------
  def toDict(self):
    return aadict(self.__dict__)

  #----------------------------------------------------------------------------
  def toText(self):
    fmt = FORMATS.get(self.type) or FORMATS.get('*')
    dat = self.toDict()
    if dat.type == 'TXT':
      dat.content = escapeContent(dat.content)
    return fmt.format(**dat)

  #----------------------------------------------------------------------------
  def __repr__(self):
    ret = '<Record'
    for key, val in sorted(self.toDict().items()):
      if val is not None:
        ret += ' ' + key + '=' + repr(val)
    ret += '>'
    return ret

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
