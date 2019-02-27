import subprocess
import paramiko
import pickle
import random
import time
import os

import logging
from threading import Timer

from recompute import cmd

# setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def local_exec(cmd, timeout=10):
  process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
  timer = Timer(timeout, process.kill)
  try:
    timer.start()
    output, error = process.communicate()
    return output if output else True
  except:
    logger.error('\tExecution Failed!')
  finally:
    timer.cancel()


def local_async_exec(cmd, logfile='/dev/null'):
  # cmd footer
  _cmd_footer = '> {logfile} 2>{logfile} &'
  # update command
  cmd = ' '.join([cmd, _cmd_footer])
  # create process
  process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, shell=True)
  try:
    output, error = process.communicate()
    logger.info(str(output))
    logger.info(str(error))
    return process.pid
  except:
    logger.error('\tExecution Failed!')


def remote_exec(cmd, login):
  _header = 'sshpass -p {password}'.format(password=login.password)
  _body = 'ssh {username}@{host} {cmd}'.format(
      username=login.username,
      host=login.host,
      cmd=cmd
      )
  return local_exec(' '.join([_header, _body]))


class Bundle(object):

  def __init__(self, name=None):
    # get current path
    self.path = os.path.abspath('.')
    # get name of current directory if custom name isn't given
    self.name = name if name else self.path.split('/')[-1]
    # local db
    self.db = '.recompute/rsync.db'  # TODO : let's not hardcode this
    # update bundle dependencies
    self.update_dependencies()

  def update_dependencies(self):
    """ Update dependencies """
    # get a list of files (local dependencies)
    self.files = list(self.get_local_deps())
    # create a file containing list of dependencies
    self.populate_requirements()
    # get a list of dependencies (python packages)
    self.requirements = self.get_requirements()
    # create a file containting list of local dependencies
    self.populate_local_deps()

  def get_local_deps(self):
    """ Run a search for *.py files in current directory """
    for dirpath, dirnames, filenames in os.walk("."):
      for filename in [f for f in filenames if f.endswith(".py")]:
        yield os.path.join(dirpath, filename)

  def populate_local_deps(self):
    """ Write local dependencies to file """
    with open(self.db, 'w') as db:
      for filename in self.files:
        logger.debug(filename)
        db.write(filename)
        db.write('\n')

  def populate_requirements(self):
    # . get a list of pip packages
    # .. write to requirements.txt
    assert local_exec('pipreqs . --force')
    # add pytest to requirements.txt
    with open('requirements.txt', 'a') as f_req:
      f_req.write('\npytest')

  def get_requirements(self):
    return [ line.replace('\n', '')
        for line in open('requirements.txt').readlines()
        if line.replace('\n', '')
        ]


