"""recompute.py

A sweet tool for Remote Execution.
This is the high-level user interface.
The user is exposed to the program through this module.
We bombard the user with a suite of features that enable comfortable execution of code in remote machines.
Each feature, named `mode` here, corresponds to a particular operation.
Scroll down for a table of available commands, options and how to use them.

"""
from recompute import utils
from recompute.instance import Instance
from recompute.config import ConfigManager
from recompute.instance import InstanceManager
from recompute.remote import Remote
from recompute.bundle import Bundle
from recompute.remote import VOID_CACHE

from getpass import getpass

import argparse
import logging
import os

# setup logger
logger = logging.getLogger(__name__)

# man page
MAN_DOCU = """
                         _ __   ___ 
                        | '__| / _ \\
                        | |   |  __/
                        |_|    \___|

+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| Mode     | Description                                         | Options               | Example                             |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| init     | Setup current directory for remote execution        | --instance-idx        | $re init                            |
|          |                                                     |                       | $re init --instance-idx=1           |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| rsync    | Use rsync to synchronize local files with remote    | --force               | $re rsync                           |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| sshadd   | Add a new instance to config                        | --instance            | $re sshadd --instance="usr@host"    |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| install  | Install pypi packages in requirements.txt in remote | cmd, --force          | $re install                         |
|          |                                                     |                       | $re install "pytorch tqdm"          |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| sync     | Synchronous execution of "args.cmd" in remote       | cmd, --force, --rsync | $re sync "python3 x.py"             |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| async    | Asynchronous execution of "args.cmd" in remote      | cmd, --force, --rsync | $re async "python3 x.py"            |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| log      | Fetch log from remote machine                       | --loop, --filter      | $re log                             |
|          |                                                     |                       | $re log --loop=2                    |
|          |                                                     |                       | $re log --filter="pattern"          |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| list     | List out processes alive in remote machine          | --force               | $re list                            |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| kill     | Kill a process by index                             | --idx                 | $re kill                            |
|          |                                                     |                       | $re kill --idx=1                    |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| purge    | Kill all remote process that are alive              | None                  | $re purge                           |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| ssh      | Create an ssh session in remote machine             | None                  | $re ssh                             |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| notebook | Create jupyter notebook in remote machine           | --run-async           | $re notebook                        |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| push     | Upload file to remote machine                       | cmd                   | $re push "x.py y/"                  |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| pull     | Download file from remote machine                   | cmd                   | $re pull "y/z.py ."                 |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| data     | Download data from web into data/ folder of remote  | cmd                   | $re data "url1 url2 url3"           |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
| man      | Show this man page                                  | None                  | $re man                             |
+----------+-----------------------------------------------------+-----------------------+-------------------------------------+
"""

# parse command-line arguments
parser = argparse.ArgumentParser(
    description='recompute.py -- A sweet tool for remote computation'
    )
# NOTE : ffs! write a descriptive help for `mode`
parser.add_argument('mode', type=str,
    help='(init/sync/async/rsync/install/log/list/kill/purgessh/notebook/conf/probe/data/pull/push/sshadd/man) recompute mode')
parser.add_argument('cmd', nargs='?', default='None',
    help='command to run in remote system')
parser.add_argument('--remote-home', nargs='?', default='projects/',
    help='remote projects/ directory')
parser.add_argument('--urls', nargs='?', default='',
    help='comma-separated list of URLs')
parser.add_argument('--instance', nargs='?', default='',
    help='[username@host] config.remotepass is used')
parser.add_argument('--filter', nargs='?', default='',
    help='keyword to filter log')
parser.add_argument('--loop', nargs='?', default='',
    help='number of seconds to wait to fetch log')
parser.add_argument('--idx', nargs='?', default='',
    help='process idx to operate on')
parser.add_argument('--name', nargs='?', default='runner',
    help='name of process')
parser.add_argument('--instance-idx', nargs='?', default=0,
    help='remote instance to use')
parser.add_argument('--force', default=False, action='store_true',
    help='clear cache')
