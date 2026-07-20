from functools import wraps
from typing import Any


def cache(func):
    store: dict[tuple[tuple[Any, ...], tuple[tuple[str, Any], ...]], Any] = {}

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        key = (args, tuple(sorted(kwargs.items())))
        if key not in store:
            store[key] = func(*args, **kwargs)
        return store[key]

    return wrapper


call_count = 0


@cache
def add(x: int, y: int) -> int:
    global call_count
    call_count += 1
    return x + y


assert add(1, 2) == 3
assert add(1, 2) == 3
assert call_count == 1

assert add(2, 3) == 5
assert call_count == 2

assert add.__name__ == "add"

print("all checks passed")