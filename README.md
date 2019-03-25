<p align="center"> 
<img src="banner.png" width="500">
</p>

---

A sweet tool for Remote Execution.


What is the chillest way one can train models in remote machines? 

- Do not worry about environment setup (dependencies)
- Don't bother choosing an instance to run on
- No more bash scripts to copy files back and forth

**re** provides a suite of features that empowers the user to focus on the experiments without having to worry about boring details listed above.

- Almost zero conf
- Abstract away boring repetitive details
- Ease of execution

You do need to follow a couple of conventions.

- Data goes into `data/`
- Any non-python file that is necessary for remote execution should be added to `.recompute/include`
- Any python file that shouldn't be pushed to remote machine should be added to `.recompute/exclude`

## Setup

```bash
pip install --user recompute
```

## Configuration

The configuration file is super-short.

```ini
[general]
instance = 0
remote_home = projects/

[instance 0]
username = grenouille
host = grasse.local
password = hen0s3datru1h

```

You can add credentials for remote machines directly into the configuration file or add them sequentially via command-line `re sshadd --instance='user@remotehost'`.

## Workflow

My machine learning workflow follows these steps:

- Copy code to remote machine `rsync`
- Setup dependencies `pip install`
- Download dataset and place them in `data/`
- Execute code in remote machine
- Get execution log
- Copy binaries generated `bin/`

wiht **re**, the tasks listed above can be accomplished with 4 commands, as below:

```bash
# re sshadd --instance='
re init                        # initalize [rsync, install]
re async "python3 x.py"        # start execution in remote
# (or) re sync "python3 x.py"  # blocking run (wait for completion)
re log                         # after a while
re pull "bin/ ./bin/" .        # pull generated binaries
```

- `init` creates local configuration files, setting up the environment for remote execution
  - Makes a list of local dependencies (python files)
  - Populates `requirements.txt` with required pypi packages
  - Installs pypi packages in remote machine
  - Copies local dependencies to remote machine using `rsync`
  - A copy of local folder is created in the remote machine, under `~/projects/`
- We could start execution in remote machine and wait for it to complete by using `sync` mode or just start remote execution and move on, using `async` mode
  - The command to be executed in remote machine, should be given as a string next to `sync` or `async` mode
- `re log` fetches log from remote machine
- `re pull` pulls any file from remote machine
  - Files are addressed by their relative paths

## Logging

**re** redirects the `stdout` and `stderr` of remote execution into `<project-name>.log`, which could be pulled to local machine by running `re log`. More often than not, it takes a while for execution to complete. So we start the execution in remote machine and check the log once in a while using `re log`. Or you could put this "once in a while" as a command-line argument and **re** pulls the log and shows you every "once in a while". It is recommended to use `logging` module to print information onto stdout, instead of `print` statements.

```bash
# fetch log from remote machine
re log
# . start execution in remote machine
# .. fetch log
re async "python3 nn.py"
re log
# . start execution 
# .. pull log every 20 seconds
re async "python3 nn.py"
re log --loop=20
```

## rsync

Files (local dependencies) can be synchronized by using `rsync` command. `rsync` is run in the background which copies files listed in `.recompute/rsync.db` to remote machine. `--force` switch forces **re** to figure out the local dependencies and update `rsync.db`.

```bash
re rsync  # --force updates .recompute/rsync.db
```

## Dependencies

`requirements.txt` is populated with python packages necessary for execution (uses `pipreqs` behind the scenes). `re install` reads `requirements.txt` and installs the packages in remote system.

```bash
# install dependencies
re install  # --force updates requirements.txt
# manual install
re install "torch tqdm"
```

## Manages Processes

**re** keeps track of all the remote processes it has spawned. We could list them out using `list` command and selectively kill processes using `kill` command.

```bash
# list live processes
re list
# +-------+--------------+-------+
# | Index |     Name     |  PID  |
# +-------+--------------+-------+
# |   0   |     all      |   *   |
# |   1   | zombie/spawn | 30601 |
# |   2   |    runner    | 31036 |
# +-------+--------------+-------+
# kill process [1]
re kill --idx=1
# kill them all
re purge
# or kill interactively with just `re kill`
```

