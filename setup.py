#!/usr/bin/env python
# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2014/02/27
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

import os, sys, setuptools
from setuptools import setup, find_packages

# require python 2.7+
if sys.hexversion < 0x02070000:
  raise RuntimeError('This package requires python 2.7 or better')

heredir = os.path.abspath(os.path.dirname(__file__))
def read(*parts, **kw):
  try:    return open(os.path.join(heredir, *parts)).read()
  except: return kw.get('default', '')

test_dependencies = [
  'nose                 >= 1.3.0',
  'coverage             >= 3.5.3',
  'globre               >= 0.1.3',
  'asset                >= 0.6.10',
]

dependencies = [
  'iniherit             >= 0.1.7',
  'dnspython            >= 1.11.1',
  'six                  >= 1.6.1',
  'blessings            >= 1.5.1',
  'aadict               >= 0.2.2',
  'requests             >= 2.5.1',
  'PyYAML               >= 3.11',
  # NOTE: this *should* be using the `suds` package, which appears to
  #       be dead. so using the suds-jurko fork for now... see
  #       https://bitbucket.org/jurko/suds
  'suds-jurko           >= 0.6',
  # 'suds                 >= 0.4',
]

entrypoints = {
  'console_scripts': [
    'dnssync            = dnssync.api.cli:main',
  ],
}

classifiers = [
  'Development Status :: 4 - Beta',
  #'Development Status :: 5 - Production/Stable',
  'Environment :: Console',
  'Intended Audience :: System Administrators',
  'Programming Language :: Python',
  'Operating System :: OS Independent',
  'Natural Language :: English',
  'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
]

setup(
  name                  = 'dnssync',
  version               = read('VERSION.txt', default='0.0.1').strip(),
  description           = 'Command line client to synchronize DNS hosted zones with local zone files',
  long_description      = read('README.rst'),
  classifiers           = classifiers,
  author                = 'metagriffin',
  author_email          = 'mg.pypi@metagriffin.net',
  url                   = 'http://github.com/metagriffin/dnssync',
  keywords              = 'dns zone synchronize download upload diff client command line cli powerdns',
  packages              = find_packages(),
  namespace_packages    = ['dnssync'],
  platforms             = ['any'],
  include_package_data  = True,
  zip_safe              = True,
  install_requires      = dependencies,
  tests_require         = test_dependencies,
  test_suite            = 'dnssync',
  entry_points          = entrypoints,
  license               = 'GPLv3+',
)

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
