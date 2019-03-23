"""utils.py : A suite of helper functions"""

from prettytable import PrettyTable

import os
import logging
import random

# setup local configuration
LOCAL_CONFIG_DIR = '.recompute'
if not os.path.exists(LOCAL_CONFIG_DIR):
  os.makedirs(LOCAL_CONFIG_DIR)
# redirect log to
LOG = '.recompute/log'
LOG_OVERFLOW = 2000


def get_logger(name, level=logging.INFO):
  """Configure logging mechanism and return logger instance

  Parameters
  ----------
  name : str
    module name (__name__)
  level : int, optional
    Level of logging (default logging.INFO)

  Returns
  -------
  logging.Logger
    A logger instance
  """
  # . if log file doesn't exist
  # .. or if it overflows
  if not os.path.exists(LOG) or len(open(LOG).readlines()) > LOG_OVERFLOW:
    open(LOG, 'w').close()  # create anew
  logging.basicConfig(filename=LOG, filemode='a', level=level)
  return logging.getLogger(name)


# ---- logger ----
logger = get_logger(__name__)


def parse_log(log):
  """Parse log

  Parameters
  ----------
  log : str
    Contents of log file

  Returns
  -------
  str
    Parsed log file
  """
  return log  # TODO : clean up log


def tabulate_processes(processes):
  """Convert list of processes into a Pretty Table

  Parameters
  ----------
  processes : list
    List of processes (name, pid)

  Returns
  -------
  PrettyTable
    A table of processes
  """
  table = PrettyTable()
  table.field_names = [ "Index", "Name", "PID" ]
  # fabricate 0th row
  table.add_row((0, 'all', '*'))
  for idx, (name, pid) in enumerate(processes):
    table.add_row((idx + 1, name, pid))
  return table


def tabulate_instances(instances):
  """Convert a dictionary of instances into a Pretty Table

  Parameters
  ----------
  instances : dict
    Dictionary of instances

  Returns
  -------
  PrettyTable
    A table of instances
  """
  # create pretty table
  table = PrettyTable()
  # add fields
  table.field_names = [ "Machine", "Status", "GPU (MB)", "Disk (MB)" ]
  # add rows
  for instance, values in instances.items():
    table.add_row(values)
  return table


def resolve_relative_path(filename, path):
  """Convert relative path to absolute"""
  return os.path.join(path, filename)


def resolve_absolute_path(filename):
  """Fetch filename from absolute path"""
  return filename.split('/')[-1]


def chain_commands(commands):
  """Chain commands together using `&&` "and" operator

  Parameters
  ----------
  commands : list
    A list of commands to be chained together

  Returns
  -------
  str
    Chained command
  """
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
  """Parse result of `ps` command

  Parameters
  ----------
  stdout : str
    Output of running `ps` command

  Returns
  -------
  list
    A List of process id's
  """
  # ps returns nothing
  if not stdout.replace('\n', '').strip():
    return []
  # ps returns something
  return [ int(line.split()[0]) for line in stdout.split('\n')
      if line.replace('\n', '').strip()
      ]


def parse_free_results(stdout):
  """Parse results of `free` command

  Parameters
  ----------
  stdout : str
    Output of running `free` command

  Returns
  -------
  int
    Free Disk space
  """
  line = stdout.split('\n')[1]
  assert 'Mem:' in line
  return int(line.split()[3])


def rand_server_port(a=8824, b=8850):
  """Get a random integer between `a` and `b`"""
  return random.randint(a, b)


def rand_client_port(a=8850, b=8890):
  """Get a random integer between `a` and `b`"""
  return random.randint(a, b)
