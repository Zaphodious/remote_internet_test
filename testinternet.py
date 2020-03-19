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

to_email = "" # Email that the message will be sent to. Set via the -e/--email command line arg
times_to_take_test = 5 # Number of times that the test will be run. Set via the -i/--iterations command line arg
devicename = "nohostnamedetected" # Name of the device that will be reported on the test. Default is the hostname of the machine. Set via the -n/--name command line arg

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
        return f'{{"date":{self.date},"ping":{self.ping},"upload":{self.upload},"download":{self.download}}}'

def make_mbps(bps):
    return round(bps / 1000000, 2)

def record_speed_test(sess):
    try:
        record = None
        st = pyspeedtest.SpeedTest()
        record = TestResult(date=time.time())
        # Adding results seperately, so that if any errors occur we still have results for the previous steps.
        record.ping = round(st.ping(), 2)
        record.download = make_mbps(st.download())
        record.upload = make_mbps(st.upload())
    except:
        print("Speed Test didn't complete")
    finally:
        sess.add(record)
        sess.commit()
        return record

def make_email(subject, body):
    user = os.environ['TESTUSER']
    return f"""\
FROM: {user}
TO: {to_email}
SUBJECT: {subject}

{body}
    """

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
        messagestring += f"| {datetime.datetime.utcfromtimestamp(round(rec.date))} | {rec.ping} | {rec.download} | {rec.upload} | {devicename} |\n"
    return messagestring

def send_results_email(sess):
    try:
        u = sess.query(TestResult).filter(TestResult.sent==False).all()
        sent = send_an_email(f"PTP Speed Results from {datetime.date.today()} from {devicename}", format_results_for_email(u))
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
    parser.add_argument('-e', '--email', help='Email to which to send the unsent results. If no email is provided, results will be cached and sent next time an address is provided.')
    parser.add_argument('-i', '--iterations', type=int, help='Number of times to take the test (default 5)')
    parser.add_argument('-n', '--name', help='Name of the system to use when sending an email (defaults to the hostname of the machine)')
    parser.add_argument('-v', '--verbose', help='Display the speed test results as they are collected (defaults to false, and status messages are printed regardless.', action="store_true")
    args = parser.parse_args()
    sess = init_db()
    print(sys.argv)
    if (args.name):
        devicename = args.name
    if (args.iterations):
        times_to_take_test = args.iterations
    if (args.test or len(sys.argv) == 1):
        print(f"Testing internet speed {times_to_take_test} times")
        for x in range(times_to_take_test):
            r = record_speed_test(sess)
            if (args.verbose or not sys.argv):
                print(f"Test {x+1}: ping={r.ping}, download={r.download}, upload={r.upload}")
        print("Testing done")
    if (args.email):
        to_email = args.email
        print(f"Sending test results to {to_email}")
        send_results_email(sess)
        print("Sending done")

