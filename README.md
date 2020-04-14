# remote_internet_test

This script will pull down a speed test, store the test in a sqlite database, and then attempt to send any unsent results to an email address. 

Before this script works, you need to set environment variables TESTUSER (gmail address of account to send email from), and TESTPASS (gmail password of account to send email from)

Current output of ./testinternet.py -h

```
usage: testinternet.py [-h] [-t] [-e EMAIL] [-i ITERATIONS] [-n NAME] [-v]

Tests the internet, stores results and sends out results. The environment
variables "TESTUSER" and "TESTPASS" must be set to the email and password of
the gmail account that will be used to send reesults. If no arguments are
supplied, the script is ran as ./script -t -a

optional arguments:
  -h, --help            show this help message and exit
  -t, --test            Run a speed test, and store it
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

```
