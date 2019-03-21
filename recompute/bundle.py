import os
import logging

from recompute.process import execute
from recompute.config import LOCAL_CONFIG_DIR

# setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RSYNC DB
RSYNC_DB = '.recompute/rsync.db'
REQS = 'requirements.txt'


class Bundle(object):

  def __init__(self, name=None):
    # get current path
    self.path = os.path.abspath('.')
    # get name of current directory if custom name isn't given
    self.name = name if name else self.path.split('/')[-1]
    # local db
    self.db = RSYNC_DB
    # create local conf directory if it doesn't exist
    if not os.path.exists(LOCAL_CONFIG_DIR):
      os.makedirs(LOCAL_CONFIG_DIR)
    # update bundle dependencies
    self.update_dependencies()

  def update_dependencies(self):
    """ Update dependencies """
    # get a list of files (local dependencies)
    self.files = list(self.get_local_deps())
    logger.debug(' '.join(self.files))
    # create a file containing list of dependencies
    self.populate_requirements()
    # get a list of dependencies (python packages)
    self.requirements = self.get_requirements()
    # create a file containting list of local dependencies
    self.populate_local_deps()

  def get_local_deps(self):
    """ Run a search for *.py files in current directory """
    for dirpath, dirnames, filenames in os.walk("."):
      for filename in [f for f in filenames if f.endswith(".py")]:
        yield os.path.join(dirpath, filename)

  def populate_local_deps(self):
    """ Write local dependencies to file """
    with open(self.db, 'w') as db:
      for filename in self.files:
        logger.debug(filename)
        db.write(filename)
        db.write('\n')

  def populate_requirements(self):
    # . get a list of pip packages
    # .. write to requirements.txt
    assert execute('pipreqs . --force')
    # add pytest to requirements.txt
    with open(REQS, 'a') as f_req:
      f_req.write('\npytest')

  def get_requirements(self):
    reqs = [ line.replace('\n', '')
        for line in open(REQS).readlines()
        if line.replace('\n', '')
        ]
    logger.debug(reqs)
    return reqs
