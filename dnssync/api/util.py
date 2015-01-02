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
  if not dnsname_re.match(domain):
    return domain
  domain = domain.lower()
  if not domain.endswith('.'):
    domain += '.'
  return domain

#------------------------------------------------------------------------------
def reldom(domain):
  '''
  Returns a canonical version of the domain name `domain` using relative
  domain name syntax (i.e. not ending with a period).
  '''
  if not dnsname_re.match(domain):
    return domain
  domain = domain.lower()
  if domain.endswith('.'):
    domain = domain[:-1]
  return domain

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
