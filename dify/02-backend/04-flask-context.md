# 2.2.2 Flask 上下文机制：`g` / `request` / `session` / `current_app`

> 理解 Flask 的四种上下文对象，能在 dify 中正确使用 request-scoped 数据。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Flask 的四种上下文对象（`g`、`request`、`session`、`current_app`）
- 理解应用上下文（App Context）和请求上下文（Request Context）的区别
- 在 dify 中找到 `g`、`current_user` 等上下文对象的使用
- 避免上下文相关的常见错误（Working Outside Application Context）

## 📚 前置知识

- [Flask 基础](./03-flask-basics.md)
- Python 线程局部变量基础（`threading.local`）

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
- 必须用 `with app.app_context():` 或 `with app.test_request_context():` 手动激活（`with` 是上下文管理器语法，详见 [上下文管理器](../01-fundamentals/12-context-manager.md)）

### 1.3 dify 的特殊使用

dify 通过 Flask 上下文传递：
- `g`：存储当前用户、租户、trace_id 等（多租户上下文详见 [多租户架构](./18-multi-tenancy.md)）
- `current_user`：通过 `flask-login` 的 `current_user` proxy
- `current_account_with_tenant()`：dify 自定义的 helper，从 `g` 取出账号和租户

## 2. 代码示例

### 2.1 `g` 对象：请求级暂存

```python
from flask import g, request

@app.before_request
def load_user():
    """每个请求前把用户加载到 g（before_request 详见 [请求钩子](./08-flask-hooks.md)）"""
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

## 3. 关键要点总结

- Flask 有**两种上下文**：应用上下文（`current_app`、`g`）和请求上下文（`request`、`session`）
- `g` 是请求级暂存，请求结束自动清空
- `session` 通过 Cookie 加密持久化跨请求数据
- dify 通过 `current_account_with_tenant()` helper 统一访问当前账号和租户
- 在 CLI / Celery / 测试中访问 `request` / `current_app` 必须用 `app_context()` 或 `test_request_context()` 手动激活
- 避免在 `current_app` 上存可变对象（线程安全风险）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
