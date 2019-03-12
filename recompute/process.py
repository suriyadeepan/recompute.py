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


def kill_process(pid):
  return os.kill(pid, signal.SIGTERM)


def kill_remote_process(pid):
  _, output = remote_execute(cmd.KILL_PROCESS.format(pid))
  return output


def execute(cmdstr, run_async=False):
  # set stdout PIPE
  stdout = open(os.devnull) if run_async else subprocess.PIPE
  # create process
  process = subprocess.Popen([cmdstr, '...'], stdout=stdout, shell=True)

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


def remote_execute(cmdstr, login):
  _header = cmd.SSH_HEADER.format(password=login.password)
  _body = cmd.SSH_EXEC.format(
      username=login.username,
      host=login.host, cmd=cmdstr
      )
  return execute(' '.join([_header, _body]))


def remote_async_execute(cmdstr, login):
  _header = cmd.SSH_HEADER.format(password=login.password)
  _body = cmd.SSH_EXEC_ASYNC.format(
      username=login.username,
      host=login.host, cmd=cmdstr
      )
  _, output = execute(' '.join([_header, _body]))
  # parse output to get PID of remote process
  pid = int(output.replace('\n', '').strip())
  return pid, None
