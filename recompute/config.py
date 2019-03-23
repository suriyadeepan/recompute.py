import configparser
import logging
import os

import pickle
from recompute import cmd

from recompute.process import remote_execute

# configuration
CONFIG_FILE = os.path.join(os.environ['HOME'], '.recompute.conf')
LOCAL_CONFIG_DIR = '.recompute'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigManager(object):

  def __init__(self, configfile=None):
    # resolve config file
    self.configfile = configfile if configfile else CONFIG_FILE
    # read config from config file
    self.config = self.load() if self.config_exists else None

  def load(self, configfile=None):
    """ Load config dictionary from configuration file """
    # resolve config file
    configfile = configfile if configfile else self.configfile
    # create parser instance
    config = configparser.ConfigParser()
    # read from file
    config.read(self.configfile)
    return config

  def config_exists(self):
    return os.path.exists(self.configfile)

  def generate(self, force=False, configfile=None):
    # if config file exits
    if self.config_exists() and not force and not configfile:
      logger.info('Config File exists; add --force to overwrite')
      return
    # create config
    config = configparser.ConfigParser()
    config.add_section('general')         # add general section
    config.set('general', 'instance', '0')  # default instance
    config.set('general', 'remote_home', '~/projects/')  # remote home folder

    # resolve config file
    configfile = configfile if configfile else self.configfile
    # write to config file
    config.write(open(configfile, 'w'))
    logger.info('config written to [{}]'.format(self.configfile))
    logger.info(dict(config['general']))
    # attach to self
    self.config = config
    return config

  def update(self, config):
    self.config = config
    # write to config file
    self.config.write(open(self.configfile, 'w'))
    logger.debug('config file updated')

  def get_instances(self):
    return [ self.config[section]
        for section in self.config.sections()
        if 'instance ' in section ]

  def get_instance(self, idx=None):
    if idx is None:
      idx = int(self.config['general']['instance'])
    return self.config['instance {}'.format(idx)]

  def get_default_instance(self):
    idx = int(self.config['general']['instance'])
    return self.get_instance(idx)

  def add_instance(self, instance):
    # get next index
    idx = len([ sec for sec in self.config.sections()
      if 'instance ' in sec ])
    # add new instance section to config file
    self.config['instance {}'.format(idx)] = {
        'user' : instance.username,
        'host' : instance.host,
        'password' : instance.password
        }
    # update config file
    self.update(self.config)
