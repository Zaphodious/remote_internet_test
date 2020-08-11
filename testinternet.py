#!./env/bin/python3

import smtplib
import pyspeedtest
from sqlalchemy import create_engine, Column, ForeignKey, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import null
import time
import datetime
import os
import os.path as path
import argparse
import socket
import sys
import subprocess
import re
import contextlib
from urllib.request import urlopen
from io import StringIO

from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from paramiko import SSHClient
from paramiko.client import AutoAddPolicy
from scp import SCPClient

to_email = "" # Email that the message will be sent to. Set via the -e/--email command line arg
times_to_take_test = 5 # Number of times that the test will be run. Set via the -i/--iterations command line arg
devicename = "nohostnamedetected" # Name of the device that will be reported on the test. Default is the hostname of the machine. Set via the -n/--name command line arg
useutc = False # If true, uses utc time when sending the email. If false, uses the timezone of the server. set via -u/--utc
pingtest = False
uptest = ''
scp_host = ""
scp_dir = ""

try:
    devicename = socket.gethostname()
except:
    pass

def get_creds(thetype):
    username = os.environ['{thetype}USER'.format(thetype=thetype)]
    password = os.environ['{thetype}PASS'.format(thetype=thetype)]
    return (username, password)

def get_gmail_creds():
    return get_creds('TEST')

def get_ssh_creds():
    return get_creds('SSH')

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
        if uptest:
            ping_response = subprocess.Popen(["ping", "-c 1", "-W 100", "www.google.com"], stdout=subprocess.PIPE).stdout.read()
            timeres_str = upingreg.findall(ping_response.decode('UTF-8'))[0].replace('time=', '')
            timeres = float(timeres_str)
            record.ping = timeres
        else:
            record.ping = round(st.ping(), 2)
        if (pingtest):
            record.download = null()
            record.upload = null()
        else:
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
        ping_response = subprocess.Popen(["ping", "-c 1", "-W 100", uptest], stdout=subprocess.PIPE).stdout.read()
        timeres_str = upingreg.findall(ping_response.decode('UTF-8'))[0].replace('time=', '')
        timeres = float(timeres_str)
        record.ping = timeres
    except Exception as e:
        print("Speed Test didn't complete")
    finally:
        sess.add(record)
        # sess.commit()
        return record


COMMASPACE = ', '


def send_an_email(subject, body, attachment_string=None):
    user, password = get_gmail_creds() # Do this first, so that we fail fast if this isn't set
    msg = MIMEMultipart()
    msg['Subject'] = subject
    # me == the sender's email address
    # family = the list of all recipients' email addresses
    msg['From'] = user
    msg['To'] = to_email

    if attachment_string:
        part = MIMEText(attachment_string, "csv")
        # encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename='data_{subject}.csv'.format(subject=subject))
        msg.attach(part)
    
    part = MIMEText(body)
    msg.attach(part)

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.ehlo()
    server.login(user, password)
    print(msg.as_string())
    server.sendmail(user, to_email, msg.as_string())
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

def get_public_ip():
    with urlopen('https://api.ipify.org') as r:
        ip = r.read()
        ip = ip.decode("utf-8") 
        return ip

def get_internal_ip():
    return socket.gethostbyname(socket.gethostname())

def make_email_body(q):
    l = len(q)
    pubip = get_public_ip()
    prvip = get_internal_ip()
    emailbody = """Results from {machinename}. Public IP {publicip}, Internal IP {internalip}. Please see the attached CSV file.""".format(machinename=devicename, publicip=pubip,internalip=prvip)
    return emailbody


def make_csv(q):
    messagestring = """pk,date,devicename,upload,download,ping\n"""
    for rec in q:
        dt = ""
        if (useutc):
            dt = datetime.datetime.utcfromtimestamp(rec.date)
        else:
            dt = datetime.datetime.fromtimestamp(rec.date).strftime('%Y-%m-%d %H:%M:%S %z')
        messagestring += ",{date},{devicename},{upload},{download},{ping}\n".format(
            date=dt,
            devicename=devicename,
            upload=rec.upload,
            download=rec.download,
            ping=rec.ping
        )
    return messagestring

def send_results_email(sess):
    try:
        u = sess.query(TestResult).filter(TestResult.sent==False).all()
        send_an_email(
        "Speed Test Results from {today} from {devicename}".format(devicename=devicename, today=datetime.date.today()),
        make_email_body(u),
        make_csv(u)
        )
        mark_all_as_sent(sess)
    except Exception as e:
        print('results not sent today')
        print(e)

