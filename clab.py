import os
import sys
import subprocess
import multiprocessing
import threading
import yaml
import argparse
import pathlib
import shlex
import uuid
import inspect
from colorama import init
from colorama import Fore, Back, Style
from datetime import datetime
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

    cmd = f'ssh {host}{dot}{domain} {cmd} '
    stdout, stderr = sendCmd(cmd)
    return stdout, stderr

def checkStatus(user, host, ssh_key, domain="", timeout=1):
    secret = str(uuid.uuid4())

    cmd = f'ssh {user}"@"{host}"."{domain} -i {ssh_key} -o ConnectTimeout={timeout} echo \'{secret}\''
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

class Monitor:


    def __init__(self, config, args):
        self.config = config
        self.args = args
        self.tsize = os.popen('stty size', 'r').read().split()

        self.host_status = {host:False for host in self.config['hosts']}
        self.checkLoop()
        self.status()


    def checkLoop(self):
        
        for host in self.config['hosts']:
            domain = self.config['global']['domain'] if self.config['global']['domain'] else ''
            ssh_key = self.config['global']['ssh_key']
            user = self.config['global']['user']
            stat = checkStatus(user, host, ssh_key, domain)
            self.host_status[host] = stat

        threading.Timer(3.0, self.checkLoop).start()

    def status(self):

        resetTerminal()
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")

        print("Monitoring Hosts -- " + current_time)
        for host in self.host_status:
            print("{:<20}".format(host), end="")

            if self.host_status[host]:
                print(Fore.GREEN + "[ONLINE]")
            else:
                print(Fore.RED + "[OFLINE]")

        threading.Timer(1.0, self.status).start()

    def checkSession(self):

        for host in self.host_status:
            
            domain = self.config['global']['domain'] if self.config['global']['domain'] else ''
            ssh_key = self.config['global']['ssh_key']
            user = self.config['global']['user']

            cmd = "tmux ls".format(host+SUF)
            stdout, stderr  = sendToHost(user, host, ssh_key, cmd, domain)
            print(stdout)


    def mainLoop(self):
        threading.Timer(1.0, self.mainLoop).start()
        print(chr(27) + "[2J")
        print("\033[0;0H")
        print(self.host_status)
        print(self.tsize)


class Dispatcher:
    def __init__(self, config, args, valid_hosts):
        self.config = config
        self.args = args
        self.valid_hosts = valid_hosts
        self.total_procs = sum(self.config['hosts'][host]['cores'] for host in self.valid_hosts)

    def genCmds(self):
        all_cmds = []
        with open(self.args.input, "r") as f:
            for line in f.readlines():
                all_cmds.append(line.strip().replace("\n",""))
    
        cmd_p_proc = chunkIt(all_cmds, self.total_procs) 

        os.makedirs(f'.cluster-tmp/{self.args.exp}', exist_ok=True)
        host_files = {}
        i = 0
        for host in self.valid_hosts:
            fname = f'.cluster-tmp/{self.args.exp}/{host}.cmdlist'
            fname = os.path.abspath(fname)
            with open(fname, 'w') as f:
                for proc in range(self.config['hosts'][host]['cores']):
                    f.write("\n".join(cmd_p_proc[i]) + "\n")
                    i += 1


            host_files[host] = fname
        return host_files

    def send(self, host_files):
        this_dir = str(pathlib.Path(__file__).parent.absolute())
        for host in host_files:
            cmd = f'tmux new-session -d -s clab@{host.replace(".", "-")}#{self.args.exp} python3 {this_dir}/pool.py -i {host_files[host]} -n {self.config["hosts"][host]["cores"]} -e {self.args.exp}'
            print(f'Sending cmd to {host}')

            domain = self.config['global']['domain'] if self.config['global']['domain'] else ''
            ssh_key = self.config['global']['ssh_key']
            user = self.config['global']['user']

            stdout, stderr  = sendToHost(user, host, ssh_key, cmd, domain)

            print(stdout)
            print(stderr)


class ClusterLab:
    def __init__(self, check_hosts=True):
        self.commands = list(methodsWithDecorator(ClusterLab, "command_dec"))
        args, parser = self.mainParser()  
        self.check_hosts = check_hosts
        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

    @command_dec
    def dispatch(self):
        self.dispatch_args = self.dispatchParser()
        self.config = yaml.load(open(self.dispatch_args.config, 'r'), Loader=yaml.CLoader)
        self.valid_hosts = [host for host in self.config['hosts']]
        if self.check_hosts:
            self.valid_hosts = self.validateHosts()
        
        if len(self.valid_hosts) == 0:
            print("No valid hosts found")
            exit()

        self.dispatcher = Dispatcher(self.config, self.dispatch_args, self.valid_hosts)
        host_files = self.dispatcher.genCmds()
        self.dispatcher.send(host_files)

    @command_dec
    def monitor(self):
        self.monitor_args = self.monitorParser()
        self.config = yaml.load(open(self.monitor_args.config, 'r'), Loader=yaml.CLoader)
        self.monitor = Monitor(self.config, self.monitor_args)

    def monitorParser(self):
        parser = argparse.ArgumentParser(description="Monitor cluster", usage="clab.py monitor [-h] [-c CONFIG] [-e EXP]")
        parser.add_argument("-c", "--config", type=str, default="config.yaml", required=False, help="config file with hosts")
        parser.add_argument("-e", "--exp", type=str,
                            default="cluster1", required=False, help="Exp name")
        return parser.parse_args(sys.argv[2:])

    def dispatchParser(self):
        parser = argparse.ArgumentParser(description="Send tasks to cluster", usage="clab.py dispatch [-h] -i INPUT [-c CONFIG] [-e EXP]")
        parser.add_argument("-i", "--input", type=str,
                            help="File with list of commands", required=True)
        parser.add_argument("-c", "--config", type=str, default="config.yaml",
                            required=False, help="config file with hosts")
        parser.add_argument("-e", "--exp", type=str,
                            default="cluster1", required=False, help="Exp name")
        return parser.parse_args(sys.argv[2:])

    def mainParser(self):
        parser = argparse.ArgumentParser(description="Simple Cluster with Python!")
        parser.add_argument("command", help="Subcommand to run", choices=self.commands)
        args = parser.parse_args(sys.argv[1:2])
        return args, parser





    def validateHosts(self):
        valid_hosts = []
        for host in self.config['hosts']:
            print(f'Checking {host:<15}...', end='')

            domain = self.config['global']['domain'] if self.config['global']['domain'] else ''
            ssh_key = self.config['global']['ssh_key']
            user = self.config['global']['user']
            stat = checkStatus(user, host, ssh_key, domain)

            if stat:
                print(Fore.GREEN + "[ONLINE]")
                valid_hosts.append(host)
            else:
                print(Fore.RED + "[OFFLINE]")
        return valid_hosts

    def getCoresCount(self):
        pass

if __name__ == "__main__":
    clab = ClusterLab()
    

