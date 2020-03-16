#!./env/bin/python3

# Using https://stackabuse.com/how-to-send-emails-with-gmail-using-python/ as guide for sending gmails

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

Base = declarative_base()

devicename = "nohostnamedetected"
try:
    devicename = socket.gethostname()
except:
    pass

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


def init_db():
    engine = create_engine('sqlite:///db.sqlite')
    Base.metadata.create_all(engine)
    DBSession = sessionmaker(bind=engine)
    return DBSession()


def make_email(subject, body):
    user = os.environ['TESTUSER']
    return f"""\
FROM: {user}
TO: {to_email}
SUBJECT: {subject}

{body}
    """

def get_gmail_creds():
    gmail_user = os.environ['TESTUSER']
    gmail_pass = os.environ['TESTPASS']
    return (gmail_user, gmail_pass)

def setup_server():
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        return server
    except Exception as e:
        print('something went wrong')
        return False


def record_speed_test(sess):
    st = None
    record = TestResult(date=time.time())
    try:
        st = pyspeedtest.SpeedTest()
        record.ping = st.ping()
        record.upload = st.upload()
        record.download = st.download()
    except:
        print("Speed Test didn't complete")
    sess.add(record)
    sess.commit()
    return record


def send_an_email(subject, body):
    server = setup_server()
    user, password = get_gmail_creds()
    message = make_email(subject, body)
    try:
        server.login(user, password)
        server.sendmail(user, 'achythlook@microcom.tv', message)
        server.close()
        return True
    except:
        print("whoops")
        return False

def unsents(sess):
    q = sess.query(TestResult).filter(TestResult.sent==False).all()
    return q


def send_results_email(sess):
    q = unsents(sess)
    jsonres = str(q)
    sent = send_an_email(f"PTP Speed Results from {datetime.date.today()} from {devicename}", jsonres)
    if (sent):
        u = unsents(sess)
        for x in u:
            x.sent = True 
        sess.commit()
        print('email sent')
    else:
        print('results not sent today')

times_to_take_test = 5

def run_tests(sess):
    for x in range(times_to_take_test):
        record_speed_test(sess)


def run_tests_and_send():
    sess = init_db()
    run_tests(sess)
    send_results_email(sess)

    


if __name__ == "__main__":
    # run_tests_and_send()
    parser  = argparse.ArgumentParser(description="Tests the internet, stores results and sends out results")
    parser.add_argument('-t', '--test', help='Run a speed test, and store it', action="store_true")
    parser.add_argument('-e', '--email', help='Send all unsent speed tests')
    parser.add_argument('-i', '--iterations', type=int, help='Number of times to take the test (default 5)')
    parser.add_argument('-n', '--name', help='Name of the system to use when sending an email')
    args = parser.parse_args()
    sess = init_db()
    if (args.name):
        devicename = args.name
    if (args.iterations):
        times_to_take_test = args.iterations
    if (args.test):
        print(f"Testing internet speed {times_to_take_test} times")
        run_tests(sess)
        print("Tests are done")
    if (args.email):
        to_email = args.email
        print(f"Sending test results to {to_email}")
        send_results_email(sess)
        print("Email sent")

