"""remote.py

Remote class models the remote machine.
It manages the interaction between the remote and the local.
Interaction includes,

* File transfer
* Log management
* Remote Execution
* Environment setup
* Process Management

"""
from __future__ import print_function
import time
import pickle
import os

from recompute import cmd
from recompute import process
from recompute import utils

# setup logger
logger = utils.get_logger(__name__)
# void cache
VOID_CACHE = '.recompute/void'


class Remote(object):
  """Remote models the remote machine"""

  def __init__(self, instance=None, bundle=None, remote_home=None):
    """
    Parameters
    ----------
    instance : instance.Instance, optional
      The instance corresponding to remote device (default None)
    bundle : bundle.Bundle, optional
      Bundle object that encapsulates current working directory (default None)
    remote_home : str, optional
      Home directory of remote device (default None)
    """
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
    self.client = None

    # projects/ folder in remote machine
    remote_home = remote_home if remote_home else 'projects/'
    self.remote_home = os.path.join(self.get_remote_home_dir(), remote_home)
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

    # list spawned processes
    self.processes = [] if not cache else cache['processes']
    # cache void
    self.cache_()

  def get_remote_home_dir(self):
    """Get $HOME directory path from remote system"""
    pid, output = process.remote_execute('pwd', self.instance)
    return output.replace('\n', '').strip()

  def cache_(self, name=None):
    """Cache attributes of self (Remote).

    Parameters
    ----------
    name : str, optional
      filename of local cache (default None)
    """
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

  def make_mkcmd(self, dir_=None):
    """Make mkdir command

    Parameters
    ----------
    dir_ : str
      Directory to create

    Returns
    -------
    str
      Command to make directory `dir_` in remote machine
    """
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
    """Make rsync command

    Returns
    -------
    str
      rsync-based command that copies local files to remote
    """
    _header = cmd.SSH_HEADER.format(password=self.instance.password)
    _body = cmd.RSYNC.format(
            deps_file=self.bundle.db,
            username=self.instance.username,
            host=self.instance.host,
            remote_dir=self.remote_dir
            )

    return ' '.join([_header, _body])

  def make_dirs(self):
    """Make necessary directories in remote machine"""
    # execute make directory command from local machine
    mkcmd = self.make_mkcmd()
    logger.info(mkcmd)
    assert process.execute(mkcmd)
    # make data/ directory
    remote_data_ = self.make_mkcmd(self.remote_data)
    logger.info(remote_data_)
    assert process.execute(remote_data_)

  def rsync(self, update=False):
    """Rsync files between local and remote systems

    Parameters
    ----------
    update : bool, optional
      When set to `True` updates dependencies in local database (default False)

    Returns
    -------
    tuple
      (pid, output) Process id and output of execution
    """
    if update:  # update bundle
      self.bundle.update_dependencies()

    # execute rsync
    rsync_cmd = self.make_rsync_cmd()
    logger.info(rsync_cmd)
    return process.execute(rsync_cmd)

  def async_execute(self, commands, logfile=None, name='runner'):
    return self.execute(commands, run_async=True, log=True, logfile=logfile, name=name)

  def execute(self, commands, run_async=False, log=True, logfile=None, name='runner'):
    """Execute `cmdstr` in remote device given by `instance`

    Parameters
    ----------
    commands : list
      List of commands to be executed sequentially
    run_async : bool, optional
      When set to `True` runs commands asynchronously
      When set to `False` runs commands synchronously (default False)
    log : bool, optional
      Enables or disables logging output of execution (default True)
    logfile : str, optional
      Log file to redirect output of execution to (default None)
    name : str, optional
      Name of process (default 'runner')

    Returns
    -------
    tuple
      (pid, output) Process id and STDOUT of execution
    """
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
    exec_fn = process.remote_async_execute if run_async else process.remote_execute
    pid, output = exec_fn(cmd.EXEC_RUNNER.format(runner=runner_abs_path), instance=self.instance)

    # add pid to processes
    self.processes.append((name, pid))
    self.cache_()
    return pid, output

  def execute_command(self, cmdstr, run_async=False,
      log=False, logfile=None, bypass_subprocess=True):
    """Execute `cmdstr` in remote device

    Parameters
    ----------
    cmdstr : str
      Command to be executed
    run_async : bool, optional
      When set to `True` runs commands asynchronously
      When set to `False` runs commands synchronously (default False)
    log : bool, optional
      Enables or disables logging output of execution (default True)
    logfile : str, optional
      Log file to redirect output of execution to (default None)

    bypass_subprocess : bool, optional
      When set to `True`, `os.system` is used for execution, (None, None) is returned
      When set to `False`, subprocess module is used for execution (default True)

    Returns
    -------
    tuple
      (pid, output) Process id and STDOUT of execution
    """
    logger.info(cmdstr)
    # if we are running async
    if run_async:
      return process.remote_async_execute(cmdstr, self.instance, logfile)
    # --- sync execution --- #
    # execute in remote machine
    return process.remote_execute(cmdstr, self.instance,
        bypass_subprocess=bypass_subprocess)

  def async_execute_command(self, cmdstr, logfile=None):
    """Execute `cmdstr` in remote device, asynchronously

    Parameters
    ----------
    cmdstr : str
      Command to be executed
    logfile : str, optional
      Log file to redirect output to (default None)

    Returns
    -------
    tuple
      (pid, output) Process id and STDOUT of execution
    """
    return self.execute_command(cmdstr, run_async=True, log=True, logfile=logfile)

  def copy_file_to_remote(self, localpath, remotepath=None):
    """Copy file to remote machine

    Parameters
    ----------
    localpath : str
      Path to local file to be copied to remote machine
    remotepath : str, optional
      Path in remote machine where local file should be copied to
    """
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
    process.execute(copy_cmd)

  def get_file_from_remote(self, remotepath, localpath=None):
    """Copy file to local machine

    Parameters
    ----------
    remotepath : str
      Path to remote file to be copied to local machine
    remotepath : str, optional
      Path in local machine where remote file should be copied to
    """
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
    process.execute(copy_cmd)

  def get_remote_log(self, keyword=None):
    """Copy log file in remote system to local machine

    Parameters
    ----------
    keyword : str, optional
      A keyword to filter out log file (default None)

    Returns
    -------
    str
      Contents of log file in remote machine
    """
    # copy to local
    self.get_file_from_remote(self.logfile, self.bundle.path)  # '.'
    return self.get_local_log(keyword)

  def get_local_log(self, keyword=None):
    """Read local log file

    Parameters
    ----------
    keyword : str, optional
      A keyword to filter out log file (default None)

    Returns
    -------
    str
      Contents of log file in local machine
    """
    # check if local log file exists
    if not os.path.exists(self.local_logfile):
      return ''

    # read from log file
    log = open(os.path.join(self.bundle.path, self.logfile.split('/')[-1])).read()

    if keyword:    # if keyword is given
      log = '\n'.join([ line for line in log.split('\n') if keyword in line])

    logger.info('\n{}'.format(log))
    return log

  def loop_get_remote_log(self, delay, keyword=None):
    """ Fetch log file in a loop.

    Get log from remote machine every `delay` seconds.
    Print only the difference between local and remote log.
    End loop when "EOF" is seen in log file.

    Parameters
    ----------
    delay : int
      Number of seconds to wait till next fetch of log
    keyword : str, optional
      A keyword to filter out log file (default None)
    """
    try:
      while True:  # tis a loop, my liege.
        # . get local log
        local_log = self.get_local_log()
        # .. get remote log
        remote_log = self.get_remote_log()
        # ... compare
        diff = remote_log.replace(local_log, '')

        # print the diff
        if diff.strip():  # if there is a difference
          logger.info('\n{}'.format(diff))
          print(diff, end='')

        if 'EOF' in diff:  # has the execution ended?
          break
        # and now we wait
        time.sleep(delay)
    except KeyboardInterrupt:
      logger.info('You did this! You did this to us!!')

  def install_deps(self, update=False):
    """Install dependencies in remote system

    Parameters
    ----------
    update : bool, optional
      when set to `True`, dependencies are updated before "pip install"
      (default False)
    """
    if update:  # update bundle
      self.bundle.update_dependencies()
    # install
    self.install(self.bundle.get_requirements())

  def install(self, packages):
    """Install pypi `packages` in remote system

    Parameters
    ----------
    package : list
      List of pypi packages read from "requirements.txt"
    """
    if len(packages) == 0:  # check if packages list is empty
      logger.info('No pypi packages required for execution')
      return
    # make pip-install command
    pip_install_cmd = 'python3 -m pip install --user {}'.format(
        ' '.join(packages)
        )
    logger.info('\tInstall dependencies\n\t{}'.format(pip_install_cmd))
    # remote execute cmd
    logger.info('\n\t{}'.format(self.execute_command(pip_install_cmd)))

  def _header_cd(self, dir_=None):
    """Create "change directory" header

    Parameters
    ----------
    dir_ : directory to change to

    Returns
    -------
    str
      Command to change directory
    """
    # resolve directory to change to
    dir_ = dir_ if dir_ else self.remote_dir
    return 'cd {}'.format(dir_)

  def _header_cd_data(self):
    """Change Directory to data/ header

    Returns
    -------
    str
      Command to change to "data/" directory in remote machine
    """
    return 'cd {}'.format(self.remote_data)

  def download(self, urls, change_to=None, run_async=False):
    """Download from web to remote machine's "data/" directory

    Parameters
    ----------
    urls : list
      List of URLs to download from
    change_to : str, optional
      Directory where downloaded files go (default None)
    run_async : bool, optional
      Download asynchronously (default False)
    """
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

    # run (download) sync
    logger.info(self.execute_command(cmd_str + _cmd_footer))

  def get_session(self):
    """Create an ssh session"""
    os.system(
        cmd.SSH_INTO_REMOTE_DIR.format(
          username=self.instance.username,
          password=self.instance.password,
          host=self.instance.host,
          remote_dir=self.remote_dir
          )
        )

  def start_notebook(self, run_async=False, name='jupyter:{}'):
    """Create and connect to remote notebook server

    Parameters
    ----------
    run_async : bool, optional
      (currently unsupported) Enables asynchronous execution of local notebook (default False)
    name : str, optional
      Name of remote notebook server process (default jupyter:{})
    """
    # TODO : what if notebook isn't installed ? Most unlikely uninstalled!
    # install jupyter notebook
    # self.install(['jupyter'])
    # choose a port number
    server_port_num = utils.rand_server_port()
    # set name=name.format(server_port_num))
    notebook_server_name = name.format(server_port_num)
    # start jupyter server
    commands = [ cmd.JUPYTER_SERVER.format(port_num=server_port_num) ]
    notebook_server_pid, output = self.async_execute(commands,
        logfile='/dev/null',        # don't need no log
        name=notebook_server_name)  # name it, so we can track it

    logger.info('\tStarted notebook server in remote machine :{}'.format(
      server_port_num))
    print('{username}@{host}:{port}'.format(
      username=self.instance.username,
      host=self.instance.host,
      port=server_port_num))

    # . choose a client port number
    # .. build notebook client command
    client_port_num = utils.rand_client_port()
    cmd_local = cmd.JUPYTER_CLIENT.format(
        username=self.instance.username,
        password=self.instance.password,
        host=self.instance.host,
        client_port_num=client_port_num,
        server_port_num=server_port_num
        )

    logger.info('Starting local notebook ')
    logger.info('\thttp://localhost:{}/tree'.format(client_port_num))
    print('http://localhost:{port}/tree'.format(port=client_port_num))

    if run_async:
      print('Async Execution not implemented yet!')  # TODO : add issue handle here
      # pid, output = process.async_execute(cmd_local)
      # return

    # connect to notebook server
    pid, output = process.execute(cmd_local)

    if not pid and not output:  # keyboard interrupt
      logger.info('YOU quit jupyter notebook')
      # ----- kill server -----
      # . list processes
      procs = self.list_processes()
      # .. find jupyter notebook process
      name, pid = procs[-1]  # pretty sure it's the last added process
      # ... make sure name and pid check out
      assert pid == notebook_server_pid
      assert name == notebook_server_name
      # .... get handle
      notebook_server_idx = len(procs) - 1
      # ..... kill it
    self.kill(notebook_server_idx)  # if its 0, no problem!

  def list_processes(self, force=False):
    """
    Parameters
    ----------
    force : bool, optional
      When set to `True`, queries remote machine to get running processes
      When set to `False`, returns existing processes (default False)

    Returns
    -------
    list
      A list of processes active in remote machine [ (name, pid) ... ]

    """
    if force:
      # get list of processes
      command = ' '.join([
        cmd.SSH_HEADER.format(password=self.instance.password),
        cmd.SSH_EXEC.format(username=self.instance.username, host=self.instance.host,
          cmd=cmd.PROCESS_LIST_LINUX.format(username=self.instance.username)
          )
        ])
      pid, output = process.execute(command)
      pids = utils.parse_ps_results(output)
      known_pids = [ proc[-1] for proc in self.processes ]
      self.processes = [ (name, pid) for name, pid in self.processes
          if pid in pids ]
      self.processes.extend([ ('zombie/spawn', pid) for pid in pids
        if pid not in known_pids ])
      # update cache
      self.cache_()

    logger.info(self.processes)
    return self.processes

  def kill(self, idx, force=False):
    """Kill process by index

    Parameters
    ----------
    idx : int
      Index of process to kill
    force : bool, optional
      When set to `True`, queries remote machine to get running processes
      When set to `False`, considers existing processes (default False)
    """
    processes = self.list_processes(force=force)
    if len(processes) > 0:
      procs_to_kill = processes if idx == 0 else [processes[idx - 1]]
      if len(procs_to_kill) > 0:
        process.kill_remote_process(
            [ p[-1] for p in procs_to_kill ],  # separate pid
            instance=self.instance)
