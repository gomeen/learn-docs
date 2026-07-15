# 2.2.5 请求钩子：`before_request` / `after_request` / `teardown`

> 理解 Flask 的请求钩子机制，能在 dify 中正确处理横切关注点（鉴权、日志、异常）。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Flask 的四种请求钩子（`before_request`、`before_first_request`、`after_request`、`teardown_*`）
- 在 dify 中找到钩子的实际使用（`app_factory.py`、`ext_request_logging.py`）
- 理解钩子与装饰器的区别（钩子是全局的，装饰器是局部的；装饰器原理详见 [装饰器](../01-fundamentals/10-decorator.md)）
- 通过钩子实现统一的鉴权、日志、异常处理

## 📚 前置知识

- [Flask 基础](./08-flask-basics.md)
- [Flask 上下文](./09-flask-context.md)

## 1. 核心概念

### 1.1 四种请求钩子

| 钩子 | 触发时机 | 典型用途 |
|------|---------|---------|
| `before_request` | 每次请求前 | 鉴权、初始化上下文 |
| `before_first_request` | 应用启动后第一个请求 | 一次性初始化（已废弃） |
| `after_request` | 每次请求后（无异常） | 设置响应头、记录日志 |
| `teardown_request` | 每次请求后（无论成败） | 清理资源、关闭 session |
| `teardown_appcontext` | 应用上下文销毁时 | 清理数据库连接 |

**关键差异**：
- `before_request` / `after_request`：可以**短路**（`return` 即响应）
- `teardown_request`：不能短路，只能清理

### 1.2 钩子的执行顺序

```
Request received
    ↓
[before_request] ← 可短路返回响应
    ↓
View Function
    ↓
[after_request] ← 仅成功时执行
    ↓
[teardown_request] ← 无论成败执行
    ↓
Response sent
```

### 1.3 dify 中的钩子使用

dify 的钩子集中在两个地方：

1. **`app_factory.py`**：全局钩子（鉴权、license 校验）
2. **`extensions/ext_*.py`**：各扩展的钩子（CORS、压缩、日志、metrics）

## 2. 代码示例

### 2.1 before_request：初始化 + 鉴权

```python
from flask import Flask, request, g, abort

app = Flask(__name__)

@app.before_request
def auth_and_init():
    """每个请求前：鉴权 + 初始化用户上下文"""
    # 1. 鉴权（从 Header 拿 token）
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        abort(401)

    # 2. 查询用户
    user = verify_token(token)
    if not user:
        abort(401)

    # 3. 存入 g（请求级共享）
    g.current_user = user
    g.tenant_id = user.tenant_id
```

### 2.2 after_request：响应增强

```python
@app.after_request
def add_version_header(response):
    """每个请求后：添加版本号响应头"""
    response.headers["X-Version"] = "1.0.0"
    response.headers["X-Env"] = "production"
    return response

@app.after_request
def log_response(response):
    """每个请求后：记录响应"""
    duration = time.perf_counter() - g.get("__start_ts", 0)
    logger.info(f"{request.method} {request.path} -> {response.status_code} ({duration:.3f}s)")
    return response
```

### 2.3 teardown_request：资源清理

```python
@app.teardown_request
def close_db_session(exception=None):
    """每个请求后：关闭数据库 session（无论成败）"""
    if hasattr(g, "db_session"):
        try:
            if exception:
                g.db_session.rollback()
            else:
                g.db_session.commit()
        finally:
            g.db_session.close()
```

### 2.4 常见错误：在 after_request 中修改业务逻辑

```python
# ❌ 错误：在 after_request 中改变响应数据
@app.after_request
def filter_sensitive_data(response):
    if "password" in response.json:
        response.json["password"] = "***"  # 太晚，业务层应该处理
    return response

# ✅ 正确：业务逻辑放在 view 中，after_request 只做无害的补充
@app.after_request
def add_cors_header(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response
```

## 3. dify 仓库源码解读

### 3.1 `before_request`：License 校验

**文件位置**：`/Users/xu/code/github/dify/api/app_factory.py`
**核心代码**（行 59-100）：

```python
@dify_app.before_request
def before_request():
    # Initialize logging context for this request
    init_request_context()
    RecyclableContextVar.increment_thread_recycles()

    # Enterprise license validation for API endpoints (both console and webapp)
    # When license expires, block all API access except bootstrap endpoints needed
    # for the frontend to load the license expiration page without infinite reloads.
    if dify_config.ENTERPRISE_ENABLED:
        is_console_api = request.path.startswith("/console/api/")
        is_webapp_api = request.path.startswith("/api/")

        if is_console_api or is_webapp_api:
            if is_console_api:
                is_exempt = any(request.path.startswith(p) for p in _CONSOLE_EXEMPT_PREFIXES)
            else:  # webapp API
                is_exempt = request.path.startswith("/api/system-features")

            if not is_exempt:
                try:
                    # Check license status (cached — see EnterpriseService for TTL details)
                    features = EnterpriseService.get_system_features()
                    if features.license.status in [
                        LicenseStatus.INACTIVE,
                        LicenseStatus.EXPIRED,
                        LicenseStatus.LOST,
                    ]:
                        raise UnauthorizedAndForceLogout(
                            "Your license is invalid. Please contact your administrator."
                        )
```

