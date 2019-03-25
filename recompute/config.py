"""config.py

The Configuration Manager is an interface to interact with the global configuration file.
It can generate, load and update the configuration file.
It interacts directly on the configuration file,
and acts as a mediator between Instance Manager and the global configuration file.

"""
import configparser
import os

from recompute import utils

# configuration
CONFIG_FILE = os.path.join(os.environ['HOME'], '.recompute.conf')
# setup logger
logger = utils.get_logger(__name__)


class ConfigManager(object):
  """ConfigManager encapsulates the global config file."""

  def __init__(self, configfile=None):
    """
    Parameters
    ----------
    configfile : str, optional
      Path to the global config file (default None).
      By default, ConfigManager reads from `$HOME/.recompute.conf`.
    """
    # resolve config file
    self.configfile = configfile if configfile else CONFIG_FILE
    # read config from config file
    self.config = self.load() if self.config_exists else None

  def load(self, configfile=None):
    """Load config dictionary from config file.

    Parameters
    ----------
    configfile : str, optional
      Path to the global config file (default None).
      By default, `$HOME/.recompute.conf` is read.

    Returns
    -------
    configparser.ConfigParser
      ConfigParser instance read from `configfile`
    """
    # resolve config file
    configfile = configfile if configfile else self.configfile
    # create parser instance
    config = configparser.ConfigParser()
    # read from file
    config.read(self.configfile)
    return config

  def config_exists(self):
    """Does global config file exist?"""
    return os.path.exists(self.configfile)

  def generate(self, force=False, configfile=None):
    """Generate a sample config file

    Parameters
    ----------
    force : bool, optional
      When set to `True`, permits overwriting global config file (default False)
      Caution adviced. Your `$HOME/.recompute.conf` will be overwritten
    configfile : str, optional
      Path to the global config file (default None).
      By default, sample config is written to `$HOME/.recompute.conf`

    Returns
    -------
    configparser.ConfigParser
      ConfigParser instance read from generate `configfile`
    """
    # if config file exits
    if self.config_exists() and not force and not configfile:
      logger.info('Config File exists; add --force to overwrite')
      return
    # create config
    config = configparser.ConfigParser()
    config.add_section('general')         # add general section
    config.set('general', 'instance', '0')  # default instance
    config.set('general', 'remote_home', 'projects/')  # remote home folder

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
    """Update global config file with `config`

    Parameters
    ----------
    config : configparser.ConfigParser
      New configuration to be written to global config file
    """
    self.config = config
    # write to config file
    self.config.write(open(self.configfile, 'w'))
    logger.debug('config file updated')

  def get_instances(self):
    """Return a list of instances read from config file

    Returns
    -------
    list
      A list of (SectionProxy) instance sections read from config file
    """
    return [ self.config[section]
        for section in self.config.sections()
        if 'instance ' in section ]

  def get_instance(self, idx=None):
    """
    Parameters
    ----------
    idx : int, optional
      Index of instance to get from config file (default None)

    Returns
    -------
    configparser.SectionProxy
      An instance section from config file

    """
    if idx is None:
      idx = int(self.config['general']['instance'])
    try:
      self.config['instance {}'.format(idx)], 'No such instance in config'
      return self.config['instance {}'.format(idx)]
    except KeyError:
      print('There is no "instance {}" section in config'.format(idx))

  def get_default_instance(self):
    """Return default instance section from config file

    Returns
    -------
    configparser.SectionProxy
      The default instance section from config file
    """
    idx = int(self.config['general']['instance'])
    return self.get_instance(idx)

  def add_instance(self, instance):
    """Add an instance section to config file

    Parameters
    ----------
    instance : instance.Instance
      A new Instance to be added to config file
    """
    # get next index
    idx = len([ sec for sec in self.config.sections()
      if 'instance ' in sec ])
    # add new instance section to config file
    self.config['instance {}'.format(idx)] = {
        'username' : instance.username,
        'host' : instance.host,
        'password' : instance.password
        }
    # update config file
    self.update(self.config)
