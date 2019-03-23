import paramiko
import pickle
import random
import time
import os

import logging

from recompute import cmd
from recompute.process import execute, async_execute
from recompute.process import remote_execute, remote_async_execute
from recompute import process

from recompute import utils

# setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# void cache
VOID_CACHE = '.recompute/void'


def rand_server_port(a=8824, b=8850):
  return random.randint(a, b)


def rand_client_port(a=8850, b=8890):
  return random.randint(a, b)


def rand_tracker(a=999999, b=9999999, label='remote'):
    return '{label}_{idx}'.format(label=label, idx=random.randint(a, b))


def rand_token(n=12):
  import string
  return ''.join(
      random.choice(string.ascii_lowercase + string.digits)
      for _ in range(n)
      )


class Remote(object):  # think of a bubble over the bundle

  def __init__(self, instance=None, bundle=None, remote_home=None):
    """ Execution Space : The Void """

    # cache name
    self.CACHE = VOID_CACHE
    cache = None

    if not instance and not bundle:
      # read from cache
      assert os.path.exists(self.CACHE)
      cache = pickle.load(open(self.CACHE, 'rb'))
      remote_home = cache['remote_home']

    self.instance = instance if instance else cache['instance']
    self.bundle = bundle if bundle else cache['bundle']

    # create an SSH Client
    self.client = None  # self.init_client()

    # projects/ folder in remote machine
    if not remote_home:
      remote_home = os.path.join(self.get_remote_home_dir(), 'projects/')
    self.remote_home = remote_home
    # projects/project/ folder in remote machine
    self.remote_dir = os.path.join(self.remote_home, self.bundle.name)
    # projects/project/data/
    self.remote_data = os.path.join(self.remote_dir, 'data/')

    if not cache:
      # make directories in remote machine
      self.make_dirs()

    # build remote log file path
    self.logfile = os.path.join(self.remote_dir,
        '{}.log'.format(self.bundle.name)
      )
    # build local log file path
    self.local_logfile = os.path.join(
        self.bundle.path,
        self.logfile.split('/')[-1]
        )

    # list spawned proceses
    self.processes = [] if not cache else cache['processes']
    # cache void
    self.cache_()

  def get_remote_home_dir(self):
    """ Get $HOME directory path from remote system """
    pid, output = process.remote_execute('pwd', self.instance)  # [-1].strip()
    return output.replace('\n', '').strip()

  def cache_(self, name=None):
    # get cache name
    name = self.CACHE if not name else name
    # create a minimal dict of self
    void_as_dict = {
        'instance' : self.instance,
        'bundle': self.bundle,
        'remote_home' : self.remote_home,
        'processes' : self.processes
        }
    # dump dictionary
    pickle.dump(void_as_dict, open(self.CACHE, 'wb'))

  def init_client(self):
    # setup ssh client
    client = paramiko.SSHClient()
    # load local policies
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
      # connect to remote system
      client.connect(self.instance.host, username=self.instance.username,
          password=self.instance.password)
    except paramiko.AuthenticationException:
      logger.error('Authentication Failed [{}@{}]'.format(
        self.instance.username, self.instance.host
        ))
      exit()

    # attach to self
    self.client = client

    return client

  def get_client(self):
    return self.client if self.client else self.init_client()

  def make_mkcmd(self, dir_=None):
    # resolve directory to make
    dir_ = dir_ if dir_ else self.remote_dir
    # create directory in remote machine
    _header = cmd.SSH_HEADER.format(password=self.instance.password)
    _body = cmd.SSH_MAKE_DIR.format(
        username=self.instance.username,
        host=self.instance.host,
        remote_dir=dir_
        )
    # join
    return ' '.join([_header, _body])

  def make_rsync_cmd(self):
    _header = cmd.SSH_HEADER.format(password=self.instance.password)
    _body = cmd.RSYNC.format(
            deps_file=self.bundle.db,
            username=self.instance.username,
            host=self.instance.host,
            remote_dir=self.remote_dir
            )

    return ' '.join([_header, _body])

  def make_dirs(self):
    # execute make directory command from local machine
    mkcmd = self.make_mkcmd()
    logger.info(mkcmd)
    assert execute(mkcmd)
    # make data/ directory
    remote_data_ = self.make_mkcmd(self.remote_data)
    logger.info(remote_data_)
    assert execute(remote_data_)

  def rsync(self, update=False):
    """ Rsync files between local and remote systems """

    if update:  # update bundle
      self.bundle.update_dependencies()

    # execute rsync
    rsync_cmd = self.make_rsync_cmd()
    logger.info(rsync_cmd)
    return execute(rsync_cmd)

  def async_execute(self, commands, logfile=None, name='runner'):
    return self.execute(commands, run_async=True, log=True, logfile=logfile, name=name)

  def execute(self, commands, run_async=False, log=True, logfile=None, name='runner'):
    # resolve log file
    logfile = logfile if logfile else self.logfile
    # create runner
    runner = process.create_runner(self.remote_dir, commands, logfile, run_async=run_async)
    # push runner to remote
    self.copy_file_to_remote(
        os.path.join(self.bundle.path, runner),  # abs path of current dir
        self.remote_dir
        )
    # get absolute path of runner
    runner_abs_path = os.path.join(self.remote_dir, runner)
    # execute runner in remote machine
    exec_fn = remote_async_execute if run_async else remote_execute
    pid, output = exec_fn(cmd.EXEC_RUNNER.format(runner=runner_abs_path), instance=self.instance)

    # add pid to processes
    self.processes.append((name, pid))
    self.cache_()
    return pid, output

  def execute_command(self, cmdstr, run_async=False, log=False,
      logfile=None, bypass_subprocess=True):
    logger.info(cmdstr)
    # if we are running async
    if run_async:
      return process.remote_async_execute(cmdstr, self.instance, logfile)
    # --- sync execution --- #
    # execute in remote machine
    return process.remote_execute(cmdstr, self.instance,
        bypass_subprocess=bypass_subprocess)

  def async_execute_command(self, cmdstr, logfile=None):
    return self.execute_command(cmdstr, run_async=True, log=True, logfile=logfile)

  def copy_file_to_remote(self, localpath, remotepath=None):
    """ Copy file to remote machine """
    # default remote path
    remotepath = remotepath if remotepath else self.remote_data
    # build copy cmd
    _header = cmd.SSH_HEADER.format(password=self.instance.password)
    _body = cmd.SCP_TO_REMOTE.format(
        username=self.instance.username,
        host=self.instance.host,
        remotepath=remotepath,
        localpath=localpath
        )
    copy_cmd = ' '.join([_header, _body])
    # local execute scp
    execute(copy_cmd)

  def get_file_from_remote(self, remotepath, localpath=None):
    """ Copy file to local machine """
    # default local path
    localpath = localpath if localpath else self.bundle.path
    # build copy cmd
    _header = cmd.SSH_HEADER.format(password=self.instance.password)
    _body = cmd.SCP_FROM_REMOTE.format(
        username=self.instance.username,
        host=self.instance.host,
        remotepath=remotepath,
        localpath=localpath
        )
    copy_cmd = ' '.join([_header, _body])
    # execute scp command
    execute(copy_cmd)

  def get_remote_log(self, keyword=None, print_log=True):
    """ Copy log file in remote system to local machine """
    # copy to local
    self.get_file_from_remote(self.logfile, self.bundle.path)  # '.'
    return self.get_local_log(keyword, print_log)

  def get_local_log(self, keyword=None, print_log=False):
    """ Read local log file """
    # check if local log file exists
    if not os.path.exists(self.local_logfile):
      return ''

    # read from log file
    log = open(os.path.join(self.bundle.path, self.logfile.split('/')[-1])).read()

    if keyword:    # if keyword is given
      log = '\n'.join([ line for line in log.split('\n') if keyword in line])

    if print_log:  # do we print it?
      logger.info('\n{}'.format(log))

    return log

  def loop_get_remote_log(self, delay, keyword=None):
    """ Fetch log file in a loop """
    try:
      while True:  # tis a loop, my liege.
        # . get local log
        local_log = self.get_local_log(print_log=False)
        # .. get remote log
        remote_log = self.get_remote_log(print_log=False)
        # ... compare
        diff = remote_log.replace(local_log, '')
        # print the diff
        if diff.strip():  # if there is a difference
          logger.info('\n{}'.format(diff))
        # and now we wait
        time.sleep(delay)
    except KeyboardInterrupt:
      logger.info('You did this! You did this to us!!')

  def install_deps(self, update=False):
    """ Install dependencies in remote system """

    if update:  # update bundle
      self.bundle.update_dependencies()
    # install
    self.install(self.bundle.get_requirements())

  def install(self, packages):
     # make pip-install command
    pip_install_cmd = 'python3 -m pip install --user {}'.format(
        ' '.join(packages)
        )
    logger.info('\tInstall dependencies\n\t{}'.format(pip_install_cmd))

    # remote execute cmd
    logger.info('\n\t{}'.format(self.execute_command(pip_install_cmd)))

  def _header_cd(self, dir_=None):
    """ Change Directory header """
    # resolve directory to change to
    dir_ = dir_ if dir_ else self.remote_dir
    return 'cd {}'.format(dir_)

  def _header_cd_data(self):
    """ Change Directory to data/ header """
    return 'cd {}'.format(self.remote_data)

  def download(self, urls, change_to=None, run_async=False):
    """ Download from web """
    # resolve cd directory
    change_to = change_to if change_to else self.remote_data
    # build cmd header
    _cmd_header = self._header_cd(change_to)
    # build cmd body
    _cmd_body = cmd.make_wget(urls)
    # build cmd footer
    data_logfile = os.path.join(change_to, 'data.log')
    _cmd_footer = cmd.CMD_LOG_FOOTER.format(logfile=data_logfile)
    # join
    cmd_str = ' && '.join([ _cmd_header, _cmd_body ])

    if run_async:  # run (download) async
      self.async_remote_exec(cmd_str, logfile=data_logfile)
      return True

    # run (download) sync
    logger.info(self.execute_command(cmd_str + _cmd_footer))

  def get_session(self):
    """ Create a session session """
    os.system(
        cmd.SSH_INTO_REMOTE_DIR.format(
          username=self.instance.username,
          password=self.instance.password,
          host=self.instance.host,
          remote_dir=self.remote_dir
          )
        )

  def start_notebook(self, run_async=False, name='jupyter notebook', force=False):
    """ Create and connect to remote notebook server """
    # install jupyter notebook
    # self.install(['jupyter'])
    # choose a port number
    server_port_num = rand_server_port()
    # start jupyter server
    commands = [ cmd.JUPYTER_SERVER.format(port_num=server_port_num) ]
    pid, output = self.async_execute(commands, logfile='/dev/null', name=name)

    logger.info('\tStarted notebook server in remote machine :{}'.format(
      server_port_num)
      )

    # . choose a client port number
    # .. build notebook client command
    client_port_num = rand_client_port()
    cmd_local = cmd.JUPYTER_CLIENT.format(
        username=self.instance.username,
        password=self.instance.password,
        host=self.instance.host,
        client_port_num=client_port_num,
        server_port_num=server_port_num
        )

    logger.info('Starting local notebook ')
    logger.info('\thttp://localhost:{}/tree'.format(client_port_num))

    if run_async:
      pid, output = async_execute(cmd_local)

    # connect to notebook server
    return execute(cmd_local)

  def list_processes(self, print_log=False, force=False):
    if force:
      # get list of processes
      command = ' '.join([
        cmd.SSH_HEADER.format(password=self.instance.password),
        cmd.SSH_EXEC.format(username=self.instance.username, host=self.instance.host,
          cmd=cmd.PROCESS_LIST_LINUX.format(username=self.instance.username)
          )
        ])
      pid, output = execute(command)
      pids = utils.parse_ps_results(output)
      self.processes = [ (name, pid) for name, pid in self.processes if pid in pids ]
      # update cache
      self.cache_()

    if print_log:
      print('[ *] {:>20}'.format('all'))
      for i, (name, pid) in enumerate(self.processes):
        print('[{:>2}] {:>20} {:>8}'.format(i + 1, name, pid))

    logger.info(self.processes)
    return [ proc[-1] for proc in self.processes ]

  def kill(self, idx, force=False):
    pids = self.list_processes(force=force)
    if len(pids) > 0:
      procs_to_kill = pids if idx == 0 else [pids[idx - 1]]
      if len(procs_to_kill) > 0:
        process.kill_remote_process(procs_to_kill, instance=self.instance)
