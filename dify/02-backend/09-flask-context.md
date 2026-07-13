# 2.2.2 Flask 上下文机制：`g` / `request` / `session` / `current_app`

> 理解 Flask 的四种上下文对象，能在 dify 中正确使用 request-scoped 数据。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Flask 的四种上下文对象（`g`、`request`、`session`、`current_app`）
- 理解应用上下文（App Context）和请求上下文（Request Context）的区别
- 在 dify 中找到 `g`、`current_user` 等上下文对象的使用
- 避免上下文相关的常见错误（Working Outside Application Context）

## 📚 前置知识

- 02-backend/08-flask-basics.md（Flask 基础）
- Python 线程局部变量基础（threading.local）

## 1. 核心概念

### 1.1 Flask 的两个上下文

Flask 在每个请求中维护两个**栈结构**的上下文：

```
Application Context（应用上下文）
├── current_app: 当前 Flask 应用实例
└── g: 请求级的临时存储（request-scoped globals）

Request Context（请求上下文）
├── request: 当前请求对象
└── session: 用户会话（跨请求持久化）
```

**类比**：
- `current_app` ≈ 全局单例的 application 引用
- `g` ≈ 当前请求的"暂存箱"（请求结束后清空）
- `request` ≈ 当前 HTTP 请求的所有信息
- `session` ≈ Cookie 加密的跨请求存储

### 1.2 应用上下文 vs 请求上下文

| 上下文 | 何时激活 | 何时销毁 | 主要对象 |
|--------|---------|---------|---------|
| 应用上下文 | 应用启动 / `app_context()` | 应用关闭 | `current_app`、`g` |
| 请求上下文 | 收到请求 | 请求结束 | `request`、`session` |

**关键约束**：
- 在没有请求时（如 CLI 命令、Celery 任务）访问 `request` 会报 `RuntimeError`
- 必须用 `with app.app_context():` 或 `with app.test_request_context():` 手动激活

### 1.3 dify 的特殊使用

dify 通过 Flask 上下文传递：
- `g`：存储当前用户、租户、trace_id 等
- `current_user`：通过 `flask-login` 的 `current_user` proxy
- `current_account_with_tenant()`：dify 自定义的 helper，从 `g` 取出账号和租户

## 2. 代码示例

### 2.1 `g` 对象：请求级暂存

```python
from flask import g, request

@app.before_request
def load_user():
    """每个请求前把用户加载到 g"""
    user_id = request.headers.get("X-User-Id")
    if user_id:
        g.current_user = User.query.get(user_id)
        g.tenant_id = g.current_user.tenant_id
    else:
        g.current_user = None

@app.route("/profile")
def profile():
    # 直接从 g 取，不需要每次都查数据库
    if g.current_user is None:
        return {"error": "Unauthorized"}, 401
    return {"name": g.current_user.name}
```

### 2.2 `session`：跨请求持久化

```python
from flask import session

app.secret_key = "your-secret-key"  # 必须设置才能用 session

@app.route("/login", methods=["POST"])
def login():
    username = request.json["username"]
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(request.json["password"]):
        session["user_id"] = user.id  # 加密存到 Cookie
        return {"status": "ok"}
    return {"error": "Invalid credentials"}, 401

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return {"status": "logged out"}
```

### 2.3 `current_app`：访问应用配置

```python
from flask import current_app

def send_email(to: str, subject: str, body: str):
    # 在任何地方都能访问应用配置
    smtp_host = current_app.config["SMTP_HOST"]
    smtp_port = current_app.config["SMTP_PORT"]
    # ... 发送邮件
```

### 2.4 常见错误：Working Outside Application Context

```python
# ❌ 错误：在没有应用上下文时访问 current_app
def background_task():
    db_url = current_app.config["DATABASE_URL"]  # RuntimeError!

# ✅ 正确 1：在 Flask 请求中访问（自动有上下文）
@app.route("/task")
def task():
    db_url = current_app.config["DATABASE_URL"]  # OK

# ✅ 正确 2：在 CLI/Celery 中手动推入上下文
def background_task():
    with app.app_context():
        db_url = current_app.config["DATABASE_URL"]  # OK

# ✅ 正确 3：在测试中用 test_request_context
def test_route():
    with app.test_request_context("/"):
        db_url = current_app.config["DATABASE_URL"]  # OK
```

### 2.5 常见错误：在 g 中存可变对象

```python
# ❌ 错误：跨请求共享可变对象
g.user_cache = {}  # 这是请求级的，OK

# 但如果存到 current_app，全局共享
current_app.user_cache = {}  # 多个请求共享，可能竞态

# ✅ 正确：g 用于请求级共享，current_app 用于只读配置
```

## 3. dify 仓库源码解读

### 3.1 上下文初始化：`before_request`

