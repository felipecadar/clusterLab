import os
import sys
import subprocess
import multiprocessing
import yaml
import argparse
import urwid
import pathlib
import shlex
import uuid
import inspect
from colorama import init
from colorama import Fore, Back, Style
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

def checkStatus(self, host,ssh_key, domain="", timeout=1):
    secret = str(uuid.uuid4())

    cmd = f'ssh -i {ssh_key} {host}{domain} -o ConnectTimeout={timeout} echo \'{secret}\''
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

class Monitor:


    def __init__(self, config, args):
        self.config = config
        self.args = args

        self.mainLoop()

    def mainLoop(self):

        # Set up color scheme
        palette = [
            ('background', '', 'black'),
            ('titlebar', 'dark red', ''),
            ('refresh button', 'dark green,bold', ''),
            ('quit button', 'dark red', ''),
            ('headers', 'white,bold', ''),
            ('green ', 'light green', 'black'),
            ('yellow ', 'yellow', 'black'),
            ('red', 'light red', 'black')]

        header_text = urwid.Text(u' ClusterLab Monitor')
        header = urwid.AttrMap(header_text, 'titlebar')

        # Create the menu
        menu = urwid.Text([
            u'Press (', ('refresh button', u'R'), u') to manually refresh. ',
            u'Press (', ('quit button', u'Q'), u') to quit.'
        ])

        # Create the quotes box
        table_text = urwid.Text(u'Press (R) to init!')
        table_filler = urwid.Filler(table_text, valign='top', top=1, bottom=1)
        v_padding = urwid.Padding(table_filler, left=1, right=1)
        table_box = urwid.LineBox(v_padding)

        # Assemble the widgets
        layout = urwid.Frame(header=header, body=table_box, footer=menu)

        txt = urwid.Text(f"Hello World {len(palette)}")
        fill = urwid.Filler(txt, 'top')
        
        loop = urwid.MainLoop(fill)
        loop.run()

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
            sendCmd(cmd)
            print(cmd)


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
            ssh_key = self.config['hosts'][host]['ssh_key'] if self.config['hosts'][host]['ssh_key'] else self.config['global']['ssh_key']
            stat = self.checkStatus(host, ssh_key, domain)

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
    

