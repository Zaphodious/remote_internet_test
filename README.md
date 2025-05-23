# remote_internet_test

This script will pull down a speed test, store the test in a sqlite database, and then attempt to send any unsent results to an email address. 

## Getting Started

1. Make sure you have python3 and python3-venv

1. run either setup_and_run.sh or setup_no_run.sh

1. Modify the newly-created run.sh with environment variables TESTUSER (the gmail address that results will be sent *from*), and TESTPASS (the password of TESTUSER). Edit the arguments for testinternet.py as appropriate.

1. run run.sh

## Current output of ./testinternet.py -h

```
usage: testinternet.py [-h] [-t] [-p] [-up UNIXPING] [-e EMAIL]
                       [-i ITERATIONS] [-n NAME] [-v] [-u] [-s SCPHOST]
                       [-d DIRECTORY]

Tests the internet, stores results and sends out results. The environment
variables "TESTUSER" and "TESTPASS" must be set to the email and password of
the gmail account that will be used to send reesults. If no arguments are
supplied, the script is ran as ./script -t -a

optional arguments:
  -h, --help            show this help message and exit
  -t, --test            Run a speed test, and store it
  -p, --ping            Run a ping test, and store it. -t/--test is ignored
                        when using this command. Up/Down speed is recorded as
                        NULL for this test.
  -up UNIXPING, --unixping UNIXPING
                        Domain to ping, using the system ping command. Does
                        not work on Windows
  -e EMAIL, --email EMAIL
                        Email to which to send the unsent results. If no email
                        is provided, results will be cached and sent next time
                        an address is provided.
  -i ITERATIONS, --iterations ITERATIONS
                        Number of times to take the test (default 5)
  -n NAME, --name NAME  Name of the system to use when sending an email
                        (defaults to the hostname of the machine)
  -v, --verbose         Display the speed test results as they are collected
                        (defaults to false, and status messages are printed
                        regardless.
  -u, --utc             Sends the results with utc time. Default is to use the
                        timezone of the host machine
  -s SCPHOST, --scphost SCPHOST
                        Uploads the results to a location over SSH
  -d DIRECTORY, --directory DIRECTORY
                        The path of directory on the SCP host machine in which
                        to put the report file and logs
```

## Cron

To run as a cron job, make a proxy trigger script (easy way to ensure the proper working dir) in your home folder with the following content:
```
#!/bin/bash
cd <absolute path to the project directory>
. run.sh
```
In your crontab, past this in (edit the time to suit, this one runs every day at 7am)
```
* 7 * * * <absolute path to proxy script>  > <absolute path to log file>
```
