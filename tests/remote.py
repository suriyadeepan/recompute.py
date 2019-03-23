import pytest
from recompute.remote import Remote
from recompute.bundle import Bundle

import os


@pytest.fixture
def remote():
  from recompute.instance import InstanceManager
  from recompute.config import ConfigManager
  instance = InstanceManager(ConfigManager()).get()
  bundle = Bundle()
  r = Remote(instance, bundle)
  r.rsync()
  r.install_deps()
  return r


@pytest.fixture
def cremote():  # cached remote
  return Remote()


def test_cache(remote):
  import pickle
  assert os.path.exists(remote.CACHE)
  assert pickle.load(open(remote.CACHE, 'rb'))


def test_execute_command(cremote):
  pid, output = cremote.execute_command(
      'ls -1 {}'.format(cremote.remote_dir),
      bypass_subprocess=False
      )
  assert 'tests' in [ line.strip() for line in output.split('\n') ]


def test_async_execute_command(cremote):
  from recompute.process import is_remote_process_alive
  pid, output = cremote.async_execute_command(
      'sleep 10'.format(cremote.remote_dir)
      )
  assert pid
  # check if such a process exists
  assert is_remote_process_alive(pid, cremote.instance)


def test_execute(cremote):
  pid, output = cremote.execute(['python3 -c "print(42)"'])
  assert int(output.strip().replace('\n', '')) == 42


def test_execute_chained(cremote):
  pid, output = cremote.execute([
    'python3 -c "print(4)"', 'python3 -c "print(2)"'
    ])
  assert int(output.strip().replace('\n', '')) == 42


def test_async_execute(cremote):
  from time import sleep
  pid, output = cremote.async_execute(['python3 -c "print(42)"'])
  sleep(5)
  assert pid
  log = cremote.get_remote_log()
  assert '42' in log
  eof = [ line for line in log.split('\n') if line.strip() ][-1]
  assert eof == 'EOF'


def test_remote_home(cremote):
  _, pwd_output = cremote.execute_command('pwd', bypass_subprocess=False)
  remote_home = pwd_output.strip().replace('\n', '')
  assert os.path.normpath(cremote.remote_home) == \
      os.path.join(remote_home, 'projects')


def test_list_processes(cremote):
  pid, output = cremote.async_execute(['sleep 60'])
  assert len(cremote.list_processes(print_log=True, force=True)) > 0


def test_kill_all(cremote):
  from time import sleep
  cremote.kill(0, force=True)
  sleep(10)
  assert len(cremote.list_processes(print_log=True, force=True)) == 0


def test_push(cremote):
  from recompute.process import execute
  with open('to_be_pushed.txt', 'w') as f:
    f.write('42')
  cremote.copy_file_to_remote(
      os.path.join(cremote.bundle.path, 'to_be_pushed.txt'),
      cremote.remote_dir
      )
  pid, output = cremote.execute_command('ls {}'.format(cremote.remote_dir),
      bypass_subprocess=False)
  assert 'to_be_pushed.txt' in output
  pid, output = execute('rm {}'.format(
    os.path.join(cremote.bundle.path, 'to_be_pushed.txt')
    ))
  pid, output = cremote.execute_command('rm {}'.format(
    os.path.join(cremote.remote_dir, 'to_be_pushed.txt')),
    bypass_subprocess=False
    )


def test_pull(cremote):
  from recompute.process import execute
  remote_file = os.path.join(cremote.remote_dir, 'to_be_pulled.txt')
  pid, output = cremote.execute_command(
      'touch {}'.format(remote_file)
      )
  cremote.get_file_from_remote(
      os.path.join(remote_file),
      cremote.bundle.path
      )
  pid, output = execute('ls {}'.format(cremote.bundle.path))
  assert 'to_be_pulled.txt' in output
  pid, output = execute('rm {}'.format(
    os.path.join(cremote.bundle.path, 'to_be_pulled.txt')
    ))
  pid, output = cremote.execute_command('rm {}'.format(
    os.path.join(cremote.remote_dir, 'to_be_pulled.txt')),
    bypass_subprocess=False
    )
