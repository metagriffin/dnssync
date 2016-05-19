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

from suds.client import Client as BaseClient, Method

from dnssync import api

#------------------------------------------------------------------------------

POWERDNS_CODES = {
  # cached from:
  #   https://www.powerdns.net/inc/pdf/PowerDNS%20Express%20API%202.3.pdf
  100 : ('SUCCESS',                          'Operation completed succesfully'),
  200 : ('INVALID_USER',                     'Invalid user, API key is incorrect'),
  210 : ('NOT_ENOUGH_BALANCE',               'Not enough balance to renew domain'),
  300 : ('DOMAIN_NAME_INVALID',              'Not a valid domain name. All names must be in the form of <name>.<tld>'),
  301 : ('DOMAIN_ALREADY_EXISTS',            'Domain could not be added because it already exists in PowerDNS'),
  302 : ('DOMAIN_IS_RESERVED',               'Domain is reserved and could not be added'),
  310 : ('NO_SUCH_DOMAIN',                   'Domain could not be found in your control panel'),
  320 : ('ADDING_DOMAIN_FAILED',             'Domain could not be added to your control panel'),
  330 : ('DELETING_DOMAIN_FAILED',           'Domain could not be deleted from your control panel'),
  400 : ('RECORD_NOT_VALID_FOR_THIS_DOMAIN', 'Record is not valid. Record must belong to the domain you are adding it to.'),
  401 : ('RECORD_INVALID_TTL',               'TTL is invalid. It must be higher than 60.'),
  402 : ('RECORD_INVALID_TYPE',              'Invalid type of record. Allowed types are: "URL", "NS", "A", "AAAA", "CNAME", "PTR", "MX" and "TXT"'),
  403 : ('RECORD_INVALID_PRIORITY',          'Invalid priority. It must be higher than 0.'),
  404 : ('RECORD_INVALID_NAME',              'Invalid record name. Record must be in the form of <sub>.<domain>.<tld>.'),
  410 : ('NO_SUCH_RECORD',                   'Record was not found'),
  420 : ('ADDING_RECORD_FAILED',             'Record could not be added to the zone'),
  430 : ('DELETING_RECORD_FAILED',           'Record could not be deleted from the zone'),
  440 : ('EDITING_RECORD_FAILED',            'Record could not be updated'),
}

POWERDNS_CODE_SUCCESS   = 100
POWERDNS_CODE_AUTHERR   = 200

#------------------------------------------------------------------------------
class WrapService(object):
  '''
  A wrapper around a SOAP service to check the ``Response.code``
  result and if not equal to ``100``, throws an exception. Why
  PowerDNS can't just use standard soap exceptions is beyond me.
  '''

  #----------------------------------------------------------------------------
  def __init__(self, client, service, *args, **kw):
    super(WrapService, self).__init__(*args, **kw)
    self.client  = client
    self.service = service

  #----------------------------------------------------------------------------
  def __getattr__(self, key):
    # todo: i'm *sure* there is a cleaner way of doing this...
    if key in self.__dict__:
      return self.__dict__[key]
    attr = getattr(self.service, key)
    if isinstance(attr, Method):
      def _makeCheckResponse(func):
        def _checkResponse(*args, **kw):
          resp = func(*args, **kw)
          if resp.code != POWERDNS_CODE_SUCCESS:
            msg = resp.description
            if resp.code in POWERDNS_CODES and msg == POWERDNS_CODES[resp.code][0]:
              msg = '[%s] %s' % (msg, POWERDNS_CODES[resp.code][1])
            if resp.code == POWERDNS_CODE_AUTHERR:
              raise api.AuthenticationError('%s: %s' % (resp.code, msg))
            raise api.DriverError('%s: %s' % (resp.code, msg))
          return resp
        return _checkResponse
      attr = _makeCheckResponse(attr)
    self.__dict__[key] = attr
    return attr

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
    self._service = self.service
    self.service = WrapService(self, self.service)


#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