**文件位置**：`/Users/xu/code/github/dify/api/app_factory.py`
**核心代码**（行 59-65）：

```python
@dify_app.before_request
def before_request():
    # Initialize logging context for this request
    init_request_context()
    RecyclableContextVar.increment_thread_recycles()
```

**解读**：
- 第 2 行：`init_request_context()` 把 trace_id、user_id 等存入 `g` 或 ContextVar
- 第 3 行：`increment_thread_recycles()` 用于线程回收计数（gevent 兼容）

### 3.2 自定义上下文 helper：`current_account_with_tenant`

**文件位置**：`/Users/xu/code/github/dify/api/libs/login.py`
**核心代码**（行 1-50）：

```python
from flask import g, current_app
from flask_login import current_user


def current_account_with_tenant() -> tuple[Account | None, str | None]:
    """返回当前请求的 (Account, tenant_id)。

    这是 dify 中最常用的上下文 helper：
    - 优先从 flask_login 的 current_user 拿（已登录）
    - 否则从 g.account 拿（API key 等场景）
    - tenant_id 始终从 g.current_tenant_id 拿
    """
    user = None
    if hasattr(g, "account") and g.account:
        user = g.account
    elif current_user and not current_user.is_anonymous:
        user = current_user
    elif hasattr(g, "login_user"):
        user = g.login_user

    tenant_id = getattr(g, "current_tenant_id", None)
    return user, tenant_id
```

**解读**：
- 第 11 行：先看 `g.account`（API key 场景手动设置）
- 第 12-13 行：再看 `current_user`（flask-login 标准登录）
- 第 14-15 行：最后看 `g.login_user`
- 第 18 行：tenant_id 始终从 `g.current_tenant_id` 拿
- **设计**：dify 把上下文获取封装成一个函数，Controller 层通过 `@with_current_user`、`@with_current_tenant_id` 装饰器自动注入

### 3.3 g 对象的实际使用

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_request_logging.py`
**核心代码**（行 30-50）：

```python
def _log_request_started(_sender, **_extra):
    """Log the start of a request."""
    # Record start time for access logging
    g.__request_started_ts = time.perf_counter()

    if not logger.isEnabledFor(logging.DEBUG):
        return

    request = flask.request
    if not (_is_content_type_json(request.content_type) and request.data):
        logger.debug("Received Request %s -> %s", request.method, request.path)
        return
```

**解读**：
- 第 4 行：`g.__request_started_ts` 存请求开始时间戳（带 `__` 前缀避免与 `g` 其他属性冲突）
- 第 9 行：`flask.request` 在 `request_started` 信号回调中也可以访问
- **典型用法**：在 `before_request` 或 Flask 信号中初始化 `g.xxx`，在视图函数中读取

## 4. 关键要点总结

- Flask 有**两种上下文**：应用上下文（`current_app`、`g`）和请求上下文（`request`、`session`）
- `g` 是请求级暂存，请求结束自动清空
- `session` 通过 Cookie 加密持久化跨请求数据
- dify 通过 `current_account_with_tenant()` helper 统一访问当前账号和租户
- 在 CLI / Celery / 测试中访问 `request` / `current_app` 必须用 `app_context()` 或 `test_request_context()` 手动激活
- 避免在 `current_app` 上存可变对象（线程安全风险）

## 5. 练习题

### 练习 1：基础（必做）

写一个 Flask 视图：
- 通过 `@app.before_request` 读取 `X-Request-Id` 请求头，存入 `g.request_id`
- 视图函数返回 `{"request_id": g.request_id}`
- 如果没有请求头，生成一个 UUID 填入

### 练习 2：进阶

阅读 `api/libs/login.py`：
1. `current_account_with_tenant()` 返回什么类型？
2. 在哪些场景下 `account` 为 `None`？
3. `tenant_id` 为 `None` 时表示什么？

### 练习 3：挑战（选做）

实现一个 CLI 命令清理过期 token（不在 HTTP 请求中）：

```python
import click

@app.cli.command()
def clean_expired_tokens():
    """清理过期 token"""
    # TODO: 在这里访问数据库
    # 提示：需要手动推入应用上下文
    ...
```

写完后说明为什么 CLI 命令必须用 `with app.app_context():`。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/app_factory.py` — `before_request` 钩子
- `/Users/xu/code/github/dify/api/libs/login.py` — `current_account_with_tenant` helper
- `/Users/xu/code/github/dify/api/extensions/ext_request_logging.py` — `g` 实际使用
- Flask 上下文文档：https://flask.palletsprojects.com/patterns/contextprocessors/
- Flask `g` 对象文档：https://flask.palletsprojects.com/api/#flask.g

---

**文档版本**：v1.0
**最后更新**：2026-07-13