class ExecSpace(object):  # think of a bubble over the bundle

  def __init__(self, login=None, bundle=None, remote_home=None):
    """ Execution Space : The Void """

    # cache name
    self.CACHE = '.recompute/void'

    if not login and not bundle:
      # read from cache
      assert os.path.exists(self.CACHE)
      cache = pickle.load(open(self.CACHE, 'rb'))
      remote_home = cache['remote_home']

    self.login = login if login else cache['login']
    self.bundle = bundle if bundle else cache['bundle']

    # create an SSH Client
    self.client = self.init_client()
    assert self.client  # make sure connection is established

    # ~/projects/ folder in remote machine
    self.remote_home = remote_home if remote_home else '~/espace/'
    # ~/projects/project/ folder in remote machine
    self.remote_dir = os.path.join(self.remote_home, self.bundle.name)
    # ~/projects/project/data/
    self.remote_data = os.path.join(self.remote_dir, 'data/')

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
    self.processes = []

    # cache void
    self.cache_()

  def cache_(self, name=None):
    # get cache name
    name = self.CACHE if not name else name
    # create a minimal dict of self
    void_as_dict = {
        'login' : self.login,
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
      client.connect(self.login.host, username=self.login.username,
          password=self.login.password)
    except paramiko.AuthenticationException:
      logger.error('Authentication Failed [{}@{}]'.format(
        self.login.username, self.login.host
        ))
      exit()

    return client

  def make_mkcmd(self, dir_=None):
    # resolve directory to make
    dir_ = dir_ if dir_ else self.remote_dir
    # create directory in remote machine
    _header = 'sshpass -p {password}'.format(password=self.login.password)
    _body = 'ssh {username}@{host} mkdir -p {remote_dir}'.format(
        username=self.login.username,
        host=self.login.host,
        remote_dir=dir_
        )

    return ' '.join([_header, _body])

  def make_rsync_cmd(self):
    _header = 'sshpass -p {password}'.format(password=self.login.password)
    _body = 'rsync -a --files-from={deps_file} . \
        {username}@{host}:{remote_dir}'.format(
            deps_file=self.bundle.db,
            username=self.login.username,
            host=self.login.host,
            remote_dir=self.remote_dir
            )

    return ' '.join([_header, _body])

  def sync(self, update=False):
    """ Rsync files between local and remote systems """

    if update:  # update bundle
      self.bundle.update_dependencies()

    # execute make directory command from local machine
    assert local_exec(self.make_mkcmd())
    # make data/ directory
    assert local_exec(self.make_mkcmd(self.remote_data))
    # execute rsync
    return local_exec(self.make_rsync_cmd())

  def remote_exec(self, cmd):
    """ Execute command in remote machine via `client` """
    stdin, stdout, stderr = self.client.exec_command(cmd)
    output = [ line.strip('\n') for line in stdout ]

    if len(output) == 1:  # one-liners
      return output[-1]

    return output if len(output) > 0 else None

  def async_remote_exec(self, cmd, logfile=None):
    """ Async execute command in remote machine """

    # resolve which logfile to write to
    logfile = logfile if logfile else self.logfile

    # open a channel
    channel = self.client.get_transport().open_session()
    # add sync footer
    async_footer = ' 2>{} &'.format(logfile)
    # execute command async
    channel.exec_command(cmd + async_footer)
    return True

  def copy_file_to_remote(self, localpath, remotepath=None):
    """ Copy file to remote machine """

    # default remote path
    remotepath = remotepath if remotepath else self.remote_data

    # build copy cmd
    _header = 'sshpass -p {password}'.format(password=self.login.password)
    _body = 'scp -r {localpath} {username}@{host}:{remotepath}'.format(
        username=self.login.username,
        host=self.login.host,
        remotepath=remotepath,
        localpath=localpath
        )
    copy_cmd = ' '.join([_header, _body])

    return local_exec(copy_cmd)

  def get_file_from_remote(self, remotepath, localpath=None):
    """ Copy file to local machine """

    # default local path
    localpath = localpath if localpath else self.bundle.path

    # build copy cmd
    _header = 'sshpass -p {password}'.format(password=self.login.password)
    _body = 'scp -r {username}@{host}:{remotepath} {localpath}'.format(
        username=self.login.username,
        host=self.login.host,
        remotepath=remotepath,
        localpath=localpath
        )
    copy_cmd = ' '.join([_header, _body])

    return local_exec(copy_cmd)

  def log_remote_exec(self, cmd, logfile=None):
    """ Log execution output and copy log to local machine """

    # resolve which logfile to write to
    logfile = logfile if logfile else self.logfile

    # add command sequence header to `cmd`
    _cmd_seq_header = 'cd {}'.format(self.remote_dir)
    cmd = ' && '.join([ _cmd_seq_header, cmd ])

    # execute command and log to logfile
    self.remote_exec('{cmd} > {logfile} 2>{logfile}'.format(
      cmd=cmd, logfile=logfile)
      )

    # copy to local
    self.get_file_from_remote(logfile, self.bundle.path)  # '.'

    logger.info('\n\n{}'.format(
      open(os.path.join(self.bundle.path, logfile.split('/')[-1])).read()
      ))

  def log_async_remote_exec(self, cmd, logfile=None):
    """ Log execution output and copy log to local machine """

    # resolve which logfile to write to
    logfile = logfile if logfile else self.logfile

    # add command sequence header to `cmd`
    _cmd_seq_header = 'cd {}'.format(self.remote_dir)
    cmd = ' && '.join([ _cmd_seq_header, cmd ])

    # execute command
    self.async_remote_exec('{cmd} > {logfile}'.format(
      cmd=cmd, logfile=self.logfile)
      )

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

    # make pip-install command
    pip_install_cmd = 'python3 -m pip install --user {}'.format(
        ' '.join(self.bundle.get_requirements())
        )
    logger.info('\tInstall dependencies\n\t{}'.format(pip_install_cmd))

    # remote execute cmd
    logger.info('\n\t{}'.format(self.remote_exec(pip_install_cmd)))

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
    _cmd_body = cmd._WGET(urls)
    # build cmd footer
    data_logfile = os.path.join(change_to, 'data.log')
    _cmd_footer = ' > {logfile} 2>{logfile}'.format(logfile=data_logfile)
    # join
    cmd_str = ' && '.join([ _cmd_header, _cmd_body ]) + _cmd_footer

    if run_async:  # run (download) async
      self.async_remote_exec(cmd_str, logfile=data_logfile)
      return True

    # run (download) sync
    logger.info(self.remote_exec(cmd_str))

    # get log file from remote to local machine
    self.get_file_from_remote(data_logfile, self.bundle.path)

  def get_session(self):
    """ Create a session session """
    os.system(
        'sshpass -p {password} ssh -t {username}@{host} \
            "cd {remote_dir}; exec \\$SHELL --login"'.format(
          username=self.login.username,
          password=self.login.password,
          host=self.login.host,
          remote_dir=self.remote_dir
          )
        )

  def start_notebook(self, run_async=False):
    """ Create and connect to remote notebook server """
    # build cmd header
    _cmd_header = self._header_cd()  # change to remote_dir
    # . build cmd body
    # .. choose a port number
    server_port_num = random.randint(8824, 8850)
    # ... fill in jupyter server cmd
    _cmd_body = cmd.JUPYTER_SERVER.format(port_num=server_port_num)
    # join
    cmd_str = ' && '.join([ _cmd_header, _cmd_body ])

    # NOTE : figure out a way to kill the notebook as well
    self.async_remote_exec(cmd_str, logfile='/dev/null')
    logger.info('\tStarted notebook server in remote machine :{}'.format(
      server_port_num))

    # . choose a client port number
    # .. build notebook client command
    client_port_num = 8888
    cmd_local = cmd.JUPYTER_CLIENT.format(
        username=self.login.username,
        password=self.login.password,
        host=self.login.host,
        client_port_num=client_port_num,
        server_port_num=server_port_num
        )

    logger.info('\tStarting local notebook :{}'.format(client_port_num))

    if run_async:
      return local_async_exec(cmd_local)

    # connect to notebook server
    return local_exec(cmd_local)
