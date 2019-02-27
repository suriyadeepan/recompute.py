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

# wget multiple urls
def _WGET(urls): return 'wget -c {}'.format(' '.join(urls))