**解读**：
- 第 2 行：`@dify_app.before_request` 全局钩子，每个请求前都执行
- 第 4 行：`init_request_context()` 初始化日志上下文（trace_id 等）
- 第 5 行：`increment_thread_recycles()` gevent 线程回收计数
- 第 9-15 行：判断是否是 console API / webapp API
- 第 18-19 行：`is_exempt` 白名单（setup、login 等不需要 license）
- 第 23-32 行：检查 license 状态，失效则抛出 `UnauthorizedAndForceLogout`

### 3.2 `after_request`：版本号响应头

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_app_metrics.py`
**核心代码**（行 1-25）：

```python
import json
import os
import threading

from flask import Response

from configs import dify_config
from dify_app import DifyApp


def init_app(app: DifyApp):
    @app.after_request
    def after_request(response):
        """Add Version headers to the response."""
        response.headers.add("X-Version", dify_config.project.version)
        response.headers.add("X-Env", dify_config.DEPLOY_ENV)
        return response

    @app.route("/health")
    def health():
        return Response(
            json.dumps({"pid": os.getpid(), "status": "ok", "version": dify_config.project.version}),
            status=200,
            content_type="application/json",
        )
```

**解读**：
- 第 14-19 行：`@app.after_request` 给所有响应加 `X-Version` 和 `X-Env` 头
- 第 21-28 行：顺便注册 `/health` 健康检查端点
- **优点**：版本号信息统一加，无需在每个 view 中处理

### 3.3 `teardown_request`：数据库连接清理

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**（行 18-65）：

```python
def _safe_rollback(connection):
    """Safely rollback database connection."""
    try:
        connection.rollback()
    except Exception:
        logger.exception("Failed to rollback connection")


def _setup_gevent_compatibility():
    global _gevent_compatibility_setup

    # Avoid duplicate registration
    if _gevent_compatibility_setup:
        return

    @event.listens_for(Pool, "reset")
    def _safe_reset(dbapi_connection, connection_record, reset_state):
        if reset_state.terminate_only:
            return

        # Safe rollback for connection
        try:
            hub = gevent.get_hub()
            if hasattr(hub, "loop") and getattr(hub.loop, "in_callback", False):
                gevent.spawn_later(0, lambda: _safe_rollback(dbapi_connection))
            else:
                _safe_rollback(dbapi_connection)
        except (AttributeError, ImportError):
            _safe_rollback(dbapi_connection)
```

**解读**：
- 第 27 行：用 SQLAlchemy 的 `event.listens_for` 注册 `Pool.reset` 事件
- 第 30-43 行：在 gevent 协程中安全 rollback（gevent 的 hub 回调中不能直接 DB 操作）
- **本质**：这是一个**SQLAlchemy 级别的 teardown 钩子**，与 Flask 的 `teardown_request` 不同

## 4. 关键要点总结

- 四种钩子：`before_request`（可短路）、`after_request`（成功时）、`teardown_request`（无论成败）、`teardown_appcontext`
- dify 的全局钩子在 `app_factory.py`（license 校验、日志上下文）
- 扩展钩子在 `extensions/ext_*.py`（CORS、压缩、metrics）
- 钩子是**横切关注点**的统一处理：鉴权、日志、异常、清理
- 装饰器（如 `@login_required`）是**局部**的，针对单个 endpoint
- 钩子不能修改业务逻辑，只能做无害的补充（响应头、日志）

## 5. 练习题

### 练习 1：基础（必做）

实现一个 Flask app：
- `before_request`：记录请求开始时间到 `g.start_ts`，并检查必需 header `X-API-Key`
- `after_request`：计算请求耗时，记录到 `X-Duration` 响应头
- `teardown_request`：记录请求结束日志

### 练习 2：进阶

阅读 `api/extensions/ext_request_logging.py`：
1. 它用了 `request_started` 信号还是 `before_request` 钩子？
2. 为什么用信号而不是钩子？
3. 它如何处理 JSON 请求体（避免日志过长）？

### 练习 3：挑战（选做）

为 dify 设计一个 `ext_rate_limit.py` 扩展：
- 通过 `before_request` 钩子对每个 IP 限流（每分钟 100 次）
- 用 Redis 存储计数器（`extensions/ext_redis.py` 提供 `redis_client`）
- 超过限制返回 429 状态码
- 白名单路径（`/health`）不限流

写完后说明为什么限流应该用 `before_request` 而不是在 view 内部判断。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/app_factory.py` — License 校验钩子
- `/Users/xu/code/github/dify/api/extensions/ext_app_metrics.py` — after_request 示例
- `/Users/xu/code/github/dify/api/extensions/ext_database.py` — SQLAlchemy teardown
- `/Users/xu/code/github/dify/api/extensions/ext_request_logging.py` — 请求日志
- Flask 钩子文档：https://flask.palletsprojects.com/api/#flask.Flask.before_request

---

**文档版本**：v1.0
**最后更新**：2026-07-13