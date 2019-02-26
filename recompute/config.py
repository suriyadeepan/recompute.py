import configparser
import logging
import os

import paramiko
import pickle
from recompute import cmd

from recompute.espace import remote_exec

# configuration
CONFIG_FILE = os.path.join(os.environ['HOME'], '.recompute.conf')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_config_file():
  # TODO : this is a cluster-fuck; find a better way to do this
  config = configparser.ConfigParser()
  config.add_section('DEFAULT')
  config.set('DEFAULT', 'default', 'user1@host')
  config.set('DEFAULT', 'domain', 'domainame.com')
  config.set('DEFAULT', 'machines', 'machine1,machine2,machine3')
  config.set('DEFAULT', 'remotepasses', 'yyyy1,yyyy2,yyyy3')
  config.set('DEFAULT', 'users', 'user1,user2,user3')
  config.set('DEFAULT', 'test', 'uyw80x19')
  config.set('DEFAULT', 'localuser', 'user1')
  config.set('DEFAULT', 'localpass', 'xxxxxxx')
  config.set('DEFAULT', 'remotepass', 'yyyyyyy')
  config.set('DEFAULT', 'defaultuser', 'user1')
  config.set('DEFAULT', 'defaulthost', 'localhost')
  config.set('DEFAULT', 'remote_home', '~/projects/')

  # write to $HOME/.recompute.conf
  with open(CONFIG_FILE, 'w') as f_config:
    f_config.write(f_config)
  # config saved!
  logger.info('\tConfig written to \n\t[{}]'.format(CONFIG_FILE))
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

  def __init__(self, config_file=CONFIG_FILE):
    self.config = self.load_config(config_file)
    self.client = None

  def load_config(self, config_file):
    """ Load config dictionary from configuration file """
    config = configparser.ConfigParser()
    config.read(config_file)
    return config['DEFAULT']

  def is_host_up(self, host):
    """ Check if a host machine is online """
    return os.system("ping -c 1 " + host) is 0

  def make_host(self, machine):
    """ Append domain name to Machine """
    if not self.config['domain']:
      return machine
    return '{}.{}'.format(machine, self.config['domain'])

  def get_hosts(self):
    """" Return a list of hosts from configuration """
    assert self.config['machines']
    return [ self.make_host(machine)
        for machine in self.config['machines'].split(',')
        ]

  def get_active_hosts(self):
    """ Return a list of active hosts """
    assert self.config
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
    config = self.config

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
        free_gpu_memory = int(remote_exec(cmd.GPU_FREE_MEMORY, login))
        free_disk_space = int(remote_exec(cmd.DISK_FREE_MEMORY, login))
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
    except paramiko.AuthenticationException:
      pass  # connection failed!

  def get_active_logins(self):
    """ Get a list of active Login's """
    hosts = self.get_active_hosts()
    logins = []

    logging.info('Active Hosts : {}'.format(hosts))
    for host in hosts:
      for user in self.config['users'].split(','):
        logging.info(':: Checking {}@{}'.format(user, host))
        # build Login instance
        login = Login(user, self.config['remotepass'], host)
        # check if login is active
        if self.is_login_active(login):
          logging.info('[Y]')
          logins.append(login)

    return logins


if __name__ == '__main__':
  logger.info('\tfixer.__main__\n')
