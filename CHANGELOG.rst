=========
ChangeLog
=========


v0.2.2
======

* Added DomainMonster support
* Added SRV record support in API


v0.2.1
======

* Pushed PowerDNS-specific code into separate module
* Converted to namespace package
* Converted engine to use generic API for DNS hosting service drivers


v0.2.0
======

* Renamed project to "dnssync" (from "pdns")


v0.1.3
======

* Added support for "dnssync-config" local variable in zone file comments
* Added support for sub-domains that begin with an underscore, e.g.
  "_domainkey" and "_dmarc"
* Fixed handling of TXT content records


v0.1.2
======

* Removed dependency on external, no longer existing, `powerdnsclient`
  package


v0.1
====

* First version
