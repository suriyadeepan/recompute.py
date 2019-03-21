import configparser
import logging
import os

import paramiko
import pickle
from recompute import cmd

from recompute.process import remote_execute

# configuration
CONFIG_FILE = os.path.join(os.environ['HOME'], '.recompute.conf')
LOCAL_CONFIG_DIR = '.recompute'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_config_file(force=False):
  # if config file exists
  if os.path.exists(CONFIG_FILE) and not force:
    return

  # create config
  config = configparser.ConfigParser()
  config.add_section('general')  # add general section
  config.set('general', 'instance', 0)  # default instance
  config.set('general', 'remote_home', '~/projects/')  # remote home folder

  # write to $HOME/.recompute.conf
  config.write(open(CONFIG_FILE, 'w'))
  logger.info('config written to [{}]'.format(CONFIG_FILE))
  logger.info(dict(config['general']))
  return config


class Login():

  def __init__(self, username=None, password=None, host=None):
    self.username = username
    self.password = password
    self.host = host

  def resolve(self, login_str):
    try:
      self.username, self.host = login_str.strip().split('@')
      return self
    except ValueError:
      logging.error('Check Login [{}]'.format(login_str))
      exit()


class Processor():

  def __init__(self):
    self.config = self.load_config()
    self.config_default = self.config['general']
    self.client = None

  def load_config(self):
    """ Load config dictionary from configuration file """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

  def add_instance(self, login):
    # make sure the login is active
    assert self.is_login_active(login)
    logger.debug('login successful')
    # infer instance index
    idx = len([ sec for sec in dict(self.config).keys()
      if 'instance ' in sec ])
    # add instance to config file
    self.config['instance {}'.format(idx)] = {
        'user' : login.username,
        'host' : login.host,
        'password' : login.password
        }
    # overwrite config file
    self.config.write(open(CONFIG_FILE, 'w'))
    logger.debug('config file updated')

  def get_instance(self, idx=None):
    if idx is None:  # if idx is not given
      # get default instance from config
      idx = int(self.config['general']['instance'])
    # get instance config from config file
    instance = self.config['instance {}'.format(idx)]
    # make sure the instance exists in config
    assert instance
    # return a Login instance
    return Login(instance['user'], instance['password'], instance['host'])

  def is_host_up(self, host):
    """ Check if a host machine is online """
    return os.system("ping -c 1 " + host) is 0

  def make_host(self, machine):
    """ Append domain name to Machine """
    if not self.config_default['domain']:
      return machine
    return '{}.{}'.format(machine, self.config_default['domain'])

  def get_hosts(self):
    """" Return a list of hosts from configuration """
    assert self.config_default['machines']
    return [ self.make_host(machine)
        for machine in self.config_default['machines'].split(',')
        ]

  def get_active_hosts(self):
    """ Return a list of active hosts """
    assert self.config_default
    return [ host for host in self.get_hosts()
        if self.is_host_up(host) ]

  def init_client(self):
    # setup ssh client
    self.client = paramiko.SSHClient()
    # load local policies
    self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

  def probe(self, force=False):
    from prettytable import PrettyTable

    # get config
    config = self.config_default

    def dict_to_table(hosts):
      # build a frickin table
      table = PrettyTable()
      table.field_names = [ "Machine", "Status", "GPU (MB)", "Disk (MB)" ]
      for host, values in hosts.items():
        table.add_row(values)

      return table

    CACHE = '.recompute/table'
    if not force and os.path.exists(CACHE):
      return dict_to_table(pickle.load(open(CACHE, 'rb')))

    # create default login
    login = Login(config['defaultuser'], config['remotepass'])

    # list of active hosts
    hosts = { h : [ h, 'active', '-', '-' ]
        for h in self.get_active_hosts() }

    # iterate through active machines
    for host in hosts.keys():
      try:
        # set host
        login.host = host
        # gather info from remote machines
        free_gpu_memory = int(remote_execute(cmd.GPU_FREE_MEMORY, login))
        free_disk_space = int(remote_execute(cmd.DISK_FREE_MEMORY, login))
        # update dictionary
        hosts[host][2] = free_gpu_memory
        hosts[host][3] = free_disk_space
      except:
        # something wrong? -> blame the host..
        hosts[host][1] = 'inactive'
        continue

    # cache table
    pickle.dump(hosts, open(CACHE, 'wb'))

    return dict_to_table(hosts)

  def is_login_active(self, login):
    """ Is a login working? """

    # create SSHClient instance
    if not self.client:
      self.init_client()

    try:  # connect to remote
      self.client.connect(login.host,
          username=login.username,
          password=login.password)
      self.client.close()  # connection success!
      return True
    except:
      return  # connection failed!

  def get_active_logins(self):
    """ Get a list of active Login's """
    hosts = self.get_active_hosts()
    logins = []

    logging.info('Active Hosts : {}'.format(hosts))
    for host in hosts:
      for user in self.config_default['users'].split(','):
        logging.info(':: Checking {}@{}'.format(user, host))
        # build Login instance
        login = Login(user, self.config_default['remotepass'], host)
        # check if login is active
        if self.is_login_active(login):
          logging.info('[Y]')
          logins.append(login)

    return logins


if __name__ == '__main__':
  logger.info('\tfixer.__main__\n')
