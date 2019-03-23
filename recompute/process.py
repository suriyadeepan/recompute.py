"""process.py

A suite of functions to execute commands in local and remote machines,
and to keep track (manage) of created processes.

"""
import os
import subprocess
import logging
import signal

from recompute import cmd

# setup logger
logger = logging.getLogger(__name__)


def is_process_alive(pid):
  """Check if a process corresponding to `pid` is alive

  Parameters
  ----------
  pid : int
    Process id

  Returns
  -------
    bool
      `True` if the process is alive, `False` otherwise
  """
  try:
    return os.kill(pid, 0) is None
  except ProcessLookupError:
    return


def is_remote_process_alive(pid, instance):
  """Check if a process is alive in remote device

  Parameters
  ----------
  pid : int
    Process id
  instance : instance.Instance
    an Instance object (remote device) to run process on

  Returns
  -------
    bool
      `True` if the process is alive in remote device
      `False` otherwise
  """
  _, output = remote_execute(cmd.PROCESS_PID_LINUX.format(pid=pid), instance)
  return str(pid) in output


def kill_process(pids):
  """Kill processes based on their pids

  Parameters
  ----------
  pids : list
    A list of process id's to kill
  """
  for pid in pids:
    os.kill(pid, signal.SIGTERM)


def kill_remote_process(pids, instance):
  """Kill processes in remote device (`instance`)

  Parameters
  ----------
  pids : list
    A list of process id's to kill
  instance : instance.Instance
    Instance object corresponding to remote device

  Returns
  -------
  str
    Result of `kill` command
  """
  _, output = remote_execute(cmd.kill_procs(pids), instance)
  return output


def fetch_stderr(cmdstr):
  """Fetch STDERR from executing `cmdstr`

  Parameters
  ----------
  cmdstr : str
    Command to be executed

  Returns
  -------
  str
    STDERR of executed command
  """
  # create process
  process = subprocess.Popen([cmdstr, '...'],
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      shell=True)
  stdout, stderr = process.communicate()
  logger.info(cmdstr)
  # read from stderr
  logger.info('ERR : {}'.format(stderr.decode('utf-8')))
  return stderr.decode('utf-8')


def execute(cmdstr, run_async=False):
  """Execute `cmdstr` and return results

  Parameters
  ----------
  cmdstr : str
    Command to be executed
  run_async : bool, optional
    When set to `True` the command is executed asynchronously
    When set to `False`, blocking execution happens (default False)

  Returns
  -------
  pid : int
    Process id of command executed
  output : str
    STDOUT of execution as a string
    `None` is returned when executed asynchronously
  """
  # set stdout PIPE
  stdout = open(os.devnull) if run_async else subprocess.PIPE
  # create process
  process = subprocess.Popen([cmdstr, '...'], stdout=stdout, shell=True)
  logger.info(cmdstr)

  if run_async:  # return PID if running async
    return process.pid, None

  try:  # else wait for process to complete
    # get stdout
    output_bytes, error = process.communicate()
    output_str = output_bytes.decode('utf-8')
    logger.info(output_str)
    return process.pid, output_str
  except KeyboardInterrupt:
    logger.error('Keyboard Interrupt')
    return None, None
  except Exception:
    logger.error('Execution Failed!')
    return None, None


def async_execute(cmdstr):
  """Execute `cmdstr` asynchronously

  Parameters
  ----------
  cmdstr : str
    Command to be executed

  Returns
  -------
  pid : int
    Process id of command executed
  output : NoneType
    None
  """
  return execute(cmdstr, run_async=True)


def remote_execute(cmdstr, instance, bypass_subprocess=False):
  """Execute `cmdstr` in remote device given by `instance`

  Parameters
  ----------
  cmdstr : str
    Command to be executed
  instance : instance.Instance
    Instance of remote device
  bypass_subprocess : bool, optional
    When set to `True`, `os.system` is used for execution, (None, None) is returned
    When set to `False`, subprocess module is used for execution (default False)

  Returns
  -------
  tuple
    (pid, output) Process id and STDOUT of execution
  """
  _header = cmd.SSH_HEADER.format(password=instance.password)
  _body = cmd.SSH_EXEC.format(
      username=instance.username,
      host=instance.host, cmd=cmdstr
      )
  if bypass_subprocess:
    _body = cmd.SSH_EXEC_PSEUDO_TERMINAL.format(
          username=instance.username,
          host=instance.host, cmd=cmdstr
          )
    os.system(' '.join([_header, _body]))
    return None, None

  return execute(' '.join([_header, _body]))


def remote_async_execute(cmdstr, instance, logfile='/dev/null'):
  """Execute `cmdstr` in remote device given by `instance`

  Parameters
  ----------
  cmdstr : str
    Command to be executed
  instance : instance.Instance
    Instance of remote device
  bypass_subprocess : bool
    When set to `True`, `os.system` is used for execution, (None, None) is returned
    When set to `False`, subprocess module is used for execution

  Returns
  -------
  tuple
    (pid, output) `pid` contains the process id of command executed
    `output` is always `None` for aysnc execution
  """
  _header = cmd.SSH_HEADER.format(password=instance.password)
  _body = cmd.SSH_EXEC_ASYNC.format(
      username=instance.username,
      host=instance.host, cmd=cmdstr,
      logfile=logfile
      )
  _, output = execute(' '.join([_header, _body]))
  # parse output to get PID of remote process
  pid = int(output.replace('\n', '').strip())
  return pid, None


def create_runner(path, commands, logfile, run_async=False, name='re.runner'):
  """Create a bash script for executing `commands` sequentially in remote system

  Parameters
  ----------
  path : str
    Path in remote device, from where `commands` should be executed
  commands : list
    A list of commands to be executed
  logfile : str
    A file where the output of execution should be redirected
  run_async : bool, optional
    When set to `True` the script is executed asynchronously
    When set to `False`, blocking execution happens (default False)
  name : str, optional
    Name of the script which contains `commands`
    The script that will be executed

  Returns
  -------
  str
    Name of the script
  """
  # . set traps
  # .. change to path
  lines = cmd.make_traps() + [ cmd.CD.format(path=path) ]
  # async execution
  for i, command in enumerate(commands):
    if run_async:  # redirect stdout/stderr to log file
      command = cmd.REDIRECT_STDOUT.format(command=command, logfile=logfile)
      if i < len(commands) - 1:
        command = '{} &'.format(command)  # push to background
      else:  # add EOF to log if last command
        command = '({} && echo EOF >> {}) &'.format(command, logfile)
    # add to list of lines
    lines.append(command)
  # end with wait if "run_async"
  lines = lines if not run_async else lines + [ cmd.WAIT ]
  # lines = lines + [ cmd.WAIT ]
  # write to disk
  logger.info('Write to file')
  with open(name, 'w') as f:
    for line in lines:
      logger.info(line)
      f.write(line)
      f.write('\n')

  return name