## Upload/Download

You might wanna download or upload a file just once without having to include it in rsync database. We have `push` and `pull` commands. And there is a special command named `data` which downloads from space separated urls from command-line, into remote machine's `data/` directory.

```bash
# . upload from local machine to remote
# .. copy [current_dir/x/localfile] to [remote_home/projects/mynn1/x/]
re push "x/localfile x/"
# . download from remote machine to local
# .. copy [remote_home/projects/mynn1/y/remotefile] to [current_dir/y/remotefile]
re pull "y/remotefile y/"
# download IRIS dataset to remote machine's [data/]
re data https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data  # more urls can be added, separated by spaces
```

## Notebook

Sometimes you wanna run code snippets in a notebook. `re notebook` starts a remote jupyter notebook server and hooks it to a local port. The remote server is tracked (`re list`) and could be killed whenever necessary.

```bash
# . start notebook server in remote machine
# .. hook to local port
re notebook  # Cntl-c to quit
```

## Probe

`probe` command probes remote machines and provides us with a table of available machines with info on available resources.

```bash
re probe
# +--------------------------------+--------+----------+-----------+
# |        Machine                 | Status | GPU (MB) | Disk (MB) |
# +--------------------------------+--------+----------+-----------+
# | grenouille@grasse.local        | active |  10432   |     4238  |
# | slartibartfast@magrathea.local | active |   8642   |    12012  |
# +--------------------------------+--------+----------+-----------+
```

## Manual

`re man` gives you a detailed manual.

|   Mode   |                   Description                       |      Options          |           Example                |
|----------|-----------------------------------------------------|-----------------------|----------------------------------|
| init     | Setup current directory for remote execution        | --instance-idx        |  re init                         |
|          |                                                     |                       |  re init --instance-idx=1        |
| rsync    | Use rsync to synchronize local files with remote    | --force               |  re rsync                        |
| sshadd   | Add a new instance to config                        | --instance            |  re sshadd --instance="usr@host" |
| install  | Install pypi packages in requirements.txt in remote | cmd, --force          |  re install                      |
|          |                                                     |                       |  re install "pytorch tqdm"       |
| sync     | Synchronous execution of "args.cmd" in remote       | cmd, --force, --rsync |  re sync "python3 x.py"          |
| async    | Asynchronous execution of "args.cmd" in remote      | cmd, --force, --rsync |  re async "python3 x.py"         |
| log      | Fetch log from remote machine                       | --loop, --filter      |  re log                          |
|          |                                                     |                       |  re log --loop=2                 |
|          |                                                     |                       |  re log --filter="pattern"       |
| list     | List out processes alive in remote machine          | --force               |  re list                         |
| kill     | Kill a process by index                             | --idx                 |  re kill                         |
|          |                                                     |                       |  re kill --idx=1                 |
| purge    | Kill all remote process that are alive              | None                  |  re purge                        |
| ssh      | Create an ssh session in remote machine             | None                  |  re ssh                          |
| notebook | Create jupyter notebook in remote machine           | --run-async           |  re notebook                     |
| push     | Upload file to remote machine                       | cmd                   |  re push "x.py y/"               |
| pull     | Download file from remote machine                   | cmd                   |  re pull "y/z.py ."              |
| data     | Download data from web into data/ folder of remote  | cmd                   |  re data "url1 url2 url3"        |
| man      | Show this man page                                  | None                  |  re man                          

## Contribution

All kinds of contribution are welcome.

- Somethin went wrong?
- What feature is missing?
- What could be done better?

Raise an [issue](https://github.com/suriyadeepan/recompute.py/issues).
Add a pull request.

## License

Copyright (c) 2019 Suriyadeepan Ramamoorthy. All rights reserved.

This work is licensed under the terms of the MIT license.  
For a copy, see <https://opensource.org/licenses/MIT>.
