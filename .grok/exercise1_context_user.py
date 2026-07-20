from contextlib import contextmanager

@contextmanager
def timer() -> Any:

  try:
    print("开始")
    yield
  finally:
    print("耗时")