import os

from recompute import process
from recompute import cmd
from recompute import utils

# setup logger
logger = utils.get_logger(__name__)

# RSYNC DB
RSYNC_DB = '.recompute/rsync.db'
REQS = 'requirements.txt'
INCLUDE = '.recompute/include'
EXCLUDE = '.recompute/exclude'


class Bundle(object):

  def __init__(self, name=None):
    # get current path
    self.path = os.path.abspath('.')
    # get name of current directory if custom name isn't given
    self.name = name if name else self.path.split('/')[-1]
    # local db
    self.db = RSYNC_DB
    # init include/exclude files
    self.init_include_exclude()
    # update bundle dependencies
    self.update_dependencies()

  def update_dependencies(self):
    """ Update dependencies """
    # get a list of files (local dependencies)
    self.files = list(self.get_local_deps())
    # add INCLUDE; remote EXCLUDE
    self.files = self.inclusion_exclusion()
    logger.info(' '.join(self.files))
    # create a file containing list of dependencies
    self.populate_requirements()
    # get a list of dependencies (python packages)
    self.requirements = self.get_requirements()
    # create a file containting list of local dependencies
    self.populate_local_deps()

  def init_include_exclude(self):
    if not os.path.exists(INCLUDE):
      open(INCLUDE, 'w').close()
    if not os.path.exists(EXCLUDE):
      open(EXCLUDE, 'w').close()

  def inclusion_exclusion(self):
    # read from .recompute/include
    include = [ f for f in open(INCLUDE).readlines() if f.strip() ]
    # read from .recompute/exclude
    exclude = [ f for f in open(EXCLUDE).readlines() if f.strip() ]
    # update self.files
    self.files = [ f for f in self.files if f not in exclude ]
    self.files.extend(include)
    return list(set(self.files))

  def get_local_deps(self):
    """ Run a search for *.py files in current directory """
    for dirpath, dirnames, filenames in os.walk("."):
      for filename in [f for f in filenames if f.endswith(".py")]:
        yield os.path.join(dirpath, filename)

  def populate_local_deps(self):
    """ Write local dependencies to file """
    with open(self.db, 'w') as db:
      for filename in self.files:
        logger.info(filename)
        db.write(filename)
        db.write('\n')

  def populate_requirements(self):
    # . get a list of pip packages
    # .. write to requirements.txt
    assert process.execute(
        cmd.REDIRECT_STDOUT_NULL.format(command=cmd.PIP_REQS)
        )
    # with open(REQS, 'a') as f_req:
    #   f_req.write('\npytest')

  def get_requirements(self):
    reqs = [ line.replace('\n', '')
        for line in open(REQS).readlines()
        if line.replace('\n', '').strip()
        ]
    logger.info(reqs)
    return reqs
