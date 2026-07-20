# 2.2.3 蓝图（Blueprint）组织大型应用

> 掌握 Flask Blueprint 模块化路由的方法，理解 dify 中按用途拆分的 Blueprint 结构。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Blueprint 的创建、注册和路由定义
- 理解 Blueprint 的 URL 前缀（`url_prefix`）机制
- 在 dify 中找到 8 个核心 Blueprint 的位置
- 设计可扩展的模块化路由结构

## 📚 前置知识

- [Flask 基础](./03-flask-basics.md)
- Python 模块化基础（详见 [模块与导入](../01-fundamentals/04-python-modules-and-imports.md)）

## 1. 核心概念

### 1.1 什么是 Blueprint？

Blueprint 是 Flask 的**路由模块化机制**：把一组相关路由打包成一个对象，然后注册到 app 上。

**类比**：
- Blueprint ≈ Django 的 `urls.py` 模块
- Blueprint ≈ Spring MVC 的 `@RestController`
- Blueprint ≈ Express.js 的 `Router`

```python
# 定义 Blueprint
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/users")
def users():
    ...

# 注册到 app
app.register_blueprint(admin_bp)
```

### 1.2 Blueprint 的关键参数

| 参数 | 作用 |
|------|------|
| `name` | Blueprint 名称（用于 `url_for()`） |
| `import_name` | 通常 `__name__` |
| `url_prefix` | 所有路由的 URL 前缀 |
| `template_folder` | 模板目录（如果用 Jinja2） |
| `static_folder` | 静态文件目录 |

### 1.3 dify 的 Blueprint 拆分策略

dify 按**用途**拆分 Blueprint：

| Blueprint | 路径前缀 | 用途 |
|-----------|---------|------|
| `console` | `/console/api` | 管理后台 API（开发者用） |
| `web` | `/api` | WebApp API（终端用户用） |
| `service_api` | `/v1` | 对外 OpenAI 兼容 API |
| `inner_api` | `/inner/api` | 内部服务调用 |
| `mcp` | `/mcp` | MCP 协议接入 |
| `openapi` | (其他) | OpenAPI 文档生成 |
| `trigger` | `/trigger` | 触发器回调 |
| `files` | `/files` | 文件上传/下载 |

每个 Blueprint 内部用 `flask_restx.Namespace` 进一步分组。

## 2. 代码示例

### 2.1 基本 Blueprint

```python
# admin/__init__.py
from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

from . import users, orders  # 导入路由模块（触发装饰器执行）

# admin/users.py
from . import admin_bp

@admin_bp.route("/users")
def list_users():
    return {"users": []}

# admin/orders.py
@admin_bp.route("/orders")
def list_orders():
    return {"orders": []}

# app.py
from admin import admin_bp
app.register_blueprint(admin_bp)
```

### 2.2 嵌套 Blueprint

```python
# 支持嵌套 URL 前缀
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")
users_bp = Blueprint("users", __name__, url_prefix="/users")
orders_bp = Blueprint("orders", __name__, url_prefix="/orders")

api_v1_bp.register_blueprint(users_bp)
api_v1_bp.register_blueprint(orders_bp)
app.register_blueprint(api_v1_bp)
# 最终路径：/api/v1/users、/api/v1/orders
```

### 2.3 Blueprint 钩子

```python
auth_bp = Blueprint("auth", __name__)

@auth_bp.before_request
def require_login():
    if not current_user.is_authenticated:
        abort(401)

# 只对 auth_bp 内的路由生效
@auth_bp.route("/profile")
def profile():
    return {"name": current_user.name}
```

### 2.4 常见错误：忘记注册 Blueprint

```python
# ❌ 错误：定义了 Blueprint 但没注册
api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/users")
def users():
    return {"users": []}

app = Flask(__name__)
# 访问 /api/users 返回 404
```

## 3. 关键要点总结

- Blueprint 把路由**模块化**：把相关路由打包成一个对象，注册到 app
- `url_prefix` 是 Blueprint 的 URL 前缀（dify 中所有 Blueprint 都有）
- dify 按**用途**拆分 8 个 Blueprint（console、web、service_api 等）
- 每个 Blueprint 内部用 `flask_restx.Namespace` 进一步分组
- 定义 Blueprint 后必须 `register_blueprint()` 才生效
- `RESOURCE_MODULES` 元组 + `import_module` 是 dify 的 controller 自动注册机制

---

**文档版本**：v1.0
**最后更新**：2026-07-13
