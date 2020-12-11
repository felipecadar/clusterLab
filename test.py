from multiprocessing import Pool
import time

def f(x):
    time.sleep(x)
    return x*x

class TestClass:

    def p1(self):
        print("p1")

    @command
    def p2(self):
        print("p2")

if __name__ == '__main__':
    # with Pool(5) as p:
    #     print(p.map(f, [1, 2, 3]))

    c = TestClass()


