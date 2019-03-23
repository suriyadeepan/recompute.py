from recompute import process
from recompute import cmd
from recompute import utils

import logging

import pickle
import os

# setup logger
logger = utils.get_logger(__name__)
# table cache
PROBE_CACHE = '.recompute/table'


class Instance(object):

  def __init__(self, username=None, password=None, host=None):
    self.username = username
    self.password = password
    self.host = host

  def resolve_str(self, loginstr):
    try:
      self.username, self.host = loginstr.strip().split('@')
      return self
    except ValueError:
      logging.error('Check Login [{}]'.format(loginstr))
      exit()

  def resolve_conf(self, conf):
    self.username = conf['username']
    self.password = conf['password']
    self.host = conf['host']
    return self

  def __repr__(self):
    return '{username}@{host}'.format(
        username=self.username, host=self.host
        )

  def __eq__(self, other):
    return self.username == other.username and \
        self.password == other.password and \
        self.host == other.host


class InstanceManager(object):

  def __init__(self, confman):
    self.confman = confman

  def add_instance(self, instance):
    # make sure the instance is active
    assert self.is_active(instance), 'Instance Inactive'
    # check if it's a duplicate
    assert len([ i for i in self.get_all()
      if i == instance ]) == 0, 'Duplicate Instance'
    # add instance to config file
    self.confman.add_instance(instance)

  def is_active(self, instance):
    return not process.fetch_stderr( ' '.join([
      cmd.SSH_HEADER.format(password=instance.password),
      cmd.SSH_TEST.format(username=instance.username, host=instance.host)
      ]))

  def get(self, idx=None):
    # get instance config
    instance = self.confman.get_instance(idx)
    # make sure the instance exists in config
    assert instance, 'Instance inactive'
    # return an instance
    return Instance(instance['username'], instance['password'], instance['host'])

  def get_all(self):
    return [ Instance().resolve_conf(instance)
        for instance in self.confman.get_instances() ]

  def get_active(self):
    return [ instance for instance in self.get_all()
        if self.is_active(instance) ]

  def fetch(self):
    # get all instances
    for instance in self.get_all():
      if self.is_active(instance):  # find an instance that's active
        return instance

  def probe(self, force=False):

    if not force and os.path.exists(PROBE_CACHE):
      return utils.tabulate_instances(pickle.load(open(PROBE_CACHE, 'rb')))

    # init dictionary of instances
    instances = {}
    # get active instances
    for instance in self.get_active():
      # init row
      instances[str(instance)] = [ str(instance), 'active', '-', '-' ]
      logger.info(instance)
      try:
        # gather info from remote machines
        # TODO : execute them in one session
        free_gpu_memory = int(
            process.remote_execute(cmd.GPU_FREE_MEMORY, instance)[-1]
            )
        logger.info('FREE GPU')
        logger.info(free_gpu_memory)
        free_disk_space = utils.parse_free_results(
            process.remote_execute(cmd.DISK_FREE_MEMORY, instance)[-1]
            )
        logger.info('FREE DISK')
        logger.info(free_disk_space)
        # update dictionary
        instances[str(instance)][2] = free_gpu_memory
        instances[str(instance)][3] = free_disk_space
      except ValueError:
        # something wrong? -> blame the host..
        instances[str(instance)][1] = 'inactive'
        continue
    # cache table
    pickle.dump(instances, open(PROBE_CACHE, 'wb'))
    return utils.tabulate_instances(instances)
