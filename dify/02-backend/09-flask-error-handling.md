# 2.2.6 自定义错误处理与异常体系

> 理解 dify 的异常体系，能设计统一的错误响应。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Flask 的 `@app.errorhandler` 装饰器和 `abort()` 函数
- 理解 dify 自定义的 `BaseHTTPException` 异常体系
- 在 dify 中找到各种错误类型（`NotSetupError`、`UnauthorizedAndForceLogout`）
- 设计统一的错误响应格式

## 📚 前置知识

- [Flask 基础](./03-flask-basics.md)
- Python 异常处理基础（try/except、raise；详见 [异常处理](../01-fundamentals/06-python-exceptions.md)）
- [请求钩子](./08-flask-hooks.md)

## 1. 核心概念

### 1.1 Flask 的异常处理机制

```python
# 1. abort() 抛出 HTTPException
from flask import abort
abort(404)  # 抛出 NotFound
abort(403, "禁止访问")  # 抛出 Forbidden with description

# 2. errorhandler() 注册自定义处理
@app.errorhandler(404)
def not_found(error):
    return {"error": "Not Found", "code": 404}, 404
```

### 1.2 dify 的异常体系

dify 定义了**领域异常基类** `BaseHTTPException`：

```python
# libs/exception.py
class BaseHTTPException(Exception):
    error_code: str  # 业务错误码（如 "not_setup"）
    description: str  # 错误描述
    code: int  # HTTP 状态码

# controllers/console/error.py
class NotSetupError(BaseHTTPException):
    error_code = "not_setup"
    description = "Dify has not been initialized..."
    code = 401
```

所有业务异常都继承 `BaseHTTPException`，统一返回格式：

```json
{
  "code": "not_setup",
  "message": "Dify has not been initialized...",
  "status": 401
}
```

### 1.3 异常体系的优势

| 优势 | 说明 |
|------|------|
| 类型安全 | 用类表示错误，IDE 能自动补全 |
| 统一格式 | 所有 `BaseHTTPException` 自动转 JSON |
| 易于扩展 | 新增异常只需继承基类 |
| 易于测试 | 测试时可以 `pytest.raises(NotSetupError)` |

## 2. 代码示例

### 2.1 自定义 HTTP 异常

```python
from libs.exception import BaseHTTPException

class NotSetupError(BaseHTTPException):
    error_code = "not_setup"
    description = "Dify has not been initialized and installed yet."
    code = 401


class AlreadySetupError(BaseHTTPException):
    error_code = "already_setup"
    description = "Dify has been successfully installed."
    code = 403


# 使用
raise NotSetupError()  # 自动返回 401 + {"code": "not_setup", "message": "..."}
```

### 2.2 注册全局异常处理

```python
from flask import jsonify
from werkzeug.exceptions import HTTPException

@app.errorhandler(BaseHTTPException)
def handle_business_error(error: BaseHTTPException):
    """统一处理业务异常"""
    return jsonify({
        "code": error.error_code,
        "message": error.description,
        "status": error.code,
    }), error.code


@app.errorhandler(HTTPException)
def handle_http_error(error: HTTPException):
    """处理 Flask 内置 HTTP 异常"""
    return jsonify({
        "code": error.name.lower().replace(" ", "_"),
        "message": error.description,
        "status": error.code,
    }), error.code


@app.errorhandler(Exception)
def handle_unexpected_error(error: Exception):
    """兜底：未捕获的异常"""
    logger.exception(f"Unhandled error: {error}")
    return jsonify({
        "code": "internal_error",
        "message": "Internal server error",
        "status": 500,
    }), 500
```

### 2.3 自定义异常携带额外信息

```python
class ValidationError(BaseHTTPException):
    error_code = "validation_error"
    description = "Request validation failed"
    code = 422

    def __init__(self, errors: list[dict]):
        super().__init__()
        self.errors = errors

    def to_dict(self):
        return {
            "code": self.error_code,
            "message": self.description,
            "status": self.code,
            "errors": self.errors,  # 详细错误信息
        }


# 使用：Pydantic 校验失败
try:
    payload = CreateUserPayload.model_validate(data)
except ValidationError as e:
    raise ValidationError(errors=e.errors())
```

### 2.4 常见错误：在异常中返回敏感信息

```python
# ❌ 错误：异常描述泄漏 SQL 或文件路径
class BadError(BaseHTTPException):
    description = f"数据库连接失败：postgresql://user:password@host/db"

# ✅ 正确：描述面向用户，技术细节写日志
class GoodError(BaseHTTPException):
    description = "服务暂时不可用，请稍后重试"

# 把详细信息记录到日志
logger.exception(f"Database connection failed: ...")
```

## 3. 关键要点总结

- dify 定义 `BaseHTTPException` 继承 `werkzeug.HTTPException`
- 业务异常用类表示：每个异常类 = 1 个 `error_code` + 1 个 `description` + 1 个 HTTP 状态码
- 触发方式：`raise NotSetupError()`，自动转为 JSON 响应
- `setup_required`、`login_required` 等装饰器集中抛业务异常
- Pydantic 校验失败用 `UnprocessableEntity`（422）
- 所有异常通过 `@app.errorhandler` 统一处理为 JSON 格式

---

**文档版本**：v1.0
**最后更新**：2026-07-13
