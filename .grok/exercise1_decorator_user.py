from functools import wraps

def cache(func):

  @wraps(func)
  def wrapper(*args:Any, **kwargs:Any) -> Any:
    cDict = None
    result = func(*args, **kwargs)

    return result
  return wrapper