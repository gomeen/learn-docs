import time
from contextlib import contextmanager


@contextmanager
def timer():
    start = time.perf_counter()
    print("开始")
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        print(f"耗时 {elapsed:.4f} 秒")


with timer():
    time.sleep(0.2)

print("done")