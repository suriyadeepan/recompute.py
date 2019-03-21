import os
import subprocess
import logging
import signal

from recompute import cmd

# setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_process_alive(pid):
  try:
    return os.kill(pid, 0) is None
  except ProcessLookupError:
    return


def is_remote_process_alive(pid, login):
  _, output = remote_execute(cmd.PROCESS_PID_LINUX.format(pid=pid), login)
  return str(pid) in output


def kill_process(pids):
  for pid in pids:
    os.kill(pid, signal.SIGTERM)


def kill_remote_process(pids, login):
  _, output = remote_execute(cmd.kill_procs(pids), login)
  return output


def execute(cmdstr, run_async=False):
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
  except:
    logger.error('\tExecution Failed!')


def async_execute(cmdstr):
  return execute(cmdstr, run_async=True)


def remote_execute(cmdstr, login, bypass_subprocess=False):
  _header = cmd.SSH_HEADER.format(password=login.password)
  _body = cmd.SSH_EXEC.format(
      username=login.username,
      host=login.host, cmd=cmdstr
      )
  if bypass_subprocess:
    _body = cmd.SSH_EXEC_PSEUDO_TERMINAL.format(
          username=login.username,
          host=login.host, cmd=cmdstr
          )
    os.system(' '.join([_header, _body]))
    return None, None

  return execute(' '.join([_header, _body]))


def remote_async_execute(cmdstr, login, logfile='/dev/null'):
  _header = cmd.SSH_HEADER.format(password=login.password)
  _body = cmd.SSH_EXEC_ASYNC.format(
      username=login.username,
      host=login.host, cmd=cmdstr,
      logfile=logfile
      )
  _, output = execute(' '.join([_header, _body]))
  # parse output to get PID of remote process
  pid = int(output.replace('\n', '').strip())
  return pid, None


def create_runner(path, commands, logfile, run_async=False, name='re.runner'):
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
