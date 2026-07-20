# 5.3.7 输入校验与输出编码

> 理解"输入校验是安全第一道防线"，掌握 Pydantic 在 dify 中的核心角色。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解输入校验的核心原则（白名单优于黑名单）
- 掌握 Pydantic 在 dify 接口层的统一校验
- 能看懂 dify 中所有 `*Payload` 类的作用
- 区分"输入校验"和"业务校验"的责任边界

## 📚 前置知识

- Flask 基础（详见 [Flask 基础](../02-backend/03-flask-basics.md)）
- SQL 注入与参数化（详见 [SQL 注入](../../_common/05-web-security/03-sql-injection.md)）——输入校验是防注入的第一道关
- Pydantic 模型（详见 [Pydantic 基础](../02-backend/12-pydantic-basics.md)）

## 1. 核心概念

### 1.1 为什么需要输入校验？

任何来自外部的数据都不可信：
- HTTP 请求参数
- Cookie / Header
- DB 读出来的数据（可能被污染）
- 文件上传
- 第三方 API 响应

**基本原则**：白名单优于黑名单 —— **明确允许什么**比**禁止什么**更安全。OWASP 视角下输入校验还关联 XSS 输出编码等（详见 [OWASP Top 10](../../_common/05-web-security/01-owasp-top10.md)、[XSS](../../_common/05-web-security/02-xss.md)）。

### 1.2 输入校验的位置

**外层（HTTP 边界）**：
- 接口签名：用 Pydantic 模型校验请求体
- 路径参数：用 Flask 的 `<uuid:>` `<string:>` 类型转换器
- 查询参数：用 `request.args.get()` + 类型转换

**内层（业务边界）**：
- Service 层：业务规则校验（"用户余额必须 > 0"）
- DB 层：字段类型 + 长度 + 非空约束

### 1.3 dify 的双层校验

dify 用 **Pydantic + SQLAlchemy ORM** 双层校验：

1. **Pydantic**：在 HTTP 边界拦截非法输入
2. **SQLAlchemy 类型**：在 DB 写入时再做类型校验

## 2. 代码示例

### 2.1 Pydantic 校验 HTTP 请求

```python
from pydantic import BaseModel, EmailStr, Field, field_validator

class LoginPayload(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=8, max_length=64)
    remember_me: bool = Field(default=False)
    invite_token: str | None = Field(default=None, max_length=128)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower().strip()


# 在 Flask 中使用
@app.post("/login")
def login():
    try:
        args = LoginPayload.model_validate(request.json)
    except ValidationError as e:
        return {"error": "Invalid input", "details": e.errors()}, 400
    # 此处 args.email 一定是合法 email，args.password 一定是 8-64 位
    ...
```

### 2.2 常见错误：直接信任用户输入

```python
# ❌ 错误：直接用 request.json
@app.post("/transfer")
def transfer():
    to = request.json["to"]      # 可能是任意字符串
    amount = request.json["amount"]  # 可能是负数 / 字符串 / None
    return do_transfer(to, amount)  # 业务层才报错，可能造成损失

# ✅ 正确：Pydantic 提前校验
class TransferPayload(BaseModel):
    to: str = Field(..., pattern=r"^acc-[0-9a-f]{8}$")  # 白名单格式
    amount: int = Field(..., gt=0, le=1_000_000)        # 范围限制

@app.post("/transfer")
def transfer():
    args = TransferPayload.model_validate(request.json)
    return do_transfer(args.to, args.amount)
```

### 2.3 路径参数类型转换

```python
# Flask 路由类型转换器
@app.get("/users/<uuid:user_id>")  # 自动转 UUID，不合法返回 404
def get_user(user_id: UUID):
    ...

@app.get("/files/<path:filename>")  # 接受任意路径
def get_file(filename: str):
    ...
```

## 3. 关键要点总结

- 输入校验 = 白名单优于黑名单
- **三层校验**：HTTP 边界（Pydantic）→ 业务层（业务规则）→ DB 层（类型约束）
- dify 用 `*Payload` Pydantic 类作为接口契约
- `register_schema_models` 让 Swagger 自动文档化
- `model_validate()` 失败自动返回 400 + 详细错误
- `decrypt_password_field` 装饰器把 Base64 解密放在校验前

---

**文档版本**：v1.0
**最后更新**：2026-07-13
