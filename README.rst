==========================
Hosted DNS Synchronization
==========================

The `dnssync` script allows DNS zones hosted at various DNS providers
to be synchronized with local bind-style text zone files. This allows
the DNS zones to be easily version-controlled, even if the service
provider does not directly support that.

Currently supported DNS service providers:

* `PowerDNS <http://powerdns.net/>`_
* `DomainMonster <http://domainmonster.com/>`_


Project
=======

* Homepage: https://github.com/metagriffin/dnssync
* Bugs: https://github.com/metagriffin/dnssync/issues


Installation
============

.. code-block:: bash

  $ pip install dnssync


Usage
=====

To download a zone from PowerDNS:

.. code-block:: bash

  $ dnssync download --driver powerdns --param apikey={KEY} --domain {DOMAIN} {ZONEFILE}


These command line options can also be stored in a configuration file,
e.g. ``config.ini``:

.. code-block:: ini

  driver        = powerdns 
  apikey        = {KEY}
  domain        = {DOMAIN}
  zonefile      = {ZONEFILE}

And then invoke dnssync as follows:

.. code-block:: bash

  $ dnssync download --config config.ini


To upload a zone:

.. code-block:: bash

  $ dnssync upload --config config.ini


And to show differences between the hosted zone and the local
zonefile:

.. code-block:: bash

  $ dnssync diff --config config.ini


Configuration
=============

The dnssync configuration file can specify the following options:

* ``driver``:

  The driver for the specific DNS hosting service; currently supported
  values:

  * ``powerdns``: for PowerDNS.net


* ``domain``: 

  The name of the zone to be operated on.


* ``zonefile``: 

  The filename of the local zone file. If specified in the
  configuration, it is taken to be relative to the configuration
  file. If specified on the command line, it is taken to be relative
  to the current working directory.


PowerDNS
--------

The following options exist for the ``powerdns`` driver:

* ``apikey``: 

  The API access key provided by PowerDNS. Note that an account must
  first be enabled (via the PowerDNS website) before it can be used.


DomainMonster
-------------

The following options exist for the ``domainmonster`` driver:

* ``username``: 

  The username of the account to log into DomainMonster with.

* ``password``:

  The password of the specified `username` account.


Multiple Profiles
-----------------

Several different profiles can be stored in the same configuration; each
profile should have a section named after the domain. Global parameters can
be stored in the "DEFAULT" section. For example:

.. code-block:: ini

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

.. code-block:: bash

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

.. code-block:: text

  ;; -*- coding: utf-8; dnssync-config: config.ini -*-

  $ORIGIN example.com.
  example.com. 3600 IN SOA ...
  ... more DNS records ...

The following command will pull all options from the ``config.ini``
file:

.. code-block:: bash

  # report differences
  $ dnssync diff example-com.zone

  # upload a new version
  $ dnssync upload example-com.zone
