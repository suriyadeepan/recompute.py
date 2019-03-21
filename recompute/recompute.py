from recompute.config import Processor, Login
from recompute.config import generate_config_file
from recompute.remote import Remote
from recompute.bundle import Bundle
from recompute.remote import VOID_CACHE

from getpass import getpass

import argparse
import logging
import os

# setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# parse command-line arguments
parser = argparse.ArgumentParser(
    description='recompute.py -- A sweet tool for remote computation'
    )
# NOTE : ffs! write a descriptive help for `mode`
parser.add_argument('mode', type=str,
    help='(init/sync/async/rsync/install/log/list/ssh/notebook/conf/probe/data/pull/push,sshadd) recompute mode')
parser.add_argument('cmd', nargs='?', default='None',
    help='command to run in remote system')
parser.add_argument('--remote_home', nargs='?', default='/home/oni/projects/',
    help='remote projects/ directory')
parser.add_argument('--urls', nargs='?', default='',
    help='comma-separated list of URLs')
parser.add_argument('--login', nargs='?', default='',
    help='[username@host] config.remotepass is used')
parser.add_argument('--filter', nargs='?', default='',
    help='keyword to filter log')
parser.add_argument('--loop', nargs='?', default='',
    help='number of seconds to wait to fetch log')
parser.add_argument('--idx', nargs='?', default='',
    help='process idx to operate on')
parser.add_argument('--name', nargs='?', default='runner',
    help='name of process')
parser.add_argument('--instance', nargs='?', default=0,
    help='remote instance to use')
parser.add_argument('--force', default=False, action='store_true',
    help='clear cache')
parser.add_argument('--no-force', dest='force', action='store_false')
parser.add_argument('--run_async', default=False, action='store_true',
    help='Execute commands async')
parser.add_argument('--no-run_async', dest='run_async', action='store_false')
parser.add_argument('--rsync', default=True, action='store_true',
    help='Update files in remote machine')
parser.add_argument('--no-rsync', dest='rsync', action='store_false')
args = parser.parse_args()


def init():
  # get processor instance
  proc = Processor()
  # create default login
  instance = int(args.instance) if args.instance else None
  login = proc.get_instance(instance)
  # create bundle
  bundle = Bundle()
  # create remote instance handle
  void = Remote(login, bundle, remote_home=args.remote_home)
  # sync files
  void.rsync()  # TODO : make sync optional -u
  # install from requirements.txt
  void.install_deps()  # TODO : make this optional -i

  return void


def cache_exists():
  return os.path.exists(VOID_CACHE)


def create_void():
  if cache_exists():
    logger.info('cache exists')
    return Remote()

  logger.info('cache doesn\'t exist')
  return init()


