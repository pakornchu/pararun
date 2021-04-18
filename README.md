# PARARUN
Threaded command execution. Takes JSON-formatted command list, execute commands in parallel then write output to log files.

## Requirement
* Python 3.6 or later

## Usage
```
usage: pararun.py [-h] [--logdir LOGDIR] [--masterlog MASTERLOG]
                  [--mastererrlog MASTERERRLOG] [--threads THREADS]
                  [--lockretry LOCKRETRY]
                  cmdfile
```
### Required argument
* `cmdfile` Location of command list
### Options
* `--logdir LOGDIR` Log directory for command execution output
* `--masterlog MASTERLOG` Master execution log path
* `--mastererrlog MASTERERRLOG` Job STDOUT/STDERR execution log path
* `--threads N` Number of threads
* `--lockretry N` Number of file lock acquisition attempt before fallback to writeback queue

### JSON command list example
```
[
  {
    "cmd": "CMD",
    "name": "NAME"
  }
]
```

## Usage example
`pararun.py cmd.json --logdir /tmp/log --masterlog /tmp/log/master.log --mastererrlog /tmp/log/masterstdout.log`

## Output example
```
2021-04-15 11:55:43,533 INFO      [MainThread] Logging output to /tmp/log
2021-04-15 11:55:43,533 INFO      [Thread-1] Thread started
2021-04-15 11:55:43,533 INFO      [Thread-2] Thread started
2021-04-15 11:55:43,565 INFO      [Thread-1] Executing whoami
2021-04-15 11:55:43,607 INFO      [Thread-2] Executing uname -a
2021-04-15 11:55:43,674 INFO      [Thread-1] Completed whoami
2021-04-15 11:55:43,689 INFO      [Thread-1] 1 job(s) left in this queue
2021-04-15 11:55:43,701 INFO      [Thread-2] Completed uname -a
2021-04-15 11:55:43,701 INFO      [Thread-2] No more job for this worker, terminating
2021-04-15 11:55:43,701 INFO      [Thread-1] Executing pwd
2021-04-15 11:55:43,701 INFO      [Thread-1] Completed pwd
2021-04-15 11:55:43,701 INFO      [Thread-1] No more job for this worker, terminating
2021-04-15 11:55:43,702 INFO      [MainThread] Master logs /tmp/log/master.log
2021-04-15 11:55:43,702 INFO      [MainThread] Master error logs /tmp/log/masterstdout.log
```
