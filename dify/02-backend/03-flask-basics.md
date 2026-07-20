# 2.2.1 Flask 基础：路由、视图、请求响应对象

> 理解 Flask 框架的核心机制，能读懂 dify 的 Controller 层代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Flask 的最小应用结构（路由 + 视图）
- 理解 `request`、`response` 对象的常用属性和方法
- 在 dify 中找到 Flask app 的创建入口（`app_factory.py`）
- 区分 Blueprint、Resource、Namespace 的不同抽象层级

## 📚 前置知识

- Python 函数、装饰器基础（详见 [装饰器](../01-fundamentals/11-decorator.md)）
- HTTP 协议基础（GET、POST、状态码；详见 [HTTP 协议](../../_common/14-api-protocols/01-http-protocol.md)）

## 1. 核心概念

### 1.1 Flask 的核心思想

Flask 是一个**微框架**（microframework）：只提供路由、请求处理、模板渲染等核心功能，其他都通过扩展实现。

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/hello", methods=["GET"])
def hello():
    name = request.args.get("name", "World")
    return jsonify({"message": f"Hello, {name}!"})
```

### 1.2 Flask 应用的三个层次

```
Flask 应用（app）
├── Blueprint 1（模块化路由组）
│   ├── Route A
│   ├── Route B
│   └── Resource（REST 资源）
├── Blueprint 2
└── Extension（数据库、登录、CORS 等）
```

dify 的结构对应：
- **Flask 应用**：`DifyApp`（`api/dify_app.py`）
- **Blueprint**：`controllers/console/__init__.py` 中的 `bp = Blueprint("console", ...)`（详见 [Blueprint](./05-flask-blueprint.md)）
- **Resource**：用 `flask_restx.Namespace` + `Resource` 类（详见 [Flask-RESTX](./06-flask-restx.md)）
- **Extension**：`extensions/ext_*.py` 下的各种扩展

### 1.3 dify 的 Flask 应用启动流程

```
api/app_factory.py::create_flask_app_with_configs()
  ↓ 创建 DifyApp
  ↓ 注册各种 ext_*.py（ext_database, ext_login, ext_blueprints 等）
  ↓ 注册 before_request / after_request 钩子
  ↓ 返回 app
api/app.py::app = create_flask_app_with_configs()
  ↓ Gunicorn 加载这个 app
```

### 1.4 请求生命周期

```
HTTP Request
  ↓
WSGI Middleware（Gunicorn）
  ↓
Flask.before_request() 钩子
  ↓
URL 匹配 → Route
  ↓
View Function / Resource
  ↓
Flask.after_request() 钩子
  ↓
HTTP Response
```

## 2. 代码示例

### 2.1 最小 Flask 应用

```python
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)

# 1. 基础路由
@app.route("/")
def index():
    return "Hello, World!"

# 2. 带参数
@app.route("/users/<int:user_id>")
def get_user(user_id: int):
    return jsonify({"id": user_id, "name": "Alice"})

# 3. 不同 HTTP 方法
@app.route("/users", methods=["GET", "POST"])
def users():
    if request.method == "GET":
        return jsonify({"users": []})
    elif request.method == "POST":
        data = request.get_json()
        # ... 创建用户
        return jsonify({"id": 1, "name": data["name"]}), 201

# 4. 自定义响应
@app.route("/custom")
def custom():
    response = make_response("Custom response")
    response.headers["X-Custom"] = "value"
    response.status_code = 200
    return response

# 5. 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404
```

### 2.2 request 对象

```python
from flask import request

@app.route("/example", methods=["POST"])
def example():
    # 1. URL 参数 (?key=value)
    page = request.args.get("page", default=1, type=int)

    # 2. 表单数据
    username = request.form.get("username")

    # 3. JSON body
    data = request.get_json()  # 自动解析 Content-Type: application/json
    name = data.get("name") if data else None

    # 4. 请求头
    auth = request.headers.get("Authorization")
    content_type = request.content_type

    # 5. 上传文件
    uploaded_file = request.files.get("file")

    # 6. Cookies
    session_id = request.cookies.get("session_id")

    return jsonify({
        "page": page,
        "username": username,
        "name": name,
        "auth": auth,
    })
```

### 2.3 常见错误：忘记解析 JSON

```python
# ❌ 错误：直接访问 request.json 可能为 None
@app.route("/api/users", methods=["POST"])
def create_user():
    name = request.json["name"]  # AttributeError if no JSON body

# ✅ 正确：用 get_json(silent=True) 避免异常
@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "name is required"}), 400
```

## 3. 关键要点总结

- Flask 是**微框架**：核心是路由 + 请求响应，其他通过扩展实现
- dify 的 Flask 应用入口在 `api/app_factory.py::create_flask_app_with_configs()`
- `DifyApp` 是 Flask 子类，扩展了 dify 特有的属性
- Blueprint 用于**模块化路由**：dify 按 `console` / `web` / `service_api` 等拆分
- `before_request` 钩子在 `app_factory.py` 注册，全局生效
- `request.get_json(silent=True)` 是解析 JSON body 的安全方式

---

**文档版本**：v1.0
**最后更新**：2026-07-13