def main():  # package entry point

  """ Boilerplate """
  # create a Processor instance
  proc = Processor()
  # load config from file
  config = proc.config

  # ------------ conf ------------ #
  if args.mode == 'conf':  # generate config file
    """ Mode : Generate configuration file """
    config = generate_config_file()
    if not config:
      logger.info('config exists; use --force to overwrite it')

  # ------------ sshadd ---------- #
  elif args.mode == 'sshadd':  # add remote instance
    """ Mode : Add remote instance to config """
    try:
      assert args.login  # make sure user@host is given as input
      # get password from user
      password = getpass('Password:')
      # . create Login instance
      # .. parse user@host
      login = Login(password=password).resolve(args.login)
      # add login to config
      proc.add_instance(login)
    except AssertionError:
      logger.error('Invalid/Empty login')

  # ------------ probe ----------- #
  elif args.mode == 'probe':  # probe remote machines
    """ Mode : Probe remote machines """
    print(proc.probe(force=args.force))

  # ------------ data ------------ #
  elif args.mode == 'data':
    """ Mode : GET data from web """
    try:
      assert args.urls
      create_void().download(args.urls.split(' '), run_async=args.run_async)
    except AssertionError:
      logger.error('Input a list of URLs to download')

  # ------------ init ------------ #
  elif args.mode == 'init':
    """ Mode : Initialize project in current directory """
    init()  # create void anew

  # ------------ sync ------------ #
  elif args.mode == 'sync':
    """ Mode : Sync Execute command in remote machine """
    assert args.cmd  # user inputs command to exec in remote
    # create void from cache
    void = create_void()
    # look for python execution
    if 'python' in args.cmd and args.rsync:  # TODO : this is pretty hacky;
      void.rsync(update=args.force)          # you are better than this!
    # blocking execute `cmd` in remote
    void.execute([args.cmd], log=True, name=args.name)

  # ------------ async ----------- #
  elif args.mode == 'async':
    """ Mode : Async Execute command in remote machine """
    assert args.cmd
    # get void
    void = create_void()
    # look for python execution
    if 'python' in args.cmd and args.rsync:
      void.rsync(update=args.force)
    # async execute `cmd` in remote
    void.async_execute([args.cmd], name=args.name)

  # ------------ rsync ----------- #
  elif args.mode == 'rsync':
    """ Mode : Rsync files """
    # create void from cache
    create_void().rsync(update=args.force)

  # ------------ install --------- #
  elif args.mode == 'install':
    """ Mode : Rsync files """
    # create void from cache
    create_void().install_deps(update=args.force)

  # ------------ log ------------- #
  elif args.mode == 'log':  # copy log from remote
    """ Mode : Copy log from remote machine """
    # get void
    void = create_void()
    # delete local log
    # NOTE : i'm not sure if i should do this!
    if os.path.exists(void.local_logfile):  # if it exists
      os.remove(void.local_logfile)
    if args.loop:  # --------- loop ----------- #
      """ Mode : Copy log from remote machine in a loop """
      void.loop_get_remote_log(int(args.loop), args.filter)
    else:  # --------------- no loop ---------- #
      void.get_remote_log(args.filter, print_log=True)

  # ------------ list ------------ #
  elif args.mode == 'list':  # list of proceses
    """ Mode : List remote processes """
    create_void().list_processes(print_log=True, force=True)

  # ------------ kill ------------ #
  elif args.mode == 'kill':  # kill process
    """ Mode : Interactive kill """
    void = create_void()
    procs = void.list_processes(print_log=True, force=True)
    idx = int(args.idx) if args.idx else None
    if not args.idx:
      idx = int(input('kill idx [0-{}] : '.format(len(procs))))
    void.kill(idx)

  # ------------ ssh ------------- #
  elif args.mode == 'ssh':  # start an ssh session
    """ Mode : Create an ssh session """
    create_void().get_session()

  # ------------ notebook -------- #
  elif args.mode == 'notebook':  # start an ssh session
    """ Mode : Create and connect to remote notebook server """
    create_void().start_notebook(args.run_async)

  # ------------ pull ------------ #
  elif args.mode == 'pull':  # copy log from remote
    """ Mode : Download file from remote machine """
    assert args.cmd  # make sure files are provided for download
    # NOTE : relative path is used
    # NOTE : copy one file/directory at a time
    void = create_void()

    # parse list of files/path
    filepaths = args.cmd.split(' ')

    try:  # make sure only one file is copied at a time
      assert len(filepaths) <= 2
    except AssertionError:
      logger.error('Copy one file/directory at a time')
      exit()

    # get absolute paths of local file and remote path
    remotefile = os.path.join(void.remote_dir, filepaths[0])
    localpath = None if len(filepaths) == 1 \
        else os.path.join(void.bundle.path, filepaths[1])

    void.get_file_from_remote(remotefile, localpath)

  # ------------ push ------------ #
  elif args.mode == 'push':  # copy log from remote
    """ Mode : Upload file to remote machine """
    assert args.cmd  # make sure files are provided for download
    # NOTE : relative path is used
    # NOTE : copy one file/directory at a time
    void = create_void()
    # parse list of files/path
    filepaths = args.cmd.split(' ')

    try:  # make sure only one file is copied at a time
      assert len(filepaths) <= 2
    except AssertionError:
      logger.error('Copy one file/directory at a time')
      exit()

    # get absolute paths of local file and remote path
    localfile = os.path.join(void.bundle.path, filepaths[0])
    remotepath = None if len(filepaths) == 1 \
        else os.path.join(void.remote_dir, filepaths[1])

    # copy file to remote
    void.copy_file_to_remote(localfile, remotepath)

  else:
    logger.error('Something went wrong! Check command-line arguments')
