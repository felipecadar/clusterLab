import os
import sys
import subprocess
import multiprocessing
import yaml
import argparse
# import urwid
import shlex
import uuid
import inspect
from colorama import init
from colorama import Fore, Back, Style
init(autoreset=True)


def methodsWithDecorator(cls, decoratorName):
    sourcelines = inspect.getsourcelines(cls)[0]
    for i,line in enumerate(sourcelines):
        line = line.strip()
        if line.split('(')[0].strip() == '@'+decoratorName: # leaving a bit out
            nextLine = sourcelines[i+1]
            name = nextLine.split('def')[1].split('(')[0].strip()
            yield(name)


def command_dec(func):
    def wrapper(func):
        pass
    return wrapper

class ClusterLab:
    def __init__(self, validate_hosts=True):
        self.commands = list(methodsWithDecorator(ClusterLab, "command_dec"))
        args, parser = self.mainParser()  
        
        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

    @command_dec
    def dispatch(self):
        self.config = yaml.load(open(args.config, 'r'), Loader=yaml.CLoader)
        self.valid_hosts = [host for host in self.config['hosts']]
        if validate_hosts:
            self.valid_hosts = self.validateHosts()

        self.total_procs = sum(self.config['hosts'][host]['cores'] for host in self.valid_hosts)
        print(f'Available cores: {total_procs}')

    def dispatchParser(self):
        parser.add_argument("-i", "--input", type=str,
                            help="File with list of commands")
        parser.add_argument("-c", "--config", type=str, default="config.yaml",
                            required=False, help="config file with hosts")
        parser.add_argument("-e", "--exp", type=str,
                            default="cluster", required=False, help="Exp name")


    def mainParser(self):
        parser = argparse.ArgumentParser(description="Simple Cluster with Python!")
        parser.add_argument("command", help="Subcommand to run", choices=self.commands)
        args = parser.parse_args(sys.argv[1:2])
        return args, parser

    def sendCmd(self, cmd, wait=True):
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

    def checkStatus(self, host, timeout=1):
        domain = self.config['global']['domain'] if self.config['global']['domain'] else ''
        ssh_key = self.config['hosts'][host]['ssh_key'] if self.config['hosts'][host]['ssh_key'] else self.config['global']['ssh_key']
        secret = str(uuid.uuid4())

        cmd = f'ssh -i {ssh_key} {host}{domain} -o ConnectTimeout={timeout} echo \'{secret}\''
        stdout, stderr = sendCmd(cmd)

        status = True if secret in stdout else False
        return status

    def validateHosts(self):
        valid_hosts = []
        for host in self.config['hosts']:
            print(f'Checking {host:<15}...', end='')
            stat = self.checkStatus(host)
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
    

