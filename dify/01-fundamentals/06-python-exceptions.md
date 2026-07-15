# 0.6 Python 异常处理

> 掌握 try/except/raise/finally 与自定义异常。dify 后端有完整的异常体系，是阅读错误处理代码的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练使用 try/except/else/finally 处理异常
- 理解异常继承层次，能看懂 dify 的异常体系
- 掌握自定义异常类
- 能看懂 dify 中所有错误处理代码

## 📚 前置知识

- [00-python-control-flow.md](./05-python-control-flow.md)

## 1. 核心概念

### 1.1 异常的传播：出错就"抛"

Python 中错误不会"忽略"，而是**抛出（raise）异常**。如果没人捕获，程序崩溃并打印 traceback：

```python
int("abc")  # ValueError: invalid literal for int() with base 10: 'abc'
```

### 1.2 异常处理：try / except / else / finally

```python
try:
    # 可能出错的代码
    result = 10 / 0
except ZeroDivisionError as e:
    # 捕获特定异常，as e 获取异常对象
    print(f"除零错误: {e}")
except (TypeError, ValueError) as e:
    # 捕获多种异常（用元组）
    print(f"类型或值错误: {e}")
except Exception as e:
    # 兜底捕获（不推荐滥用）
    print(f"未知错误: {e}")
else:
    # try 块没出错时执行（可选）
    print("操作成功")
finally:
    # 无论是否出错都执行（通常用于清理资源）
    print("清理资源")
```

### 1.3 主动抛出异常：raise

```python
def divide(a, b):
    if b == 0:
        raise ValueError("除数不能为 0")
    return a / b

# 重新抛出当前异常（在 except 块中）
try:
    divide(10, 0)
except ValueError:
    print("记录日志...")
    raise  # 重新抛出，让上层处理
```

### 1.4 异常继承层次

```
BaseException
├── KeyboardInterrupt       # Ctrl+C
├── SystemExit              # sys.exit()
└── Exception               # 大多数异常的基类
    ├── ValueError          # 值不合法
    ├── TypeError           # 类型不匹配
    ├── KeyError            # 字典键不存在
    ├── IndexError          # 列表索引越界
    ├── AttributeError      # 属性不存在
    ├── FileNotFoundError   # 文件不存在
    ├── PermissionError     # 权限不足
    └── ...
```

**关键原则**：
- 捕获**具体异常**而不是宽泛的 `Exception`
- `BaseException` 通常不直接捕获（会吞掉 KeyboardInterrupt）
- dify 大量使用**自定义异常类**继承 `Exception`

### 1.5 自定义异常

```python
class ServiceError(Exception):
    """服务层异常的基类。"""

    def __init__(self, message: str, code: str = "SERVICE_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class AccountNotFoundError(ServiceError):
    """账户不存在。"""

    def __init__(self, account_id: str):
        super().__init__(
            message=f"账户 {account_id} 不存在",
            code="ACCOUNT_NOT_FOUND",
        )
```

## 2. 代码示例

### 2.1 异常链：raise from

`json.loads` 的用法详见 [17-json-processing](./17-json-processing.md)；此处只看异常链。

```python
try:
    data = json.loads(raw_json)
except json.JSONDecodeError as e:
    raise ValueError("配置解析失败") from e
# 显示原始异常 + 新异常的完整链
```

### 2.2 上下文管理器 + 异常

`@contextmanager` / `yield` 的实现细节此处不展开（详见 [11-context-manager](./11-context-manager.md)），只需理解：异常时回滚、无论如何关闭连接。

```python
@contextmanager
def db_transaction():
    conn = connect_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()  # 出错时回滚
        raise  # 重新抛出
    finally:
        conn.close()  # 无论如何关闭连接
```

### 2.3 何时用异常 vs 返回值

```python
# ❌ 用返回值表示错误（不推荐）
def find_user(user_id) -> dict:
    user = db.query(user_id)
    if user is None:
        return {"error": "not found"}
    return {"user": user}

# 调用方需要判断：if "error" in result ...

# ✅ 用异常表示异常情况（Pythonic）
def find_user(user_id) -> User:
    user = db.query(user_id)
    if user is None:
        raise UserNotFoundError(user_id)
    return user

# 调用方正常写：try/except UserNotFoundError
```

## 3. dify 仓库源码解读

### 3.1 dify 的异常体系基类

**文件位置**：`/Users/xu/code/github/dify/api/services/errors.py`
**核心代码**（行 1-40）：

```python
class ServiceError(Exception):
    """服务层异常的基类。"""

    pass


class AccountNotFoundError(ServiceError):
    """账户不存在。"""

    pass


class WorkspaceNotFoundError(ServiceError):
    """工作区不存在。"""

    pass


class ProviderQuotaExceededError(ServiceError):
    """模型供应商配额超限。

    触发此异常时通常需要提示用户升级套餐。
    """

    pass


class ModelCurrentlyNotSupportError(ServiceError):
    """当前模型不支持此功能。"""

    pass
```

