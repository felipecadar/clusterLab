import os
import sys
import subprocess
import multiprocessing
import threading

try:
    import yaml
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    import yaml
    from yaml import Loader, Dumper


import argparse
import pathlib
import shlex
import uuid
import inspect
from colorama import init
from colorama import Fore, Back, Style
from datetime import datetime

import logging
logging.basicConfig(filename='clab.log', format='%(asctime)s --> %(message)s ',datefmt='%d/%m/%Y %I:%M:%S %p',  filemode='w', level=logging.DEBUG)


init(autoreset=True)

def sendCmd(cmd, wait=True):
    p = subprocess.Popen(shlex.split(
        cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if wait:
        p.wait()

        stdout, stderr = p.communicate()
        stdout = stdout.decode("utf-8").strip()
        stderr = stderr.decode("utf-8").strip()

        return stdout, stderr
    
    else:
        return None, None

def sendToHost(user, host, ssh_key, cmd, domain=""):
    if len(domain) > 0:
        dot = "."
    else:
        dot = ""

    cmd = 'ssh {}{}{} {} '.format(host, dot, domain, cmd)
    # print(cmd)
    stdout, stderr = sendCmd(cmd)
    return stdout, stderr

def checkStatus(user, host, ssh_key, domain="", timeout=1):
    secret = str(uuid.uuid4())
    if len(domain) > 0:
        dot = "."
    else:
        dot = ""

    # cmd = 'ssh {user}"@"{host}"."{domain} -i {ssh_key} -o ConnectTimeout={timeout} echo \'{secret}\''
    # cmd = 'ssh {}"@"{}{}{} -i {} -o ConnectTimeout={} echo \'{}\''.format(user, host, dot, domain, ssh_key, timeout, secret)
    cmd = 'ssh {}"@"{}{}{} -o ConnectTimeout={} echo \'{}\''.format(user, host, dot, domain, timeout, secret)
    stdout, stderr = sendCmd(cmd)

    status = True if secret in stdout else False
    return status

def chunkIt(seq, num):
    out = [ [] for _ in range(num)]
    for i, el in enumerate(seq):
        out[i%num].append(el)
    return out

def methodsWithDecorator(cls, decoratorName):
    sourcelines = inspect.getsourcelines(cls)[0]
    for i,line in enumerate(sourcelines):
        line = line.strip()
        if line.split('(')[0].strip() == '@'+decoratorName: # leaving a bit out
            nextLine = sourcelines[i+1]
            name = nextLine.split('def')[1].split('(')[0].strip()
            yield(name)

def command_dec(func):
    return func

def resetTerminal():
    print(chr(27) + "[2J")
    print("\033[0;0H")