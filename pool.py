import os, sys, shlex
import subprocess
import multiprocessing
import argparse
import socket


def parseArgs():
    parser = argparse.ArgumentParser("Pool of workers to run commands")
    parser.add_argument("-i", "--input", type=str, help="File with list of commands")
    parser.add_argument("-n", "--nproc", type=int, default=0, required=False, help="Max number of cores to use. 0 = all")
    parser.add_argument("-m", "--mem", type=int, default=0, required=False, help="Limit RAM usage (in MB). 0 = no limit")
    parser.add_argument("-e", "--exp", type=str, default="cluster", required=False, help="Exp name")
    return parser.parse_args()

def worker(cmd):
    p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    stdout, stderr = p.communicate()
    stdout = stdout.decode("utf-8").strip()
    stderr = stderr.decode("utf-8").strip()
    current = multiprocessing.current_process()

    lock.acquire()
    print("---------start-process----------")
    print(current._identity)
    print("STDOUT:\n")
    print(stdout)
    print("STDERR:\n")
    print(stderr)
    print("---------end-process----------")
    lock.release()
    return stdout

def init(l):
    global lock
    lock = l

if __name__ == "__main__":
    args = parseArgs()

    os.makedirs(".cluster-logs/", exist_ok=True)

    hostname = socket.gethostname()
    sys.stdout = open(f'.cluster-logs/{hostname}-{args.exp}.log', 'w')

    with open(args.input, "r") as f:
        lines = f.readlines()
    
    nproc = os.cpu_count()
    if args.nproc > 0:
        nproc = args.nproc

    MemLmt = args.mem
    m = multiprocessing.Manager()
    l = m.Lock()

    cmds = []
    for line in lines:
        cmds.append(line.strip().replace("\n",""))


    pool = multiprocessing.Pool(nproc, initializer=init, initargs=(l,))
    pool.map(worker, cmds)
    pool.close()
    pool.join()