import os
import logging

# setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def resolve_relative_path(filename, path):
  return os.path.join(path, filename)


def resolve_absolute_path(filename):
  return filename.split('/')[-1]


def chain_commands(commands):
  # separate them
  if isinstance(commands, type('42')):
    commands = commands.split('&&')
  # get root command
  root = commands[0]
  # add exec to subsequent commands
  subseq = [ 'exec {}'.format(command) for command in commands[1:] ]
  # chain them
  return root + ' ' + ' && '.join(subseq)


def parse_ps_results(stdout):
  return [ int(line.split(' ')[0].strip())
      for line in stdout.split('\n')
      if line.split(' ')[0].strip()
      ]
