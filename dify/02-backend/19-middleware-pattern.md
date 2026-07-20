# 2.4.2 中间件架构与拦截器模式

> 理解 Flask 中间件和拦截器模式，掌握 dify 的横切关注点处理。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 WSGI 中间件和 Flask 扩展的差异
- 理解 dify 的 `extensions/ext_*.py` 模式
- 在 dify 中找到常见的中间件（压缩、日志、metrics）
- 通过装饰器实现自定义拦截器

## 📚 前置知识

- [请求钩子](./08-flask-hooks.md)
- [Controller 装饰器](./10-flask-in-dify.md)
- WSGI 协议基础

## 1. 核心概念

### 1.1 三种横切关注点处理方式

| 方式 | 作用范围 | 触发时机 | 典型用途 |
|------|---------|---------|---------|
| **WSGI 中间件** | 整个 HTTP 请求 | 最外层 | GZip、Sentry 错误上报 |
| **Flask 扩展** | Flask app 级别 | 应用启动时初始化 | SQLAlchemy、Login |
| **请求钩子** | 每个请求 | 视图前后 | 鉴权、日志、CORS（CORS 详见 [CORS](../../_common/05-web-security/05-cors.md)） |
| **装饰器** | 单个 endpoint | 视图调用时 | RBAC、参数校验（装饰器原理详见 [装饰器](../01-fundamentals/11-decorator.md)；RBAC 详见 [`_common` RBAC](../../_common/08-authorization/01-rbac.md)） |

责任链/管道思想也常用于中间件编排（详见 [责任链](../../_fundamentals/06-design-patterns/17-chain.md)）。

### 1.2 dify 的中间件模式

dify 用 **Extension（扩展）** 模式管理中间件：

```
api/extensions/
├── ext_database.py        # SQLAlchemy 扩展
├── ext_redis.py           # Redis 客户端
├── ext_blueprints.py      # 注册 Blueprint
├── ext_compress.py        # GZip 压缩
├── ext_app_metrics.py     # 健康检查 + 版本号
├── ext_request_logging.py # 请求日志
├── ext_celery.py          # Celery 集成
└── ...
```

每个 `ext_*.py` 文件定义一个 `init_app(app: DifyApp)` 函数，在应用启动时被调用。Redis / Celery 等扩展细节见 [Redis 与 Celery 系列](../04-cache-and-queue/)（如 [Celery 架构](../04-cache-and-queue/05-celery-architecture.md)）。

### 1.3 拦截器模式（Decorator-based Interceptor）

dify 用装饰器实现细粒度拦截：

```python
@app.route("/apps")
@login_required           # 拦截器 1：必须登录
@rbac_permission_required  # 拦截器 2：必须有权限
@with_current_user         # 拦截器 3：注入当前用户
@get_app_model             # 拦截器 4：加载 app_model
def get_apps(...):
    pass
```

## 2. 代码示例

### 2.1 WSGI 中间件

```python
# WSGI 中间件（最外层，包裹整个 app）
class GZipMiddleware:
    def __init__(self, app, min_size=1024):
        self.app = app
        self.min_size = min_size

    def __call__(self, environ, start_response):
        """符合 WSGI 协议的可调用对象。"""
        # 请求前：可以修改 environ
        # ...

        # 调用下一个中间件/app
        response_started = []
        response_body = []

        def custom_start_response(status, headers, exc_info=None):
            # 收集响应头
            response_started.append((status, headers))
            return start_response(status, headers, exc_info)

        # 调用 app
        body_iter = self.app(environ, custom_start_response)

        # 收集响应体
        for chunk in body_iter:
            response_body.append(chunk)

        # 响应后：可以压缩、加密等
        status, headers = response_started[0]
        full_body = b"".join(response_body)

        if len(full_body) >= self.min_size:
            import gzip
            full_body = gzip.compress(full_body)
            headers = [(k, v) for (k, v) in headers if k.lower() != "content-length"]
            headers.append(("Content-Length", str(len(full_body))))
            headers.append(("Content-Encoding", "gzip"))

        start_response(status, headers)
        return [full_body]


# 使用
app.wsgi_app = GZipMiddleware(app.wsgi_app)
```

### 2.2 Flask Extension

```python
from dify_app import DifyApp


def init_app(app: DifyApp):
    """Flask 扩展的标准入口。"""
    from flask_compress import Compress
    compress = Compress()
    compress.init_app(app)
    # 初始化完成，扩展会在每个请求中自动生效
```

### 2.3 拦截器装饰器

```python
from functools import wraps
from flask import g, abort


def login_required(view):
    """登录检查拦截器。"""
    @wraps(view)
    def decorated(*args, **kwargs):
        if not g.get("current_user"):
            abort(401)
        return view(*args, **kwargs)
    return decorated


def rbac_required(permission: str):
    """RBAC 权限检查拦截器（带参数）。"""
    def decorator(view):
        @wraps(view)
        def decorated(*args, **kwargs):
            user = g.get("current_user")
            if not user.has_permission(permission):
                abort(403)
            return view(*args, **kwargs)
        return decorated
    return decorator


# 使用
@app.route("/apps")
@login_required
@rbac_required("app:read")
def list_apps():
    pass
```

### 2.4 常见错误：拦截器修改了 view 的行为

```python
# ❌ 错误：拦截器悄悄修改了返回值
def bad_interceptor(view):
    @wraps(view)
    def decorated(*args, **kwargs):
        result = view(*args, **kwargs)
        result["__injected"] = True  # 拦截器不应该修改业务结果
        return result
    return decorated

# ✅ 正确：拦截器只做横切关注点（鉴权、日志），不修改业务结果
def good_interceptor(view):
    @wraps(view)
    def decorated(*args, **kwargs):
        log_request()
        result = view(*args, **kwargs)
        return result  # 不修改
    return decorated
```

## 3. 关键要点总结

- dify 用 **Extension（扩展）** 模式管理中间件（`extensions/ext_*.py`）
- 每个扩展暴露 `init_app(app: DifyApp)` 函数
- **WSGI 中间件** 处理最外层（GZip、Sentry）
- **Flask 扩展** 在应用启动时初始化（SQLAlchemy、Login）
- **请求钩子** 处理每个请求（鉴权、日志）
- **装饰器** 实现细粒度拦截（RBAC、参数校验）
- dify 的拦截器用 Concatenate 泛型实现类型安全的参数注入
- 拦截器只做**横切关注点**，不修改业务结果

---

**文档版本**：v1.0
**最后更新**：2026-07-13
