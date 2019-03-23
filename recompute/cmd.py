"""cmd.py

Unorganized messy blob of commands.

TODO
----
This definitely requires better organization.
Commands in string format should be replaced with functions with arguments for formatting the command.

"""
# __pipreqs__ resolves pypi package requirements
# and writes it to requirements.txt
PIP_REQS = 'pipreqs . --force'

# __nvidia-smi__ gives a status report on the GPU
# we format the results to get free GPU memory
GPU_FREE_MEMORY = 'nvidia-smi \
    --query-gpu=memory.free \
    --format=csv,nounits,noheader'

# __free__ outputs free disk space available in device
# we format it using `utils.parse_free_results`
DISK_FREE_MEMORY = "free -m"

# __jupyter-notebook__ starts a notebook server in remote device
# `port_num` acts as a handle to keep track of the server
JUPYTER_SERVER = 'jupyter-notebook --no-browser --port={port_num}\
    --NotebookApp.token="" .'

SSH_HEADER = 'sshpass -p {password}'

# we hook up the remote notebook server to a local port via __ssh__
# `client_port_num` and `server_port_num` are required
JUPYTER_CLIENT = SSH_HEADER + ' ' + 'ssh -N -L \
    {client_port_num}:localhost:{server_port_num} \
    {username}@{host}'

# __ps__ results are filtered using __grep__ with a the pattern __re.runner__
# to identify the processes we started in the remote system
PROCESS_LIST_LINUX = 'ps axf | grep re.runner | grep -v grep'

# process list for __mac__
# ...
PROCESS_LIST_OSX = 'ps aux | grep re.runner | grep -v grep'

# filter __ps__ results using __pid__
# ...
PROCESS_PID_LINUX = 'ps -aux | grep {pid}'

# __kill__ process with pid as handle
# ...
KILL_PROCESS = 'kill -9 {}'

# __scp__ copies file from remote device to local device
# one file at a time, fellas!
SCP_FROM_REMOTE = 'scp -r {username}@{host}:{remotepath} {localpath}'

# __scp__ copies file from local device to remote device
# one file at a time, fellas!
SCP_TO_REMOTE = 'scp -r {localpath} {username}@{host}:{remotepath}'

# __rsync__ synchonizes files listed in `.recompute/rsync.db`
# with remote device
RSYNC = 'rsync -a --files-from={deps_file} . \
        {username}@{host}:{remote_dir}'

# execute __cmd__ in remote device via __ssh__
# ...
SSH_EXEC = 'ssh {username}@{host} \'{cmd}\''

# __ssh__ execute in remote device with a pseudo tty terminal
# ...
SSH_EXEC_PSEUDO_TERMINAL = 'ssh -t {username}@{host} \'{cmd}\''

# __nohup__ ensures uninterrupted remote execution
# ...
SSH_EXEC_ASYNC = 'ssh {username}@{host} \'nohup {cmd} > {logfile} \
    2>{logfile} & echo $!\''

# start __ssh__ session
# changed into `remote_dir`
__SSH_INTO_REMOTE_DIR = 'ssh -t {username}@{host} \
            "cd {remote_dir}; exec \\$SHELL --login"'
SSH_INTO_REMOTE_DIR = SSH_HEADER + ' ' + __SSH_INTO_REMOTE_DIR

# with __mkdir__, create directory in remote device
# ...
SSH_MAKE_DIR = 'ssh {username}@{host} mkdir -p {remote_dir}'

# run `exit` in a __ssh__ session
# to test if the instance works
SSH_TEST = 'ssh {username}@{host} \'exit\''

# redirect __stdout__ and __stderr__ to `logfile`
# push process to background using __&__
CMD_LOG_FOOTER_ASYNC = ' > {logfile} 2>{logfile} &'

# redirect __stdout__ and __stderr__ to `logfile`
CMD_LOG_FOOTER = ' > {logfile} 2>{logfile}'

# use __date__ to get "laste modified" time-stamp of a file
# ...
LAST_MODIFIED = 'date -r {filename}'

# __cd__ into a path
# NOTE : do we need this? seems silly!
CD = 'cd {path}'

# set `SIGINT` __trap__
# execute `kill` when SIGINT signal is received
TRAP = 'trap "kill 0" SIGINT'

# run `command` and redirect __stdout__ and __stderr__ to `logfile`
# ...
REDIRECT_STDOUT = '{command} > {logfile} 2>&1'

# run `command` and redirect __stdout__ and __stderr__ to /dev/null
# we basically throw away outputs
REDIRECT_STDOUT_NULL = '{command} > /dev/null 2>&1'

# __wait__ for user interruption
# NOTE : again, do we need this?
WAIT = 'wait'

# execute bash script `runner`
# ...
EXEC_RUNNER = 'bash {runner}'

# set `INT` and `TERM` __trap__
# exit when trap is triggered
TRAP_INT_TERM = 'trap "exit" INT TERM'

# set `EXIT` __trap__
# `kill` process when trap is triggered
TRAP_EXIT = 'trap "kill 0" EXIT'


def make_wget(urls):
  """Download multiple URLs with `wget`

  Parameters
  ----------
  urls : list
    A list of URLs to download from
  """
  return 'wget -c {}'.format(' '.join(urls))


def make_traps():
  """Return a list of traps.

  We place these traps, one in a line, in the `runner` script.
  """
  return [ TRAP_INT_TERM, TRAP_EXIT ]


def kill_procs(pids):
  """ Kill a list of processes using their PIDs

  Parameters
  ----------
  pids : list
    A list of process id's (processes that ought to be killed)
  """
  return ' '.join( ['kill -9'] + [ str(pid) for pid in pids ] )
