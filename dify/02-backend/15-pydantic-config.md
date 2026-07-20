# 2.3.4 Pydantic 配置：`ConfigDict` / `extra="forbid"`

> 掌握 Pydantic 的 ConfigDict 配置，能设计严格的 DTO 校验。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Pydantic v2 的 ConfigDict 关键配置
- 理解 `extra="forbid"` 的价值（防止字段拼写错误）
- 在 dify 中找到 `extra`、`from_attributes`、`populate_by_name` 的实际配置
- 设计严格 vs 宽松的 DTO 策略

## 📚 前置知识

- [Pydantic BaseModel](./12-pydantic-basics.md)
- [DTO 三层 Schema](./14-pydantic-dto.md)

## 1. 核心概念

### 1.1 ConfigDict 的关键配置

Pydantic v2 用 `ConfigDict` 配置模型行为。其中 `frozen=True` 让实例不可变，语义类似 `@dataclass(frozen=True)`（dataclass 详见 [dataclass](../01-fundamentals/26-dataclasses.md)）：

```python
from pydantic import BaseModel, ConfigDict

class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",         # 禁止额外字段
        from_attributes=True,   # 支持 ORM 反序列化
        populate_by_name=True,  # 支持字段别名
        frozen=True,            # 模型不可变
        strict=True,            # 严格类型检查
    )
```

### 1.2 常用配置项

| 配置 | 作用 | 默认值 | 适用场景 |
|------|------|--------|---------|
| `extra` | 是否允许额外字段 | `"ignore"` | API 输入校验（推荐 `forbid`） |
| `from_attributes` | 支持 ORM/对象属性 | `False` | Response DTO |
| `populate_by_name` | 序列化时支持别名 | `False` | 与前端字段名不一致时 |
| `frozen` | 实例不可变 | `False` | 值对象 |
| `str_strip_whitespace` | 自动去除前后空格 | `False` | 字符串字段 |
| `use_enum_values` | 序列化时用 enum 值 | `False` | 与 JSON 序列化 |
| `arbitrary_types_allowed` | 允许任意类型字段 | `False` | 自定义类型 |

### 1.3 extra 模式对比

```python
# 默认 (ignore): 忽略未知字段
class Default(BaseModel):
    name: str
# Default.model_validate({"name": "Alice", "extra_field": "x"})  # OK

# forbid: 禁止未知字段
class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
# Strict.model_validate({"name": "Alice", "extra_field": "x"})  # ValidationError!

# allow: 保留未知字段
class Permissive(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
# Permissive.model_validate({"name": "Alice", "extra": "x"}).extra  # "x"
```

## 2. 代码示例

### 2.1 API 请求校验：extra="forbid"

```python
from pydantic import BaseModel, ConfigDict, Field


class CreateUserPayload(BaseModel):
    """创建用户请求体（严格模式）"""
    model_config = ConfigDict(extra="forbid")  # 禁止额外字段

    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r"^[\w.-]+@[\w.-]+$")


# 测试
# OK
CreateUserPayload.model_validate({"name": "Alice", "email": "a@b.com"})

# ❌ 报错：未知字段
CreateUserPayload.model_validate({
    "name": "Alice",
    "email": "a@b.com",
    "is_admin": True,  # 拼写错误或注入攻击
})
# ValidationError: Extra inputs are not permitted
```

### 2.2 Response DTO：from_attributes

```python
class UserORM:
    def __init__(self, id, name, email, password_hash):
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash  # 敏感


class UserResponse(BaseModel):
    """用户响应（自动从 ORM 读取）"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    # 不暴露 password_hash


# ORM → DTO
orm = UserORM(id="u001", name="Alice", email="a@b.com", password_hash="secret")
response = UserResponse.model_validate(orm)
# 只包含 id、name、email，不包含 password_hash
```

### 2.3 字段别名：populate_by_name

```python
class APIRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(alias="userId")


# 接收时支持两种字段名
req1 = APIRequest.model_validate({"userId": "u001"})  # OK
req2 = APIRequest.model_validate({"user_id": "u001"})  # 也 OK

# 序列化时
print(req1.model_dump(by_alias=True))  # {"userId": "u001"}
print(req1.model_dump())  # {"user_id": "u001"}（默认 Python 字段名）
```

### 2.4 值对象：frozen=True

```python
class Money(BaseModel):
    """值对象：不可变"""
    model_config = ConfigDict(frozen=True)

    amount: int
    currency: str = "CNY"


money = Money(amount=100)
money.amount = 200  # ❌ ValidationError: Instance is frozen

# 相等性按值
m1 = Money(amount=100, currency="USD")
m2 = Money(amount=100, currency="USD")
print(m1 == m2)  # True
```

### 2.5 字符串规范化

```python
class CleanString(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str
    description: str


# 自动去除前后空格
obj = CleanString.model_validate({"name": "  Alice  ", "description": "  desc  "})
print(obj.name)  # "Alice"
print(obj.description)  # "desc"
```

### 2.6 常见错误：忘记 frozen=True 的值对象

```python
# ❌ 错误：值对象可变（违反 DDD）
class MoneyBad(BaseModel):
    amount: int
    currency: str = "CNY"

m = MoneyBad(amount=100)
m.amount = 200  # 静默修改

# ✅ 正确：frozen=True
class MoneyGood(BaseModel):
    model_config = ConfigDict(frozen=True)
    amount: int
    currency: str = "CNY"
```

## 3. 关键要点总结

- `ConfigDict` 用类属性 `model_config` 配置
- **API 输入校验**：用 `extra="forbid"` 防止字段拼写错误
- **Response DTO**：用 `from_attributes=True` 支持 ORM 反序列化
- **值对象**：用 `frozen=True` 实现不可变
- **跨模块类型**：用 `arbitrary_types_allowed=True` 允许任意类型
- **字符串规范化**：用 `str_strip_whitespace=True` 自动去空格
- **dify 的 ResponseModel 基类**集中配置 `from_attributes` 和 `populate_by_name`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
