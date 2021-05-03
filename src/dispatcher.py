from src.util import *
from threading import Thread
from time import sleep

from queue import Queue, Empty

import logging
# logging.basicConfig(filename='clab.log', format='%(asctime)s %(message)s --> ',datefmt='%d/%m/%Y %I:%M:%S %p',  filemode='w', level=logging.DEBUG)

def MonitoringThread(in_queue, valid_hosts):
    init = datetime.now()
    init_time = init.strftime("%H:%M:%S")
    while True:
        if in_queue.empty():
            break

        resetTerminal()
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")

        print("Running Comands from " + init_time + " to "  + current_time)
        print("Used Hosts: "+ ",".join(valid_hosts))
        print("Comands in Queues: {}".format(in_queue.qsize()))
        sleep(1)

    print(Fore.GREEN + "Done")


def Master(config, host, in_queue, kill_queue):
    out_queue = Queue()
    cores = config['hosts'][host]['cores']
    cores_thread = []

    for i in range(cores):
        th = Thread(target=coreThread, args=(i, out_queue, kill_queue, config, host))
        th.start()
        cores_thread.append(th)

    while True:


        if out_queue.empty():
            try:
                cmd = in_queue.get(timeout=1)
                out_queue.put(cmd)
            except Empty:

                if in_queue.empty():
                    kill_queue.put(1)
                    for th in cores_thread:
                        th.join()
                    logging.debug("END subthreads {}".format(host))
                    break

    logging.debug("END Master {}".format(host))


def coreThread(th_id, in_queue, kill_queue, config, host):
    while True:
        if in_queue.empty():
            if not kill_queue.empty():
                logging.debug("[{}]-{:02d} | KILL".format(host, th_id))
                break
        else:
            try:
                cmd = in_queue.get(timeout=1)
            except:
                if not kill_queue.empty():
                    logging.debug("[{}]-{:02d} | KILL".format(host, th_id))
                    break
                else:
                    continue
            
            logging.debug("[{}]-{:02d} | Running CMD: {}".format(host, th_id, cmd))
            
            sendToHost(config['global']['user'], host, config['global']['ssh_key'], cmd, config['global']['domain'])
            


class Dispatcher:
    def __init__(self, config, args, valid_hosts):
        self.config = config
        self.args = args
        self.valid_hosts = valid_hosts
        self.master_threads = {}
        self.kill_queue = Queue()
        self.all_cmds = self.genCmds()

    def dispatchMaster(self):
        in_queue = Queue()
        host_queues = {}

        for cmd in self.all_cmds:
            in_queue.put(cmd)

        M_th = Thread(target=MonitoringThread, args=(in_queue,self.valid_hosts))
        M_th.start()
        
        for host in self.valid_hosts:
            th = Thread(target=Master, args=(self.config, host, in_queue, self.kill_queue))
            th.start()

            host_queues[host] = th

        pass


    def genCmds(self):
        all_cmds = []
        with open(self.args.input, "r") as f:
            for line in f.readlines():
                all_cmds.append(line.strip().replace("\n",""))
    
        return all_cmds

class Args:
    pass

if __name__ == "__main__":
    config = yaml.load(open("config.yaml", 'r'), Loader=yaml.CLoader)
    args = Args()
    args.input = "testargs.txt"

    D = Dispatcher(config=config, args=args, valid_hosts=list(config['hosts'].keys()))
    D.dispatchMaster()