import pytest
from recompute import config
import configparser


@pytest.fixture
def confman():
  return config.ConfigManager()


def test_load(confman):
  assert isinstance(confman.load(), configparser.ConfigParser)


def test_config_exists(confman):
  assert confman.config_exists()


def test_generate(confman):
  import os
  assert not confman.generate()
  configfile = '/tmp/recompute.conf'
  assert confman.generate(configfile=configfile)
  assert os.path.exists(configfile)


def test_update(confman):
  confman.update(confman.config)


def test_get_instances(confman):
  instances = confman.get_instances()
  assert len(instances) > 0
  assert isinstance(instances[-1], configparser.SectionProxy)


def test_get_instance(confman):
  assert isinstance(confman.get_instance(), configparser.SectionProxy)


def test_get_default_instance(confman):
  assert confman.get_default_instance() == \
      confman.get_instance(int(confman.config['general']['instance']))
