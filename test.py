from multiprocessing import Pool
import time

def f(x):
    time.sleep(x)
    return x*x

if __name__ == '__main__':
    with Pool(5) as p:
        print(p.map(f, [1, 2, 3]))