parser.add_argument('--no-force', dest='force', action='store_false')
parser.add_argument('--run-async', default=False, action='store_true',
    help='Execute commands async')
parser.add_argument('--no-run-async', dest='run_async', action='store_false')
parser.add_argument('--rsync', default=True, action='store_true',
    help='Update files in remote machine')
parser.add_argument('--no-rsync', dest='rsync', action='store_false')
args = parser.parse_args()


def init():
  """Setup current directory for remote execution

  * Setup remote instance for execution
  * Create local configuration files
  * Bundle up local repository
  * Sync files
  * Install Dependencies

  Returns
  -------
  remote.Remote
    An instance of Remote class
  """
  # get configuration manager
  confman = ConfigManager()
  # build instance manager
  instanceman = InstanceManager(confman)
  # create default instance
  instance_idx = int(args.instance_idx) if args.instance_idx else None
  instance = instanceman.get(instance_idx)
  # create bundle
  bundle = Bundle()
  # create remote instance handle
  remote = Remote(instance, bundle, remote_home=args.remote_home)
  # sync files
  remote.rsync()
  # install from requirements.txt
  remote.install_deps()
  return remote


def cache_exists():
  """Does cache exist?"""
  return os.path.exists(VOID_CACHE)


def get_remote():
  """Get an instance of Remote from cache or create anew"""
  if cache_exists():
    logger.info('Cache exists')
    return Remote()

  logger.info('Cache doesn\'t exist')
  return init()


