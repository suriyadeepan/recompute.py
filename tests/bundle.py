import pytest
from recompute.bundle import Bundle


@pytest.fixture
def bundle():
  return Bundle()


def test_get_local_deps(bundle):
  assert len(list(bundle.get_local_deps())) > 0


def test_get_requirements(bundle):
  assert len(bundle.get_requirements()) > 0


def test_rsync_db(bundle):
  from recompute.bundle import RSYNC_DB
  assert len(open(RSYNC_DB).readlines()) > 1


def test_requirements(bundle):
  from recompute.bundle import REQS
  assert len(open(REQS).readlines()) > 1
