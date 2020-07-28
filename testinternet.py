#!./env/bin/python3

import smtplib
import pyspeedtest
from sqlalchemy import create_engine, Column, ForeignKey, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import time
import datetime
import os
import argparse
import socket
import sys
import subprocess
import re

to_email = "" # Email that the message will be sent to. Set via the -e/--email command line arg
times_to_take_test = 5 # Number of times that the test will be run. Set via the -i/--iterations command line arg
devicename = "nohostnamedetected" # Name of the device that will be reported on the test. Default is the hostname of the machine. Set via the -n/--name command line arg
useutc = False # If true, uses utc time when sending the email. If false, uses the timezone of the server. set via -u/--utc
pingtest = False

try:
    devicename = socket.gethostname()
except:
    pass

def get_gmail_creds():
    gmail_user = os.environ['TESTUSER']
    gmail_pass = os.environ['TESTPASS']
    return (gmail_user, gmail_pass)

Base = declarative_base()
class TestResult(Base):
    __tablename__ = 'testresults'
    id = Column(Integer, primary_key=True)
    date = Column(Float)
    ping = Column(Float, default=0)
    upload = Column(Float, default=0)
    download = Column(Float, default=0)
    sent = Column(Boolean, default=False)

    def __repr__(self):
        return '{{"date":{date},"ping":{ping},"upload":{upload},"download":{download}}}'.format(date=self.date, ping=self.ping, upload=self.upload, download=self.download)

def make_mbps(bps):
    return round(bps / 1000000, 2)

def record_speed_test(sess):
    try:
        record = None
        st = pyspeedtest.SpeedTest()
        record = TestResult(date=time.time())
        # Adding results seperately, so that if any errors occur we still have results for the previous steps.
        record.ping = round(st.ping(), 2)
        if (not pingtest):
            record.download = make_mbps(st.download())
            record.upload = make_mbps(st.upload())
    except:
        print("Speed Test didn't complete")
    finally:
        sess.add(record)
        # sess.commit()
        return record

upingreg_raw = r'time=[0-9\.]*'
upingreg = re.compile(upingreg_raw)


def do_unix_ping_test(sess):
    try:
        record = None
        record = TestResult(date=time.time())
        # Adding results seperately, so that if any errors occur we still have results for the previous steps.
        ping_response = subprocess.Popen(["ping", "-c 1", "-W 100", "www.google.com"], stdout=subprocess.PIPE).stdout.read()
        timeres_str = upingreg.findall(ping_response.decode('UTF-8'))[0].replace('time=', '')
        timeres = float(timeres_str)
        record.ping = timeres
    except Exception as e:
        print("Speed Test didn't complete")
    finally:
        sess.add(record)
        # sess.commit()
        return record


def make_email(subject, body):
    user = os.environ['TESTUSER']
    return """\
FROM: {user}
TO: {to_email}
SUBJECT: {subject}

{body}
    """.format(user=user, to_email=to_email, subject=subject, body=body)

def send_an_email(subject, body):
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.ehlo()
    user, password = get_gmail_creds()
    message = make_email(subject, body)
    server.login(user, password)
    server.sendmail(user, to_email, message)
    server.close()
    return True


def format_results_for_email(q):
    messagestring = """\
| Time and Date | Ping (ms) | Download (mbps) | Upload (mbps) | Device |
| ------------- | --------- | ------------- | --------------- | ------ |
"""
    for rec in q:
        dt = ""
        if (useutc):
            dt = datetime.datetime.utcfromtimestamp(rec.date)
        else:
            dt = datetime.datetime.fromtimestamp(rec.date).strftime('%Y-%m-%d %H:%M:%S %z')
        messagestring += "| {date} | {ping} | {download} | {upload} | {devicename} |\n".format(
            date=dt,
            ping=rec.ping,
            download=rec.download,
            upload=rec.upload,
            devicename=devicename
        )
    return messagestring

def send_results_email(sess):
    try:
        u = sess.query(TestResult).filter(TestResult.sent==False).all()
        send_an_email("Speed Test Results from {today} from {devicename}".format(devicename=devicename, today=datetime.date.today()), format_results_for_email(u))
        for x in u:
            x.sent = True 
        sess.commit()
    except Exception as e:
        print('results not sent today')
        print(e)

def init_db():
    engine = create_engine('sqlite:///db.sqlite')
    Base.metadata.create_all(engine)
    DBSession = sessionmaker(bind=engine)
    return DBSession()

if __name__ == "__main__":
    parser  = argparse.ArgumentParser(description=' Tests the internet, stores results and sends out results. The environment variables "TESTUSER" and "TESTPASS" must be set to the email and password of the gmail account that will be used to send reesults. If no arguments are supplied, the script is ran as ./script -t -a')
    parser.add_argument('-t', '--test', help='Run a speed test, and store it', action="store_true")
    parser.add_argument('-p', '--ping', help='Run a ping test, and store it. -t/--test is ignored when using this command.', action="store_true")
    parser.add_argument('-up', '--unixping', help='Run a ping test, using the systems ping command. Ignores -p and -t. Does not work on Windows.', action="store_true")
    parser.add_argument('-e', '--email', help='Email to which to send the unsent results. If no email is provided, results will be cached and sent next time an address is provided.')
    parser.add_argument('-i', '--iterations', type=int, help='Number of times to take the test (default 5)')
    parser.add_argument('-n', '--name', help='Name of the system to use when sending an email (defaults to the hostname of the machine)')
    parser.add_argument('-v', '--verbose', help='Display the speed test results as they are collected (defaults to false, and status messages are printed regardless.', action="store_true")
    parser.add_argument('-u', '--utc', help='Sends the results with utc time. Default is to use the timezone of the host machine', action="store_true")
    args = parser.parse_args()
    sess = init_db()
    print(sys.argv)
    useutc = args.utc
    pingtest = args.ping
    if (args.name):
        devicename = args.name
    if (args.iterations):
        times_to_take_test = args.iterations
    if (args.test or args.ping or len(sys.argv) == 1) and not args.unixping:
        print("Testing internet speed {} times".format(times_to_take_test))
        for x in range(times_to_take_test):
            r = record_speed_test(sess)
            if (args.verbose or not sys.argv):
                print("Test {amt}: ping={ping}, download={download}, upload={upload}".format(amt=x+1, ping=r.ping, download=r.download, upload=r.upload))
        sess.commit()
        print("Testing done")
    if args.unixping:
        for x in range(times_to_take_test):
            do_unix_ping_test(sess)
        sess.commit()
    if (args.email):
        to_email = args.email
        print("Sending test results to {}".format(to_email))
        send_results_email(sess)
        print("Sending done")

