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
    raise NotImplementedError()

  #----------------------------------------------------------------------------
  def put(self, name, zone):
    '''
    Updates the zone named `name` (an absolute domain name) to the
    specification in `zone` on the current hosted DNS provider.

    If available, this should return the stats on how many records
    were added/updated/deleted by returning an object with numeric
    `created`, `updated`, and `deleted` attributes.
    '''
    raise NotImplementedError()

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
