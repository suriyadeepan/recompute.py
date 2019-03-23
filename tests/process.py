from recompute.instance import Instance
import pytest


@pytest.fixture
def instance():
  # --- set valid instance credentials --- #
  from recompute.instance import InstanceManager
  from recompute.config import ConfigManager
  return InstanceManager(ConfigManager()).get()


def test_is_process_alive():
  from recompute.process import is_process_alive
  import subprocess
  import os
  proc = subprocess.Popen(['sleep 60', '...'], shell=True, stdout=open(os.devnull))
  assert is_process_alive(proc.pid)
  proc.terminate()


def test_execute():
  from recompute.process import is_process_alive
  from recompute.process import execute
  pid, output = execute('ls -1a')
  assert not is_process_alive(pid)
  output_list = output.split('\n')
  assert '.' in output_list and '..' in output_list
  assert len(output_list) > 2


def test_async_execute():
  from recompute.process import is_process_alive
  from recompute.process import async_execute
  import signal
  import os
  pid, output = async_execute('sleep 60')
  assert not output
  assert is_process_alive(pid)
  os.kill(pid, signal.SIGTERM)


def test_remote_execute(instance):
  from recompute.process import remote_execute
  pid, output = remote_execute('ls -1a', instance)
  output_list = output.split('\n')
  assert '.' in output_list and '..' in output_list
  assert len(output_list) > 2


def test_remote_async_execute(instance):
  from recompute.process import remote_async_execute
  from recompute.process import is_remote_process_alive
  pid, _ = remote_async_execute('sleep 60', instance)
  assert isinstance(pid, type(42))
  assert is_remote_process_alive(pid, instance)


def test_is_remote_process_alive(instance):
  from recompute.process import is_remote_process_alive
  from recompute.process import remote_async_execute
  pid, output = remote_async_execute('sleep 60', instance)
  assert isinstance(pid, type(42))
  assert is_remote_process_alive(pid, instance)
