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

from __future__ import print_function

import sys
import argparse
import iniherit
import ConfigParser
import logging
import re
import os.path
from aadict import aadict

from .i18n import _
from . import engine
from . import error

#------------------------------------------------------------------------------

iniherit.mixin.install_globally()

WARRANTY = '''\
This software is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This software is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see http://www.gnu.org/licenses/.
'''

# todo: use real parsers for these...
localvars_cre   = re.compile(r'-\*-.*dnssync-config:\s+([^\s]+).*-\*-')
localorigin_cre = re.compile(r'\$ORIGIN\s+([^\s]+)')

#------------------------------------------------------------------------------
# command aliasing, shamelessly scrubbed from:
#   https://gist.github.com/sampsyo/471779
# (with some adjustments to make aliases only show up in non-summary help)
# todo: in conjunction with aliases, use 'only-match' selection system...
#       ==> i.e. alias 'rotate' to 'set' and only-match 'rot' and 's'...
class AliasedSubParsersAction(argparse._SubParsersAction):
  fuzzy = True
  class _AliasedPseudoAction(argparse.Action):
    def __init__(self, name, aliases, help):
      dest = name
      if aliases:
        dest += ' (%s)' % ','.join(aliases)
      sup = super(AliasedSubParsersAction._AliasedPseudoAction, self)
      sup.__init__(option_strings=[], dest=dest, help=help)
  def __init__(self, *args, **kw):
    super(AliasedSubParsersAction, self).__init__(*args, **kw)
    self.aliases = []
  def add_parser(self, name, **kwargs):
    if 'aliases' in kwargs:
      aliases = kwargs['aliases']
      del kwargs['aliases']
    else:
      aliases = []
    parser = super(AliasedSubParsersAction, self).add_parser(name, **kwargs)
    # Make the aliases work.
    for alias in aliases:
      self._name_parser_map[alias] = parser
    self.aliases.extend(aliases)
    # Make the help text reflect them, first removing old help entry.
    if 'help' in kwargs:
      help = kwargs.pop('help')
      self._choices_actions.pop()
      pseudo_action = self._AliasedPseudoAction(name, aliases, help)
      self._choices_actions.append(pseudo_action)
    return parser

#------------------------------------------------------------------------------
class AliasSuppressingHelpFormatter(argparse.HelpFormatter):
  def _metavar_formatter(self, action, default_metavar):
    tmp = None
    if isinstance(action, AliasedSubParsersAction):
      tmp = action.choices
      action.choices = [ch for ch in tmp if ch not in action.aliases]
    ret = super(AliasSuppressingHelpFormatter, self)._metavar_formatter(action, default_metavar)
    if tmp is not None:
      action.choices = tmp
    return ret

#------------------------------------------------------------------------------
class FuzzyChoiceArgumentParser(argparse.ArgumentParser):
  def __init__(self, *args, **kw):
    if 'formatter_class' not in kw:
      kw['formatter_class'] = AliasSuppressingHelpFormatter
    super(FuzzyChoiceArgumentParser, self).__init__(*args, **kw)
  def _fuzzy_get_value(self, action, value):
    maybe = [item for item in action.choices if item.startswith(value)]
    if len(maybe) == 1:
      return maybe[0]
    match = re.compile('^' + '.*'.join([re.escape(ch) for ch in value]))
    maybe = [item for item in action.choices if match.match(item)]
    if len(maybe) == 1:
      return maybe[0]
    return None
  def _get_value(self, action, arg_string):
    ret = None
    if getattr(action, 'fuzzy', False) \
        and getattr(action, 'choices', None) is not None \
        and arg_string not in action.choices:
      ret = self._fuzzy_get_value(action, arg_string)
    if ret is None:
      ret = super(FuzzyChoiceArgumentParser, self)._get_value(action, arg_string)
    if ret in getattr(action, 'aliases', []) \
        and isinstance(action, AliasedSubParsersAction):
      # todo: this is not very "generalized"...
      ret = action.choices[ret].prog.split()[-1]
    return ret

#------------------------------------------------------------------------------
class LogFmt(logging.Formatter):
  def lvlstr(self, level):
    if level >= logging.CRITICAL : return '[**] CRITICAL:'
    if level >= logging.ERROR    : return '[**] ERROR:'
    if level >= logging.WARNING  : return '[++] WARNING:'
    if level >= logging.INFO     : return '[--] INFO:'
    # if level >= logging.DEBUG    : return '[  ] DEBUG:'
    return '[  ]'
  def format(self, record):
    msg = record.getMessage()
    #pfx = '%s|%s: ' % (self.levelString[record.levelno], record.name)
    pfx = self.lvlstr(record.levelno) + ' '
    return pfx + ('\n' + pfx).join(msg.split('\n'))

def LogRecord_getMessage_i18n(self):
  tmp = self.args
  self.args = None
  msg = self._real_getMessage()
  self.args = tmp
  if tmp:
    return _(msg) % tmp
  return _(msg)

logging.LogRecord._real_getMessage = logging.LogRecord.getMessage
logging.LogRecord.getMessage = LogRecord_getMessage_i18n

