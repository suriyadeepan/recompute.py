<p align="center"> 
<img src="banner.png" width="500">
</p>

---

A sweet tool for Remote Computation


Some jobs must be assigned to powerful machines equipped with GPUs. Training a language model on 60 million tamil news articles. Some jobs could be run in my macbook. Locally. Quickly. Bayesian Logistic Regression on IRIS data. Not every job fits nicely into these two categories. There are jobs that take 4 to 7 minutes to run in my macbook. I let them run. Because getting it to run in a remote machine is just too much work. I would rather waste 4-7 minutes? Oh you'd do something else during these 4-7 minutes. Lets not kid ourselves. We are bad at multi-tasking because we are not wired for that. [GTD](https://www.youtube.com/watch?v=CHxhjDPKfbY) cannot transcend biological limitations.

What would [Bill Murray](https://plato.stanford.edu/entries/nietzsche/#EterRecuSame) do?

Why is running code in remote machine so painful? If the jobs are all similar (python, machine learning), can we not automate this process? What is the process anyway? 

- Copy *necessary* code to remote machine `rsync`
- Set up dependencies `pip install`
- Download datasets; place them in the right directory `data/`
- Run code in remote
- Copy binaries generated `bin/`

I can't think of anything else. This is everything I've done over and over and over again. This is 2016, 2017 and 2018 for me. (Question to self : Wtf are you doing with your life?)

Why didn't I automate this? Because I was young and dumb and full of energy. Now that I'm seeing symptoms of ageing, I figured I got to do something about this. And I did.

I created a command-line tool called [recompute.py](https://github.com/suriyadeepan/recompute), which automates the process above.

![](#)

Pretty cool, right? I thought so. It takes care of pretty much everything. Only catch is, you follow a couple of conventions.

- Data goes into `data/`
- Any non-python file that is necessary for remote execution should be added to `.recompute/include`
- Any python file that shouldn't be pushed to remote machine should be added to `.recompute/exclude`

The configuration file is long and boring, which is a good thing apparently. 

```ini
[DEFAULT]
default=user2@remotehost
localuser=user1
localpass=xxxxxxx
defaultuser=user2
defaulthost=remotehost
remote_home=~/projects/
```

You can add credentials for remote machines directly into the configuration file or add them sequentially via command-line `recompute sshadd --login='user@remotehost'`.

## Process

The process I've described above can be completed in 3 steps with 3 commands - `init`, `async/sync`, `log`. `init` creates local configuration files, setting up the environment for executing `recompute`. Makes a list of local dependencies (python files). Populates `requirements.txt` with required pypi packages. Installs pypi packages in remote machine. Copies local dependencies to remote machine using `rsync`. A copy of local folder is created in the remote machine, under `~/projects/`.

We could start execution in remote machine and wait for it to complete by using `sync` mode. Or just start remote execution and move on, using `async` mode. The command to be executed in remote machine, should be given as a string next to `sync` or `async` mode. `log` command fetches log from remote machine.

```bash
recompute init  # initalize [rsync, install]
recompute async "python3 nn1_2.py"      # start execution in remote
# (or) recompute sync "python3 nn1.py"  # blocking run (wait for completion)
recompute log   # after a while
```

## Logging

`recompute.py` redirects the `stdout` and `stderr` of remote execution into `project-name.log`, which could be pulled to local machine by running `recompute log`. More often than not, it takes a while for execution to complete. So we start the execution in remote machine and check the log once in a while using `recompute log`. Or you could put this "once in a while" as a command-line argument and `recompute.py` pulls the log and shows you every "once in a while". It is recommended to use `logging` module to print information onto stdout, instead of `print` statements.

```bash
# fetch log from remote machine
recompute log
# . start execution in remote machine
# .. fetch log
recompute async "python3 nn.py"
recompute log
# . start execution 
# .. pull log every 20 seconds
recompute async "python3 nn.py"
recompute log --loop=20
```

## rsync

Files (local dependencies) can be synchronized by using `rsync` command. `rsync` is run in the background which copies files listed in `.recompute/rsyc.db` to remote machine. `--force` switch forces `recompute.py` to figure out the local dependencies and update `rsync.db`. 

```bash
# rsync
recompute rsync  # --force updates .recompute/rsync.db
```

## Dependencies

`requirements.txt` is populated with python packages necessary for execution (uses `pipreqs` behind the scenes). `recompute install` reads `requirements.txt` and installs the packages in remote system.

```bash
# install dependencies
recompute install  # --force updates requirements.txt
```

## Track Processes

`recompute` keeps track of all the running processes it has spawned. We could list them out using `list` command and selectively kill processes using `kill` command. 

```bash
# list live processes
recompute list
#  [0] * all
#  [1] remote_2484596 (cd ~/projects/mynn1/ && python3 nn1.py)
#  [2] remote_1062295 (cd ~/projects/mynn2/ && python3 nn2.py)
# kill process [1]
recompute kill --idx=1
# kill them all [0]
recompute kill --idx=0
# or kill interactively with just `recompute kill`
```

## Upload/Download

You might wanna download or upload a file just once without having to include it in rsync database. We have `push` and `pull` commands. And there is a special command named `data` which downloads from space separated urls from command-line, into remote machine's `data/` directory.

```bash
# . upload from local machine to remote
# .. copy [current_dir/x/localfile] to [remote_home/projects/mynn1/x/]
recompute push "x/localfile x/"
# . download from remote machine to local
# .. copy [remote_home/projects/mynn1/y/remotefile] to [current_dir/y/remotefile]
recompute pull "y/remotefile y/"
# download IRIS dataset to remote machine's [data/]
recompute data https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data  # more urls can be added, separated by spaces
```

## Notebook

Sometimes you wanna run code snippets in a notebook. `recompute notebook` starts a remote jupyter notebook server and hooks it to a local port. The remote server is tracked (`recompute list`) and could be killed whenever necessary.

```bash
# . start notebook server in remote machine
# .. hook to local port
recompute notebook  # Cntl-c to quit
# list processes
recompute list
#  [0] * all
#  [1] remote_5889010 (cd ~/projects/mynn1/ && jupyter notebook --no-browser --port=8833 --NotebookApp.token="" .)
recompute kill --idx=1
```

## Probe

Sharing can be worse than hell if you are sharing something valuable with uncivilized people. This is the [Tragedy of the Commons](https://en.wikipedia.org/wiki/Tragedy_of_the_commons). Wait, it gets worse. What if you are alloted resources based on the "[quality](https://en.wikipedia.org/wiki/Quis_custodiet_ipsos_custodes%3F)" of your work? Just thinking about it gives me anxiety. Fortunately I just have to deal with the Tragedy of the Commons, where multiple remote machines exist and some are free to use. Choose the machine with the most free resources? No, we are better than that. We choose a machine that has just enough resources to get our job done. Right now, we choose this machine manually. `probe` command probes remote machines and provides us with a table of available machines and their corresponding available resources.

```bash
recompute probe
```

**NOTE** : Insert table here

## Issues

There are a lot of them.

- pypi packages are installed globally in the remote machine. Creating a virtual environment for each project would be cleaner. Create a switch to toggle this behaviour, may be?

- Instead of installing pip packages and copying files to remote machine, we could bundle the necessary packages and files into one stand-alone package and push it to remote machine. We should be able to execute this package in remote machine, without having to worry about dependencies. May be use `cloudpickle` for this?

- `probe` gives us GPU memory and free disk space information. Can we use this information to find the best machine to use for execution? What's the criteria for choosing the best machine? It should fit the memory requirements of our model. Its not impossible to calculate this. But it is  too much work. May be we could get this information from the user?

  > " I wanna run `x.py` quickly and see the output. I don't care where you run it. Just get me the output soon. Oh, by the way, it might require 3 GB disk space and 1.5 GB GPU memory. Report back to me ASAP."

  I almost named the tool "fixer" but changed the name after realizing it would confuse people. `fixer` sounds cool but `recompute` is more memorable. 

- Is there a more "natural" way to view the running process? Is it possible to redirect the stdout/stderr of remote process to current terminal?
