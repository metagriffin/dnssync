# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2016/09/30
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

import locale
import re
import math
import datetime

#------------------------------------------------------------------------------
class InvalidDuration(Exception): pass

#------------------------------------------------------------------------------
def findFirstOf(s, charr):
  'Finds the first occurence of any of the array of characters `charr`'
  # i can't believe this is not available in python...
  for idx in range(len(s)):
    for c in charr:
      if s[idx] == c: return idx
  return -1

#------------------------------------------------------------------------------
# acceptable format: '^([0-9]+[smhd]{1})*[0-9]+[smhd]?$'
durMultiplier = {'s':1, 'm':60, 'h':3600, 'd':86400, 'w':604800}
def asdur(s, default='s'):
  if s is None or len(s) <= 0:
    return 0
  idx = findFirstOf(s, ['s', 'm', 'h', 'd', 'w'])
  if idx == -1:
    try:
      val = locale.atof(s) * durMultiplier[default]
      if int(val) == val:
        val = int(val)
      return val
    except:
      raise InvalidDuration(s)
  sub = s[0:idx]
  return asdur(sub, s[idx]) + asdur(s[idx + 1:])

#------------------------------------------------------------------------------
def _dumps(quantity, unit, labels, label, current):
  if quantity < unit:
    return quantity
  ret = math.floor(quantity/unit)
  current.append('%d%s' % (ret, labels.get(label + (':s' if ret == 1 else ':p'), label)))
  return quantity - ( ret * unit )
def dumps(delta, useWeeks=True, precision=None, labels=None):
  '''
  Converts `delta` (which can be either a datetime.timedelta object or
  a number of seconds) to a string. `useWeeks` controls whether or not
  "w" (or "weeks") should be used. `precision` specifies the level of
  maximum precision (can be None, "s", "m", "h", or "d").
  '''
  # todo: support sub-seconds better...
  # todo: support de-pluralization of long labels...
  if isinstance(delta, datetime.timedelta):
    delta = delta.total_seconds()
  delta = abs(delta)
  if precision == 's':
    delta = int(round(delta))
  elif precision == 'm':
    delta = int(round(delta / 60.0)) * 60
  elif precision == 'h':
    delta = int(round(delta / 3600.0)) * 3600
  elif precision == 'd':
    delta = int(round(delta / 86400.0)) * 86400
  ret = []
  if labels is True:
    labels = {
      's:s' : ' second',     # singular
      's:p' : ' seconds',    # plural
      'm:s' : ' minute',
      'm:p' : ' minutes',
      'h:s' : ' hour',
      'h:p' : ' hours',
      'd:s' : ' day',
      'd:p' : ' days',
      'w:s' : ' week',
      'w:p' : ' weeks',
      ','   : ', ',
    }
  labels = labels or {}
  if useWeeks:
    delta = _dumps(delta, 86400 * 7, labels, 'w', ret)
  delta = _dumps(delta, 86400, labels, 'd', ret)
  delta = _dumps(delta, 3600, labels, 'h', ret)
  delta = _dumps(delta, 60, labels, 'm', ret)
  if delta != 0:
    if delta == math.floor(delta):
      ret.append('%d%s' % (delta, labels.get('s:s' if delta == 1 else 's:p', 's')))
    else:
      dig = re.sub(r'(\..*?)0+$', '', '%.3f' % (delta,))
      ret.append('%s%s' % (dig, labels.get('s:p', 's')))
  return labels.get(',', '').join(ret)

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
