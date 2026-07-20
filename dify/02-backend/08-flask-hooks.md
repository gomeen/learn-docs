# 2.2.5 请求钩子：`before_request` / `after_request` / `teardown`

> 理解 Flask 的请求钩子机制，能在 dify 中正确处理横切关注点（鉴权、日志、异常）。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Flask 的四种请求钩子（`before_request`、`before_first_request`、`after_request`、`teardown_*`）
- 在 dify 中找到钩子的实际使用（`app_factory.py`、`ext_request_logging.py`）
- 理解钩子与装饰器的区别（钩子是全局的，装饰器是局部的；装饰器原理详见 [装饰器](../01-fundamentals/11-decorator.md)）
- 通过钩子实现统一的鉴权、日志、异常处理

## 📚 前置知识

- [Flask 基础](./03-flask-basics.md)
- [Flask 上下文](./04-flask-context.md)

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

## 3. 关键要点总结

- 四种钩子：`before_request`（可短路）、`after_request`（成功时）、`teardown_request`（无论成败）、`teardown_appcontext`
- dify 的全局钩子在 `app_factory.py`（license 校验、日志上下文）
- 扩展钩子在 `extensions/ext_*.py`（CORS、压缩、metrics）
- 钩子是**横切关注点**的统一处理：鉴权、日志、异常、清理
- 装饰器（如 `@login_required`）是**局部**的，针对单个 endpoint
- 钩子不能修改业务逻辑，只能做无害的补充（响应头、日志）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
