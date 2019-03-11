import subprocess
import paramiko
import pickle
import random
import time
import os

import logging

from recompute import cmd

# setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def local_exec(cmdstr, timeout=10):
  process = subprocess.Popen(cmdstr.split(), stdout=subprocess.PIPE)
  logger.info(cmdstr)
  try:
    output, error = process.communicate()
    return output if output else True
  except:
    logger.error('\tExecution Failed!')


def local_async_exec(cmdstr, logfile='/dev/null', track=True):
  # add tracker
  tracker = rand_tracker(label='local') if track else ''
  cmdstr = '{cmd} {tracker}'.format(cmd=cmdstr, tracker=tracker)
  # cmd footer
  _cmd_footer = cmd.CMD_LOG_FOOTER_ASYNC.format(logfile)
  # update command
  cmdstr = ' '.join([cmdstr, ' ', _cmd_footer])
  # create process
  process = subprocess.Popen(cmdstr.split(), stdout=subprocess.PIPE, shell=True)
  try:
    output, error = process.communicate()
    logger.info('\t{pid} ({cmd})'.format(pid=tracker, cmd=cmdstr))
    return tracker
  except KeyboardInterrupt:
    logger.error('\tYou interrupted!')


def remote_exec(cmdstr, login):
  _header = cmd.SSH_HEADER.format(password=login.password)
  _body = cmd.SSH_EXEC.format(
      username=login.username,
      host=login.host, cmd=cmdstr
      )
  return local_exec(' '.join([_header, _body]))


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
    cache = None

    if not login and not bundle:
      # read from cache
      assert os.path.exists(self.CACHE)
      cache = pickle.load(open(self.CACHE, 'rb'))
      remote_home = cache['remote_home']

    self.login = login if login else cache['login']
    self.bundle = bundle if bundle else cache['bundle']

    # create an SSH Client
    self.client = None  # self.init_client()

    # ~/projects/ folder in remote machine
    self.remote_home = remote_home if remote_home else '~/projects/'
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
    self.processes = [] if not cache else cache['processes']

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

    # attach to self
    self.client = client

    return client

  def get_client(self):
    return self.client if self.client else self.init_client()

  def make_mkcmd(self, dir_=None):
    # resolve directory to make
    dir_ = dir_ if dir_ else self.remote_dir
    # create directory in remote machine
    _header = cmd.SSH_HEADER.format(password=self.login.password)
    _body = cmd.SSH_MAKE_DIR.format(
        username=self.login.username,
        host=self.login.host,
        remote_dir=dir_
        )
    # join
    return ' '.join([_header, _body])

  def make_rsync_cmd(self):
    _header = cmd.SSH_HEADER.format(password=self.login.password)
    _body = cmd.RSYNC.format(
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

  def remote_exec(self, cmdstr):
    """ Execute command in remote machine via `client` """
    # get client
    client = self.get_client()
    stdin, stdout, stderr = client.exec_command(cmdstr)
    output = [ line.strip('\n') for line in stdout ]

    if len(output) == 1:  # one-liners
      return output[-1]

    return output if len(output) > 0 else None

  def async_local_exec(self, cmdstr, logfile='/dev/null', track=False):
    """ Async local execution """
    # add tracker
    tracker = rand_tracker(label='local') if track else ''
    cmdstr = '{cmd} {tracker}'.format(cmd=cmdstr, tracker=tracker)
    # cmd footer
    _cmd_footer = cmd.CMD_LOG_FOOTER_ASYNC.format(logfile=logfile)
    # update command
    cmdstr = ' '.join([cmdstr, ' ', _cmd_footer])
    # create process
    process = subprocess.Popen(cmdstr.split(), stdout=subprocess.PIPE, shell=True)
    try:
      output, error = process.communicate()
    except KeyboardInterrupt:
      logger.error('\tYou interrupted!')

    # keep track of it
    self.processes.append((tracker, cmdstr))
    logger.info('\t{pid} ({cmd})'.format(pid=tracker, cmd=cmdstr))
    # update cache
    self.cache_()

    return tracker

  def async_remote_exec(self, cmdstr, logfile=None, track=True):
    """ Async execute command in remote machine """

    # resolve which logfile to write to
    logfile = logfile if logfile else self.logfile

    # place a tracker
    tracker = rand_tracker() if track else ''
    cmd_tracked = '{cmd} {tracker}'.format(cmd=cmdstr, tracker=tracker)

    # open a channel
    client = self.get_client()
    channel = client.get_transport().open_session()
    # add sync footer
    async_footer = cmd.CMD_LOG_FOOTER_ASYNC.format(logfile=logfile)
    # execute command async
    channel.exec_command(cmd_tracked + ' ' + async_footer)

    # keep track of it
    self.processes.append((tracker, cmdstr))
    logger.info('\t{pid} ({cmd})'.format(pid=tracker, cmd=cmdstr))

    # update cache
    self.cache_()

    return tracker

  def copy_file_to_remote(self, localpath, remotepath=None):
    """ Copy file to remote machine """
    # default remote path
    remotepath = remotepath if remotepath else self.remote_data
    # build copy cmd
    _header = cmd.SSH_HEADER.format(password=self.login.password)
    _body = cmd.SCP.format(
        username=self.login.username,
        host=self.login.host,
        remotepath=remotepath,
        localpath=localpath
        )
    copy_cmd = ' '.join([_header, _body])
    # local execute scp
    local_exec(copy_cmd)

  def get_file_from_remote(self, remotepath, localpath=None):
    """ Copy file to local machine """
    # default local path
    localpath = localpath if localpath else self.bundle.path
    # build copy cmd
    _header = cmd.SSH_HEADER.format(password=self.login.password)
    _body = cmd.SCP_FROM_REMOTE.format(
        username=self.login.username,
        host=self.login.host,
        remotepath=remotepath,
        localpath=localpath
        )
    copy_cmd = ' '.join([_header, _body])
    # execute scp command
    local_exec(copy_cmd)

    # get last modified date
    _, stdout, _ = self.get_client().exec_command(
        cmd.LAST_MODIFIED.format(filename=remotepath)
        )
    # read from stdout
    last_modified = str('\n'.join(stdout.readlines())).replace('\n', '')
    logger.info('\n\tLast Modification time : {}\n'.format(last_modified))
    return last_modified

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
    last_modified = self.get_file_from_remote(logfile, self.bundle.path)  # '.'
    logger.info('\n\n{}'.format(
      open(os.path.join(self.bundle.path, logfile.split('/')[-1])).read()
      ))
    # return last modified date
    return last_modified

  def log_async_remote_exec(self, cmd, logfile=None):
    """ Log execution output and copy log to local machine """

    # resolve which logfile to write to
    logfile = logfile if logfile else self.logfile

    # add command sequence header to `cmd`
    _cmd_seq_header = 'cd {}'.format(self.remote_dir)
    cmd = ' && '.join([ _cmd_seq_header, cmd ])

    # execute command
    tracker = self.async_remote_exec(cmd, logfile)

  def get_remote_log(self, keyword=None, print_log=True):
    """ Copy log file in remote system to local machine """
    # copy to local
    last_modified = self.get_file_from_remote(self.logfile, self.bundle.path)  # '.'
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
    logger.info(self.remote_exec(cmd_str + _cmd_footer))

    # get log file from remote to local machine
    last_modified = self.get_file_from_remote(data_logfile, self.bundle.path)

  def get_session(self):
    """ Create a session session """
    os.system(
        cmd.SSH_INTO_REMOTE_DIR.format(
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
    server_port_num = rand_server_port()
    # ... fill in jupyter server cmd
    _cmd_body = cmd.JUPYTER_SERVER.format(port_num=server_port_num)
    # join
    cmd_str = ' && '.join([ _cmd_header, _cmd_body ])

    # NOTE : figure out a way to kill the notebook as well
    tracker = self.async_remote_exec(cmd_str, logfile='/dev/null')
    logger.info('\tStarted notebook server in remote machine :{}'.format(
      server_port_num))

    # . choose a client port number
    # .. build notebook client command
    client_port_num = rand_client_port()
    cmd_local = cmd.JUPYTER_CLIENT.format(
        username=self.login.username,
        password=self.login.password,
        host=self.login.host,
        client_port_num=client_port_num,
        server_port_num=server_port_num
        )

    logger.info('\tStarting local notebook :{}'.format(client_port_num))

    if run_async:
      return self.async_local_exec(cmd_local, track=True)  # keep track of it

    # connect to notebook server
    return local_exec(cmd_local)  # not

  def list_processes(self, print_log=False):
    # get client
    client = self.get_client()
    _, stdout, _ = client.exec_command(cmd.PROCESS_LIST_LINUX)
    remote_proc_log = str('\n'.join(stdout.readlines()))
    # local_proc_log = str('\n'.join(local_exec(cmd.PROCESS_LIST_OSX)))
    # logger.info(local_exec(cmd.PROCESS_LIST_OSX))
    local_proc_log = ''

    active_processes = []
    # [all] option
    logger.info('[0] * all')
    i = 1
    for (tracker, cmd_) in self.processes:
      # search for tracker in process log
      if str(tracker) in remote_proc_log or \
          str(tracker) in local_proc_log:  # or in the local process log
        active_processes.append((tracker, cmd_))
        logger.info('[{idx}] {tracker} ({cmd})'.format(
          idx=i, tracker=tracker, cmd=cmd_
          ))
        i = i + 1

    # keep track of acive_processes
    self.processes = active_processes

    return self.processes

  def kill(self, idx, force=True):
    # get client
    client = self.get_client()
    # get list of active proceses
    processes = self.list_processes() if force else self.processes
    # if idx == 0 -> kill them all!
    dead_procs = [ processes[idx - 1] ] if idx > 0 else processes

    # iterate through processes to be killed
    for tracker, cmd_ in dead_procs:
      # get process id using tracker
      proc_list_cmd = cmd.PROCESS_LIST_LINUX if 'remote' in tracker \
          else cmd.PROCESS_LIST_OSX
      _, stdout, _ = client.exec_command(proc_list_cmd)
      # parse output of `ps` command
      proc_log = [ line.replace('\n', '') for line in stdout.readlines()
          if 'grep' not in line ]
      pids = [ int(line.split(' ')[1]) for line in proc_log ]
      # kill remote process
      pid = max(pids)  # choose pid
      # if remote tracker
      if 'remote' in tracker:
        client.exec_command(cmd.KILL_PROCESS.format(pid))
      else:
        local_exec(cmd.KILL_PROCESS.format(pid))
