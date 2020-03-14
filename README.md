# remote_internet_test

This script will pull down a speed test, store the test in a sqlite database, and then attempt to send any unsent results to an email address. 

Things to do before this will work: 
1) Create a text file in the directory containing this project dir (if this readme is in /dev/bla, put it in /dev) called testpass.txt, and put the gmail password in it
2) After running pip install -r requirements.txt, find the pyspeedtest.py file, go to line 186, and change 'www.speedtest.net' to 'c.speedtest.net'. 