**解读**：
- 第 3 行：所有服务异常的**基类**，方便上层统一捕获
- 第 8/12/16/22 行：每种业务异常一个类，命名清晰
- **设计意图**：用异常类型表达"为什么出错"，而不是用错误码字符串
- **优点**：调用方可以精确捕获 `except AccountNotFoundError`，避免误捕其他错误

### 3.2 HTTP 层的异常捕获

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/wraps.py`
**核心代码**（行 30-60）：

```python
import logging
from functools import wraps

from flask import jsonify

from services.errors import (
    AccountNotFoundError,
    ServiceError,
    WorkspaceNotFoundError,
)

logger = logging.getLogger(__name__)


def handle_service_errors(view_func):
    """装饰器：捕获服务层异常并转为 HTTP 响应。"""

    @wraps(view_func)
    def decorated(*args, **kwargs):
        try:
            return view_func(*args, **kwargs)
        except AccountNotFoundError as e:
            logger.warning("账户不存在: %s", e)
            return jsonify({"error": "Account not found"}), 404
        except WorkspaceNotFoundError as e:
            logger.warning("工作区不存在: %s", e)
            return jsonify({"error": "Workspace not found"}), 404
        except ServiceError as e:
            # 其他服务异常的兜底
            logger.error("服务异常: %s", e)
            return jsonify({"error": str(e)}), 500
        except Exception:
            # 未预期的异常
            logger.exception("未处理异常")
            return jsonify({"error": "Internal server error"}), 500

    return decorated
```

**解读**：
- 这是用装饰器统一捕获异常的写法（装饰器原理见 [10-decorator](./10-decorator.md)），本文关注 **try/except 映射 HTTP 状态码**
- 第 23-32 行：把不同异常映射到不同 HTTP 状态码（404 / 500）
- 第 33-35 行：**兜底异常**必须放最后（基类 ServiceError 在具体异常之后）
- 第 36-38 行：`logger.exception()` 自动记录 traceback
- **关键模式**：服务层抛**业务异常**，HTTP 层装饰器**翻译**为 HTTP 响应

### 3.3 数据库操作的异常处理

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**（行 80-110）：

```python
from sqlalchemy.exc import IntegrityError, OperationalError


@contextmanager
def session_scope():
    """事务安全的 session（带异常处理）。"""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except IntegrityError as e:
        # 违反唯一约束、外键约束等
        session.rollback()
        logger.warning("数据完整性错误: %s", e)
        raise
    except OperationalError as e:
        # 数据库连接问题
        session.rollback()
        logger.error("数据库连接失败: %s", e)
        raise
    except Exception:
        session.rollback()
        logger.exception("数据库操作失败")
        raise
    finally:
        session.close()
```

**解读**：
- 第 12-15 行：`IntegrityError` 是 SQLAlchemy 特有异常（唯一键冲突等）
- 第 16-19 行：`OperationalError` 通常是连接断开、超时
- 第 20-22 行：**异常必须重新抛出**，让调用方决定如何处理
- **关键模式**：上下文管理器 = 自动资源清理 + 异常处理

## 4. 关键要点总结

- `try/except/else/finally` 四件套：`else` 在没出错时执行，`finally` 总是执行
- 捕获**具体异常**，不要滥用 `Exception`
- `raise from e` 保留原始异常链
- 自定义异常继承 `Exception`，建立业务异常体系
- dify 风格：服务层抛**业务异常**，HTTP 层**翻译为状态码**
- 读代码时会看到用装饰器统一处理异常；装饰器实现见上文链接的专题

## 5. 练习题

### 练习 1：基础（必做）

写一个 `safe_divide(a, b)` 函数：
- `b == 0` 时抛 `ValueError`
- `a` 不是数字时抛 `TypeError`
- 正常返回 `a / b`

并写测试覆盖三种情况。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/services/errors.py`：
1. dify 的异常基类叫什么？
2. 至少列出 5 个 dify 定义的具体异常类及其含义。

### 练习 3：挑战（选做）

> 学完 [10-decorator](./10-decorator.md) 后再做：实现一个装饰器 `@retry_on_error(max_retries=3, exceptions=(ValueError,))`，在指定异常发生时自动重试指定次数。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/errors.py`
- `/Users/xu/code/github/dify/api/controllers/console/wraps.py`
- `/Users/xu/code/github/dify/api/extensions/ext_database.py`
- Python 官方文档：https://docs.python.org/3/tutorial/errors.html
- PEP 3134（异常链）：https://peps.python.org/pep-3134/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
