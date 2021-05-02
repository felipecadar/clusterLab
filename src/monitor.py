from src.util import *

class Monitor:


    def __init__(self, config, args):
        self.config = config
        self.args = args
        self.tsize = os.popen('stty size', 'r').read().split()

        self.host_status = {host:False for host in self.config['hosts']}
        self.running_status = {host:False for host in self.config['hosts']}

        self.checkLoop()
        self.tmuxLoop()
        
        self.status()


    def checkLoop(self):
        
        for host in self.config['hosts']:
            domain = self.config['global']['domain'] if self.config['global']['domain'] else ''
            ssh_key = self.config['global']['ssh_key']
            user = self.config['global']['user']
            stat = checkStatus(user, host, ssh_key, domain)
            self.host_status[host] = stat

        threading.Timer(3.0, self.checkLoop).start()


    def tmuxLoop(self):
        
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
