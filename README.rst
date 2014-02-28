============================
PowerDNS Command Line Client
============================

The `pdns` script allows DNS zones hosted at PowerDNS to be synchronized
with local bind-style zone files via the PowerDNS API.


Project
=======

* Homepage: https://github.com/metagriffin/pdns
* Bugs: https://github.com/metagriffin/pdns/issues


Installation
============

.. code-block:: bash

  $ pip install pdns


Usage
=====

To download a zone:

.. code-block:: bash

  $ pdns download --apikey {KEY} --domain {DOMAIN} {ZONEFILE}


These command line options can also be stored in a configuration file,
e.g. ``config.ini``:

.. code-block:: ini

  apikey        = {KEY}
  domain        = {DOMAIN}
  zonefile      = {ZONEFILE}

And then invoke pdns as follows:

.. code-block:: bash

  $ pdns download --config config.ini


To upload a zone:

.. code-block:: bash

  $ pdns upload --config config.ini


And to show differences between the hosted zone and the local
zonefile:

.. code-block:: bash

  $ pdns diff --config config.ini


Configuration
=============

The pdns configuration file can specify the following options:

* ``apikey``: 

  The API access key provided by PowerDNS. Note that an account must
  first be enabled (via the PowerDNS website) before it can be used.

* ``domain``: 

  The name of the zone to be operated on.

* ``zonefile``: 

  The filename of the local zone file. If specified in the
  configuration, it is taken to be relative to the configuration
  file. If specified on the command line, it is taken to be relative
  to the current working directory.


Several different profiles can be stored in the same configuration; each
profile should have a section named after the domain. Global parameters can
be stored in the "DEFAULT" section. For example:

.. code-block:: ini

  [DEFAULT]

  # set some global parameters
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
  $ pdns upload -c config.ini

  # upload 'other-example.com'
  $ pdns upload -c config.ini -d other-example.com
