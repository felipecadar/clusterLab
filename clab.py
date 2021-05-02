from src.util import *
from src.monitor import Monitor
from src.dispatcher import Dispatcher

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
        self.dispatcher.dispatchMaster()

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
    