def main():  # package entry point

  """ Boilerplate """
  # get configuration manager
  confman = ConfigManager()
  # build instance manager
  instanceman = InstanceManager(confman)

  # ------------ man ------------- #
  if args.mode == 'man':
    """ Mode : Show man page """
    print(MAN_DOCU)
    exit()

  # ------------ conf ------------ #
  elif args.mode == 'conf':  # generate config file
    """ Mode : Generate configuration file """
    config = confman.generate(force=args.force)
    if not config:
      logger.info('config exists; use --force to overwrite it')
      print('config exists; use --force to overwrite it')

  # ------------ sshadd ---------- #
  elif args.mode == 'sshadd':  # add remote instance
    """ Mode : Add remote instance to config """
    try:
      assert args.instance  # make sure user@host is given as input
      # get password from user
      password = getpass('Password:')
      # . create Instance instance
      # .. parse user@host
      instance = Instance(password=password).resolve_str(args.instance)
      # add instance to config
      instanceman.add_instance(instance)
    except AssertionError:
      logger.error('Invalid/Empty instance')

  # ------------ probe ----------- #
  elif args.mode == 'probe':  # probe remote machines
    """ Mode : Probe remote machines """
    print(instanceman.probe(force=args.force))

  # ------------ data ------------ #
  elif args.mode == 'data':
    """ Mode : GET data from web """
    try:
      assert args.urls
      get_remote().download(args.urls.split(' '), run_async=args.run_async)
    except AssertionError:
      logger.error('Input a list of URLs to download')

  # ------------ init ------------ #
  elif args.mode == 'init':
    """ Mode : Initialize project in current directory """
    init()  # create remote anew

  # ------------ sync ------------ #
  elif args.mode == 'sync':
    """ Mode : Sync Execute command in remote machine """
    assert args.cmd  # user inputs command to exec in remote
    # create remote from cache
    remote = get_remote()
    # look for python execution
    if 'python' in args.cmd and args.rsync:  # TODO : this is pretty hacky;
      remote.rsync(update=args.force)          # you are better than this!
    # blocking execute `cmd` in remote
    remote.execute([args.cmd], log=True, name=args.name)

  # ------------ async ----------- #
  elif args.mode == 'async':
    """ Mode : Async Execute command in remote machine """
    assert args.cmd
    # get remote
    remote = get_remote()
    # look for python execution
    if 'python' in args.cmd and args.rsync:
      remote.rsync(update=args.force)
    # async execute `cmd` in remote
    remote.async_execute([args.cmd], name=args.name)

  # ------------ rsync ----------- #
  elif args.mode == 'rsync':
    """ Mode : Rsync files """
    # create remote from cache
    get_remote().rsync(update=args.force)

  # ------------ install --------- #
  elif args.mode == 'install':
    """ Mode : Rsync files """
    if not args.cmd:
      # create remote from cache
      get_remote().install_deps(update=args.force)
    else:
      # space separated pypi packages
      get_remote().install(args.cmd.split(' '))

  # ------------ log ------------- #
  elif args.mode == 'log':  # copy log from remote
    """ Mode : Copy log from remote machine """
    # get remote
    remote = get_remote()
    # delete local log
    # NOTE : i'm not sure if i should do this!
    if os.path.exists(remote.local_logfile):  # if it exists
      os.remove(remote.local_logfile)
    if args.loop:  # --------- loop ----------- #
      """ Mode : Copy log from remote machine in a loop """
      remote.loop_get_remote_log(int(args.loop), args.filter)
    else:  # --------------- no loop ---------- #
      log = remote.get_remote_log(args.filter)
      print(utils.parse_log(log))

  # ------------ list ------------ #
  elif args.mode == 'list':  # list of processes
    """ Mode : List remote processes """
    print(utils.tabulate_processes(
        get_remote().list_processes(force=True)
        ))

  # ------------ kill ------------ #
  elif args.mode == 'kill':  # kill process
    """ Mode : Interactive kill """
    remote = get_remote()
    # print table of processes
    print(utils.tabulate_processes(
      remote.list_processes(force=True)
      ))
    # resolve index of proc
    idx = int(args.idx) if args.idx else None
    if not args.idx:
      # get index from user
      try:
        idx = int(input('Process to kill (index) : '))
      except KeyboardInterrupt:
        exit()  # the user chikened out!
    # kill process
    remote.kill(idx)

  # ------------ purge ----------- #
  elif args.mode == 'purge':  # kill them all
    get_remote().kill(0)

  # ------------ ssh ------------- #
  elif args.mode == 'ssh':  # start an ssh session
    """ Mode : Create an ssh session """
    get_remote().get_session()

  # ------------ notebook -------- #
  elif args.mode == 'notebook':  # start an ssh session
    """ Mode : Create and connect to remote notebook server """
    get_remote().start_notebook(args.run_async)

  # ------------ pull ------------ #
  elif args.mode == 'pull':  # copy log from remote
    """ Mode : Download file from remote machine """
    assert args.cmd  # make sure files are provided for download
    # NOTE : relative path is used
    # NOTE : copy one file/directory at a time
    remote = get_remote()

    # parse list of files/path
    filepaths = args.cmd.split(' ')

    try:  # make sure only one file is copied at a time
      assert len(filepaths) <= 2
    except AssertionError:
      logger.error('Copy one file/directory at a time')
      exit()

    # get absolute paths of local file and remote path
    remotefile = os.path.join(remote.remote_dir, filepaths[0])
    localpath = None if len(filepaths) == 1 \
        else os.path.join(remote.bundle.path, filepaths[1])

    remote.get_file_from_remote(remotefile, localpath)

  # ------------ push ------------ #
  elif args.mode == 'push':  # copy log from remote
    """ Mode : Upload file to remote machine """
    assert args.cmd  # make sure files are provided for download
    # NOTE : relative path is used
    # NOTE : copy one file/directory at a time
    remote = get_remote()
    # parse list of files/path
    filepaths = args.cmd.split(' ')

    try:  # make sure only one file is copied at a time
      assert len(filepaths) <= 2
    except AssertionError:
      logger.error('Copy one file/directory at a time')
      exit()

    # get absolute paths of local file and remote path
    localfile = os.path.join(remote.bundle.path, filepaths[0])
    remotepath = None if len(filepaths) == 1 \
        else os.path.join(remote.remote_dir, filepaths[1])

    # copy file to remote
    remote.copy_file_to_remote(localfile, remotepath)

  else:
    logger.error('Something went wrong! Check command-line arguments')