#------------------------------------------------------------------------------
def main(args=None):

  common = argparse.ArgumentParser(add_help=False)

  common.add_argument(
    _('-v'), _('--verbose'),
    dest='verbose', action='count', default=0,
    help=_('increase verbosity (can be specified multiple times)'))

  common.add_argument(
    _('-c'), _('--config'), metavar=_('FILENAME'),
    dest='config', default=None,
    help=_('configuration filename'))

  common.add_argument(
    _('-D'), _('--driver'), metavar=_('DRIVERNAME'),
    dest='driver', default=None,
    help=_('driver type (e.g. "powerdns", "domainmonster")'))

  common.add_argument(
    _('-d'), _('--domain'), metavar=_('ZONENAME'),
    dest='domain', default=None,
    help=_('specify the domain name (i.e. zone name) to operate on'))

  common.add_argument(
    _('-p'), _('--param'), metavar=_('NAME=VALUE'),
    dest='params', default=[], action='append',
    help=_('set and/or override the driver parameter named'
           ' "NAME" to "VALUE"'))

  common.add_argument(
    _('--warranty'),
    dest='warranty', default=False, action='store_true',
    help=_('display the %(prog)s warranty'))

  cli = FuzzyChoiceArgumentParser(
    parents     = [common],
    description = _('Synchronize hosted DNS zones with local zone files.'),
  )

  cli.register('action', 'parsers', AliasedSubParsersAction)

  subcmds = cli.add_subparsers(
    dest='command',
    title=_('Commands'),
    help=_('command (use "{} [COMMAND] --help" for details)', '%(prog)s'))

  # LIST command
  subcli = subcmds.add_parser(
    _('list'), #aliases=('ls',),
    parents=[common],
    help=_('list the zones hosted by a DNS service'))
  subcli.set_defaults(command='list')

  # DOWNLOAD command
  subcli = subcmds.add_parser(
    _('download'), aliases=('get',),
    parents=[common],
    help=_('download a zone from a hosted DNS service'))
  subcli.add_argument(
    'zonefile', metavar=_('ZONEFILE'),
    nargs='?',
    help=_('the filename of the local zone file'))
  subcli.set_defaults(command='download')

  # UPLOAD command
  subcli = subcmds.add_parser(
    _('upload'), aliases=('set',),
    parents=[common],
    help=_('upload a zone to a hosted DNS service'))
  subcli.add_argument(
    'zonefile', metavar=_('ZONEFILE'),
    nargs='?',
    help=_('the filename of the local zone file'))
  subcli.set_defaults(command='upload')

  # DIFF command
  subcli = subcmds.add_parser(
    _('diff'), aliases=('changes',),
    parents=[common],
    help=_('show differences between the hosted DNS zone and'
           ' a local zone file'))
  subcli.add_argument(
    'zonefile', metavar=_('ZONEFILE'),
    nargs='?',
    help=_('the filename of the local zone file'))
  subcli.set_defaults(command='diff')

  # todo: if only "--warranty" is specified, parse_args aborts... therefore
  #       adding hack here... note that this is still not "perfect", since
  #       the args may be "-v --warranty", which would also abort. ugh.
  #       but i can't do '--warranty' in args because that would fail
  #       "-c --warranty", i.e. the filename is named "--warranty", but...
  if args == None:
    args = sys.argv[1:]
  if args == ['--warranty']:
    # bogus injection of command to make the parser happy...
    args = ['diff', '--warranty']

  options = cli.parse_args(args=args)
  params  = aadict(par.split('=', 1) for par in options.params)
  params.driver = options.driver
  params.domain = options.domain

  if options.warranty:
    sys.stdout.write(WARRANTY)
    return 0

  rootlog = logging.getLogger()
  rootlog.setLevel(logging.ERROR)
  handler = logging.StreamHandler()
  handler.setFormatter(LogFmt())
  rootlog.addHandler(handler)
  if options.verbose == 1    : rootlog.setLevel(logging.INFO)
  elif options.verbose == 2  : rootlog.setLevel(logging.DEBUG)
  elif options.verbose > 2   : rootlog.setLevel(1)

  if getattr(options, 'zonefile', None) and os.path.exists(options.zonefile):
    with open(options.zonefile, 'rb') as fp:
      data = fp.read()
      if not options.config:
        match = localvars_cre.search(data)
        if match:
          options.config = os.path.join(
            os.path.dirname(options.zonefile), match.group(1))
      if not options.domain:
        # todo: perhaps use dns.zone for this?...
        match = localorigin_cre.search(data)
        if match:
          options.domain = params.domain = match.group(1)

  if options.config:
    config = ConfigParser.SafeConfigParser()
    config.optionxform = str.lower
    config.read(options.config)
    section = options.domain
    if not section and config.has_option('DEFAULT', 'domain'):
      section = config.get('DEFAULT', 'domain')
    if not config.has_section(section):
      section = 'DEFAULT'

    # TODO: generalize this...
    for attr in ('driver', 'apikey', 'domain', 'username', 'password'):
      if params.get(attr) is None:
        if config.has_option(section, attr):
          params[attr] = config.get(section, attr)
    # /TODO

    if not getattr(options, 'zonefile', None):
      if config.has_option(section, 'zonefile'):
        # TODO: make relative to config...
        options.zonefile = config.get(section, 'zonefile')

  if not params.driver:
    cli.error(_('required parameter "driver" not specified'))

  try:
    module = getattr(__import__('dnssync.' + params.driver), params.driver)
  except ImportError as err:
    print(_('[**] ERROR: unknown/unavailable driver "{}"', params.driver), file=sys.stderr)
    return 10

  try:
    driver = module.Driver(params)
    return engine.run(options.command, driver, options)
  except error.Error as err:
    print(_('[**] ERROR: {}: {}', err.__class__.__name__, err.message), file=sys.stderr)
    return 20


#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
