# 5.3.7 输入校验与输出编码

> 理解"输入校验是安全第一道防线"，掌握 Pydantic 在 dify 中的核心角色。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解输入校验的核心原则（白名单优于黑名单）
- 掌握 Pydantic 在 dify 接口层的统一校验
- 能看懂 dify 中所有 `*Payload` 类的作用
- 区分"输入校验"和"业务校验"的责任边界

## 📚 前置知识

- 01-fundamentals/01-flask-basics.md
- 14-sql-injection.md

## 1. 核心概念

### 1.1 为什么需要输入校验？

任何来自外部的数据都不可信：
- HTTP 请求参数
- Cookie / Header
- DB 读出来的数据（可能被污染）
- 文件上传
- 第三方 API 响应

**基本原则**：白名单优于黑名单 —— **明确允许什么**比**禁止什么**更安全。

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

## 3. dify 仓库源码解读

### 3.1 登录接口的 Pydantic 校验

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/auth/login.py`
**核心代码**（行 66-91）：

```python
class LoginPayload(LoginPayloadBase):
    remember_me: bool = Field(default=False, description="Remember me flag")
    invite_token: str | None = Field(default=None, description="Invitation token")


class EmailPayload(BaseModel):
    email: EmailStr = Field(...)
    language: str | None = Field(default=None)


class EmailCodeLoginPayload(BaseModel):
    email: EmailStr = Field(...)
    code: str = Field(...)
    token: str = Field(...)
    language: str | None = Field(default=None)
    timezone: str | None = Field(default=None)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_timezone_string(value)


register_schema_models(console_ns, LoginPayload, EmailPayload, EmailCodeLoginPayload)
```

**解读**：
- 第 1-3 行：`LoginPayload` 继承基类 + 扩展字段
- 第 6-8 行：`EmailStr` 类型自动校验邮箱格式
- 第 11-15 行：必填字段用 `...` 占位
- 第 19-22 行：`@field_validator("timezone")` 自定义校验逻辑
- 第 26 行：`register_schema_models` 把模型注册到 Swagger，**自动生成 API 文档**
- **关键设计**：所有接口共用 Pydantic 模型，业务代码只关心已校验的数据

### 3.2 接口中使用 Payload

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/auth/login.py`
**核心代码**（行 101-114）：

```python
@console_ns.route("/login")
class LoginApi(Resource):
    """Resource for user login."""

    @setup_required
    @email_password_login_enabled
    @console_ns.expect(console_ns.models[LoginPayload.__name__])
    @console_ns.response(200, "Success", console_ns.models[SimpleResultOptionalDataResponse.__name__])
    @decrypt_password_field
    def post(self):
        """Authenticate user and login."""
        args = LoginPayload.model_validate(console_ns.payload)
        request_email = args.email
        normalized_email = request_email.lower()
```

**解读**：
- 第 6 行：`@console_ns.expect(...)` 告诉 Swagger 此接口接收什么模型
- 第 7 行：`@console_ns.response(...)` 声明响应类型
- 第 8 行：`@decrypt_password_field` 装饰器**先解密密码字段**（前端 Base64 编码）
- 第 10 行：`LoginPayload.model_validate(console_ns.payload)` 自动校验
- **校验失败**：自动返回 400 + 详细错误信息
- **设计意图**：所有安全检查"前置"，业务函数只接收合法数据

### 3.3 密码字段加密传输

**文件位置**：`/Users/xu/code/github/dify/api/libs/encryption.py`
**核心代码**（行 42-66）：

```python
    @classmethod
    def decrypt_password(cls, encrypted_password: str) -> str | None:
        """
        Decrypt password field

        Args:
            encrypted_password: Encrypted password from frontend

        Returns:
            Decrypted password or None if decryption fails
        """
        return cls.decrypt_field(encrypted_password)

    @classmethod
    def decrypt_verification_code(cls, encrypted_code: str) -> str | None:
        """
        Decrypt verification code field

        Args:
            encrypted_verification_code: Encrypted code from frontend

        Returns:
            Decrypted code or None if decryption fails
        """
        return cls.decrypt_field(encrypted_code)
```

**解读**：
- 第 5 行：`encrypted_password` 是 Base64 编码后的密码
- 第 12 行：返回解密后的明文密码（Base64 解码）
- **多层校验**：Base64 解码（合法性）+ Pydantic（业务字段）+ SQLAlchemy（DB 约束）

## 4. 关键要点总结

- 输入校验 = 白名单优于黑名单
- **三层校验**：HTTP 边界（Pydantic）→ 业务层（业务规则）→ DB 层（类型约束）
- dify 用 `*Payload` Pydantic 类作为接口契约
- `register_schema_models` 让 Swagger 自动文档化
- `model_validate()` 失败自动返回 400 + 详细错误
- `decrypt_password_field` 装饰器把 Base64 解密放在校验前

## 5. 练习题

### 练习 1：基础（必做）

用 Pydantic 写一个 `RegisterPayload`，要求：邮箱格式、密码 8-64 位、用户名 3-20 位字母数字下划线。

### 练习 2：进阶

阅读 `api/controllers/console/auth/login.py`，解释 dify 为什么用 `register_schema_models` 而不是在函数内部定义 Pydantic 模型？

### 练习 3：挑战（选做）

设计一个 **统一校验错误响应格式**：把所有 Pydantic ValidationError 转换为 dify 的 `SimpleResultMessageResponse` 格式，前端能稳定处理。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/auth/login.py`
- `/Users/xu/code/github/dify/api/libs/encryption.py`
- Pydantic 文档：https://docs.pydantic.dev/latest/
- OWASP 输入校验：https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13