# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2014/11/05
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

# shamelessly scrubbed from 05bit's "powerdnsclient" project that has
# been deleted, but was located at:
#   https://github.com/05bit/python-powerdnsclient

from suds.client import Client as BaseClient

#------------------------------------------------------------------------------
class Client(BaseClient):
  '''
  Client for PowerDNS service.

  Methods (SOAP):

    addNativeDomain(xs:string domainName, )
    addRecordToZone(xs:int zoneId, xs:string Name,
                    xs:string Type, xs:string Content,
                    xs:int TimeToLive, xs:int Priority, )
    deleteAllRecordsForDomain(xs:int zoneId, )
    deleteRecordById(xs:int recordId, )
    deleteZoneById(xs:int zoneId, )
    deleteZoneByName(xs:string zoneName, )
    listRecords(xs:int zoneId, )
    listRecordsByType(xs:int zoneId, xs:string type, )
    listZones()
    renewZone(xs:int zoneId, )
    updateRecord(xs:int recordId, xs:string Name,
                 xs:string Type, xs:string Content,
                 xs:int TimeToLive, xs:int Priority, )

  Read complete description here:
  https://www.powerdns.net/services/express.asmx
  '''

  POWERDNS_URL = 'https://www.powerdns.net/services/express.asmx?WSDL'

  #----------------------------------------------------------------------------
  def __init__(self, apikey):
    url = self.POWERDNS_URL
    location = '%s&apikey=%s' % (url, apikey)
    super(Client, self).__init__(url, location=location)

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
