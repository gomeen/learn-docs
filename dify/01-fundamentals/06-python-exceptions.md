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

`json.loads` 的用法详见 [17-json-processing](./20-json-processing.md)；此处只看异常链。

```python
try:
    data = json.loads(raw_json)
except json.JSONDecodeError as e:
    raise ValueError("配置解析失败") from e
# 显示原始异常 + 新异常的完整链
```

### 2.2 上下文管理器 + 异常

`@contextmanager` / `yield` 的实现细节此处不展开（详见 [11-context-manager](./12-context-manager.md)），只需理解：异常时回滚、无论如何关闭连接。

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

## 3. 关键要点总结

- `try/except/else/finally` 四件套：`else` 在没出错时执行，`finally` 总是执行
- 捕获**具体异常**，不要滥用 `Exception`
- `raise from e` 保留原始异常链
- 自定义异常继承 `Exception`，建立业务异常体系
- dify 风格：服务层抛**业务异常**，HTTP 层**翻译为状态码**
- 读代码时会看到用装饰器统一处理异常；装饰器实现见上文链接的专题

---

**文档版本**：v1.0
**最后更新**：2026-07-13
