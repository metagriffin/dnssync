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

import re
import os

import morph

#------------------------------------------------------------------------------

dnsname_re = re.compile(
  # todo: ideally, use the following more general RE:
  #   each component: (?![0-9]+$)(?!-)[a-zA-Z0-9-]{1,63}(?<!-)
  r'''
  ^
  (?:
    (?![0-9]+\.)                # sld name components cannot be numbers-only
    (?!-)                       # name components cannot start with a dash
    [a-zA-Z0-9_]                # first character alpha-numeric + underscore
    [a-zA-Z0-9-]{0,62}          # at most 62 alpha-numeric + dash characters
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
  '''
  Returns a canonical version of the domain name `domain` using absolute
  domain name syntax (i.e. ending with a period).
  '''
  if domain.startswith('*.'):
    return '*.' + absdom(domain[2:])
  if not dnsname_re.match(domain):
    return domain
  domain = domain.lower()
  if not domain.endswith('.'):
    domain += '.'
  return domain

#------------------------------------------------------------------------------
def reldom(domain, to=None):
  '''
  Returns a canonical version of the domain name `domain` using relative
  domain name syntax (i.e. not ending with a period).
  '''
  if to is not None:
    tmp = absdom(domain)
    to = absdom(to)
    if tmp.endswith('.' + to):
      return tmp[:-1 - len(to)]
  if not dnsname_re.match(domain):
    return domain
  domain = domain.lower()
  if domain.endswith('.'):
    domain = domain[:-1]
  return domain

#------------------------------------------------------------------------------
_evalenv_re = re.compile(
  '(.*?)\\$\\{ENV:([^:}]*)(:-([^}]*))?\\}', flags=re.DOTALL)
def evalenv(val, context=None):
  '''
  Executes environment variable expansion on ``val`` where any
  sequence in the format ${ENV:NAME[:-DEFAULT]} is substituted. If the
  specified environment variable is not defined and no default is
  provided, then a ValueError is raised.
  '''
  if not morph.isstr(val):
    return val
  # todo: use re.finditer()...
  # todo: this expression evaluation is very primitive...
  match = _evalenv_re.match(val)
  if not match:
    return val
  ret = match.group(1)
  if match.group(2) in os.environ:
    ret += os.environ.get(match.group(2))
  elif match.group(3):
    # todo: expand based on content of context?...
    ret += match.group(4)
  else:
    raise ValueError('environment variable "%s" not defined' % (match.group(2),))
  return ret + evalenv(val[len(match.group(0)):])

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
