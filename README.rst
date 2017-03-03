==========================
Hosted DNS Synchronization
==========================

The `dnssync` script allows DNS zones hosted at various DNS providers
to be synchronized with local bind-style text zone files. This allows
the DNS zones to be easily version-controlled, even if the service
provider does not directly support that.

Currently supported DNS service providers:

* `DomainMonster <http://domainmonster.com/>`_ (via HTML scraping)
* `PowerDNS <http://powerdns.net/>`_
* `ZoneEdit <http://zoneedit.com/>`_ (via HTML scraping)
* `Register.LY <http://register.ly/>`_ (via HTML scraping)


Project
=======

* Homepage: https://github.com/metagriffin/dnssync
* Bugs: https://github.com/metagriffin/dnssync/issues


Installation
============

.. code:: bash

  $ pip install dnssync


Usage
=====

To download a zone from PowerDNS:

.. code:: bash

  $ dnssync download --driver powerdns --param apikey={KEY} --domain {DOMAIN} {ZONEFILE}


These command line options can also be stored in a configuration file,
e.g. ``config.ini``:

.. code:: ini

  driver        = powerdns
  apikey        = {KEY}
  domain        = {DOMAIN}
  zonefile      = {ZONEFILE}

And then invoke dnssync as follows:

.. code:: bash

  $ dnssync download --config config.ini


To upload a zone:

.. code:: bash

  $ dnssync upload --config config.ini


And to show differences between the hosted zone and the local
zonefile:

.. code:: bash

  $ dnssync diff --config config.ini


And to test that a DNS server is serving the zone as specified:

.. code:: bash

  $ dnssync verify --config config.ini

Note that the ``verify`` command has some limitations in how accurate
it can be. For example, record-level TTL's cannot be extracted from
DNS (only remaining time, not total time, to expiry).


Configuration
=============

The dnssync configuration file can specify the following options:

* ``driver``:

  The driver for the specific DNS hosting service; currently supported
  values:

  * ``domainmonster``: for DomainMonster.com
  * ``powerdns``: for PowerDNS.net
  * ``zoneedit``: for ZoneEdit.com


* ``domain``:

  The name of the zone to be operated on.


* ``zonefile``:

  The filename of the local zone file. If specified in the
  configuration, it is taken to be relative to the configuration
  file. If specified on the command line, it is taken to be relative
  to the current working directory.


DomainMonster
-------------

The following options exist for the ``domainmonster`` driver:

* ``username``:

  The username of the account to log into DomainMonster with.

* ``password``:

  The password of the specified `username` account.

.. IMPORTANT::

  The `domainmonster` driver uses HTML-scraping to operate on the
  hosted zone. This means that it, unfortunately, is quite brittle and
  may break if DomainMonster changes its HTML structure. If this
  appears to be happening, please report it to
  https://github.com/metagriffin/dnssync/issues and I'll fix it ASAP.


PowerDNS
--------

The following options exist for the ``powerdns`` driver:

* ``apikey``:

  The API access key provided by PowerDNS. Note that an account must
  first be enabled (via the PowerDNS website) before it can be used.

.. IMPORTANT::

  The PowerDNS service has, as of 2016/09/29, been end-of-lifed.  That
  means that you need to already have an account and service purchased
  to be able to use this driver.


ZoneEdit
--------

The following options exist for the ``zoneedit`` driver:

* ``username``:

  The username of the account to log into ZoneEdit with.

* ``password``:

  The password of the specified `username` account.

.. IMPORTANT::

  The `zoneedit` driver uses HTML-scraping to operate on the hosted
  zone (despite what ZoneEdit advertises, they do NOT have an API to
  manage their DNS zones). This means that it, unfortunately, is quite
  brittle and may break if ZoneEdit changes its HTML structure. If
  this appears to be happening, please report it to
  https://github.com/metagriffin/dnssync/issues and I'll fix it ASAP.


Multiple Profiles
-----------------

Several different profiles can be stored in the same configuration; each
profile should have a section named after the domain. Global parameters can
be stored in the "DEFAULT" section. For example:

.. code:: ini

  [DEFAULT]

  # set some global parameters
  driver        = powerdns
  apikey        = 2f16eef6-5b1f-4d80-96f7-0237da03db48

  # set the default domain to manage
  domain        = example.com

  [example.com]
  zonefile      = example-com.zone

  [other-example.com]
  zonefile      = other-example-com.zone


Then, to upload the zones:

.. code:: bash

  # upload 'example.com'
  $ dnssync upload -c config.ini

  # upload 'other-example.com'
  $ dnssync upload -c config.ini -d other-example.com


Zonefile Local Variables
------------------------

The zonefile can also specify the configuration file via emacs-style
local variables. The configuration file specified on the command line,
however, takes precedence. For example, given the following
``example-com.zone`` zonefile:

.. code:: text

  ;; -*- coding: utf-8; dnssync-config: config.ini -*-

  $ORIGIN example.com.
  example.com. 3600 IN SOA ...
  ... more DNS records ...

The following command will pull all options from the ``config.ini``
file:

.. code:: bash

  # report differences
  $ dnssync diff example-com.zone

  # upload a new version
  $ dnssync upload example-com.zone
