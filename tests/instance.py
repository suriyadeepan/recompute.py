import pytest
from recompute.instance import Instance
from recompute.instance import InstanceManager
from recompute.config import ConfigManager


@pytest.fixture
def instance():
  return InstanceManager(ConfigManager()).get()


@pytest.fixture
def instanceman():  # cached remote
  return InstanceManager(ConfigManager())


def test_is_active(instanceman, instance):
  assert instanceman.is_active(instance)


def test_get(instanceman, instance):
  assert instanceman.is_active(instanceman.get())


def test_get_all(instanceman, instance):
  instances = instanceman.get_all()
  assert len(instances) > 0
  assert isinstance(instances[-1], type(instance))


def test_get_active(instanceman, instance):
  instances = instanceman.get_active()
  assert len(instances) > 0
  assert isinstance(instances[-1], type(instance))


def test_fetch(instanceman, instance):
  assert instanceman.is_active(instanceman.fetch())


def test_add_instance(instanceman, instance):
  with pytest.raises(AssertionError):
    instanceman.add_instance(Instance('dummy', 'dummy', 'dummy'))
    instanceman.add_instance(instance)


def test_probe(instanceman, instance):
  # from recompute import utils, process, cmd
  assert instanceman.probe(force=True)
  assert instanceman.probe()


def test_resolve_str(instanceman, instance):
  assert str(Instance().resolve_str('a@b')) == 'a@b'


def test_resolve_conf(instanceman, instance):
  instance_x = instanceman.get(0)
  assert isinstance(instance_x, type(instance))
  instance_y = Instance().resolve_conf(instanceman.confman.config['instance 0'])
  assert instance_x == instance_y
