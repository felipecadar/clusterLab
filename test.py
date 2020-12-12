import time

def f(x):
    begin = time.time()
    now = time.time()
    while now - begin < 10:
        now = time.time()
        x*x


if __name__ == "__main__":
    print("AAAAAAAa")
    f(10)