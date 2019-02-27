GPU_FREE_MEMORY = 'nvidia-smi \
    --query-gpu=memory.free \
    --format=csv,nounits,noheader'
DISK_FREE_MEMORY = "awk '/^Mem/ {print $4}' <(free -m)"
JUPYTER_SERVER = 'jupyter notebook --no-browser --port={port_num} --NotebookApp.token=""'
JUPYTER_CLIENT = 'sshpass -p {password} \
    ssh -N -L {client_port_num}:localhost:{server_port_num} \
    {username}@{host}'
PROCESS_LIST_LINUX = 'ps -aux | grep {}'
KILL_PROCESS = 'kill -9 {}'
SSH_HEADER = 'sshpass -p {password}'
SCP_FROM_REMOTE = 'scp -r {username}@{host}:{remotepath} {localpath}'
SCP_TO_REMOTE = 'scp -r {localpath} {username}@{host}:{remotepath}'
RSYNC = 'rsync -a --files-from={deps_file} . \
        {username}@{host}:{remote_dir}'
SSH_EXEC = 'ssh {username}@{host} {cmd}'
__SSH_INTO_REMOTE_DIR = 'ssh -t {username}@{host} \
            "cd {remote_dir}; exec \\$SHELL --login"'
SSH_INTO_REMOTE_DIR = SSH_HEADER + ' ' + __SSH_INTO_REMOTE_DIR
SSH_MAKE_DIR = 'ssh {username}@{host} mkdir -p {remote_dir}'
CMD_LOG_FOOTER = ' > {logfile} 2>{logfile} &'
LAST_MODIFIED = 'date -r {filename}'


def make_wget(urls):
  """ `wget` from multiple urls """
  return 'wget -c {}'.format(' '.join(urls))