def mark_all_as_sent(sess):
    try:
        u = sess.query(TestResult).filter(TestResult.sent==False).all()
        for x in u:
            x.sent = True 
        sess.commit()
    except Exception as e:
        print('Could not clear records')
        print(e)


@contextlib.contextmanager
def scp_connection(*args, **kwargs):
    """Uses the SCP library to create an SCP connection. Same param as paramiko.SSHClient.connect()"""
    sshuser, sshpass = get_ssh_creds()
    client = SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(AutoAddPolicy)
    client.connect(*args,**kwargs)
    scpclient = SCPClient(client.get_transport())
    with scpclient as s:
        yield scpclient
    
def timenow():
    return datetime.datetime.utcfromtimestamp(time.time())

def upload_dir():
    return scp_dir # path.join(scp_dir, devicename)

def upload_name():
    return "{time}_FROM_{devicename}.csv".format(devicename=devicename,time=timenow())

def upload_path():
    return path.join(upload_dir(), upload_name())

def make_log_string():
    return "upload from {pubip}/{prvip} at {timeat}".format(pubip=get_public_ip(), prvip=get_internal_ip(), timeat=timenow())

def log_path():
    return path.join(upload_dir(), "log_{time}_{devicename}.log".format(time=timenow(), devicename=devicename))

def upload_via_scp(conn):
    u,p = get_ssh_creds()
    try:
        res = sess.query(TestResult).filter(TestResult.sent==False).all()
        with scp_connection(scp_host, username=u, password=p) as c:
            print(c)
            print(upload_dir())
            print(upload_name())
            print(upload_path())
            csv = make_csv(res)
            csv_file = StringIO(csv)
            log_file = StringIO(make_log_string())
            c.putfo(csv_file, upload_path())
            c.putfo(log_file, log_path())
            mark_all_as_sent(sess)
            pass
    except Exception as e:
        print('results not dumped today')
        print(e)
        raise e
    print(scp_host)
    print(scp_dir)

def init_db():
    engine = create_engine('sqlite:///db.sqlite')
    Base.metadata.create_all(engine)
    DBSession = sessionmaker(bind=engine)
    return DBSession()

if __name__ == "__main__":
    parser  = argparse.ArgumentParser(description=' Tests the internet, stores results and sends out results. The environment variables "TESTUSER" and "TESTPASS" must be set to the email and password of the gmail account that will be used to send reesults. If no arguments are supplied, the script is ran as ./script -t -a')
    parser.add_argument('-t', '--test', help='Run a speed test, and store it', action="store_true")
    parser.add_argument('-p', '--ping', help='Run a ping test, and store it. -t/--test is ignored when using this command. Up/Down speed is recorded as NULL for this test.', action="store_true")
    parser.add_argument('-up', '--unixping', help='Domain to ping, using the system ping command. Does not work on Windows', type=str)
    parser.add_argument('-e', '--email', help='Email to which to send the unsent results. If no email is provided, results will be cached and sent next time an address is provided.')
    parser.add_argument('-i', '--iterations', type=int, help='Number of times to take the test (default 5)')
    parser.add_argument('-n', '--name', help='Name of the system to use when sending an email (defaults to the hostname of the machine)')
    parser.add_argument('-v', '--verbose', help='Display the speed test results as they are collected (defaults to false, and status messages are printed regardless.', action="store_true")
    parser.add_argument('-u', '--utc', help='Sends the results with utc time. Default is to use the timezone of the host machine', action="store_true")
    parser.add_argument('-s', '--scphost', help='Uploads the results to a location over SSH', type=str)
    parser.add_argument('-d', '--directory', help='The path of directory on the SCP host machine in which to put the report file and logs', type=str)
    args = parser.parse_args()
    sess = init_db()
    print(sys.argv)
    useutc = args.utc
    pingtest = args.ping
    uptest = args.unixping
    if (args.name):
        devicename = args.name
    if (args.iterations):
        times_to_take_test = args.iterations
    if (args.test or args.ping or args.unixping or len(sys.argv) == 1):
        print("Testing internet speed {} times".format(times_to_take_test))
        for x in range(times_to_take_test):
            r = record_speed_test(sess)
            if (args.verbose or not sys.argv):
                print("Test {amt}: ping={ping}, download={download}, upload={upload}".format(amt=x+1, ping=r.ping, download=r.download, upload=r.upload))
        sess.commit()
        print("Testing done")
    if (args.scphost and args.directory):
        scp_host = args.scphost
        scp_dir = args.directory
        upload_via_scp(sess)
        
    if (args.email):
        to_email = args.email
        print("Sending test results to {}".format(to_email))
        send_results_email(sess)
        print("Sending done")

