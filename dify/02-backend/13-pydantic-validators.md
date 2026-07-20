# 2.3.2 字段校验器：`field_validator` / `model_validator`

> 掌握 Pydantic 的字段级和模型级校验器，能实现复杂的业务校验。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `field_validator` 和 `model_validator` 的区别
- 理解 `mode="before"` vs `mode="after"` 的校验时机
- 实现跨字段校验（如确认密码、开始/结束日期）
- 在 dify 仓库中找到校验器的实际使用

## 📚 前置知识

- [Pydantic BaseModel](./12-pydantic-basics.md)
- Python 函数与装饰器（`@field_validator` 是装饰器写法，详见 [装饰器](../01-fundamentals/11-decorator.md)）

## 1. 核心概念

### 1.1 两种校验器

| 校验器 | 作用范围 | 典型场景 |
|--------|---------|---------|
| `field_validator` | 单个字段 | 邮箱格式、手机号、脱敏 |
| `model_validator` | 整个模型 | 跨字段约束（密码确认、日期范围） |

### 1.2 mode="before" vs mode="after"

```python
@field_validator("age", mode="before")
@classmethod
def validate_age_before(cls, v):
    """在校验前转换（如字符串转 int）"""
    if isinstance(v, str):
        return int(v)
    return v

@field_validator("age", mode="after")
@classmethod
def validate_age_after(cls, v):
    """在校验后处理（必须是 int）"""
    if v < 0:
        raise ValueError("年龄不能为负")
    return v
```

**执行顺序**：
```
输入数据 → [field_validator before] → 类型转换 → [field_validator after] → 完成
                                          ↓
                                  [model_validator]
```

### 1.3 dify 中的校验器

dify 用校验器处理：
- **类型转换**：字符串 → int、UUID 标准化
- **跨字段约束**：查询参数 tags_ids 与 creator_ids 互斥
- **数据规范化**：邮箱小写化、去除前后空格

## 2. 代码示例

### 2.1 field_validator：单字段校验

```python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    email: str
    age: int

    @field_validator("email", mode="after")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("邮箱格式错误")
        return v.lower().strip()  # 规范化

    @field_validator("age", mode="before")
    @classmethod
    def parse_age(cls, v):
        """mode='before' 在类型转换前运行"""
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                raise ValueError("年龄必须是数字")
        return v


# 测试
user = User(email="  ALICE@Example.com  ", age="30")
print(user.email)  # "alice@example.com"（规范化）
print(user.age)  # 30（字符串转 int）
```

### 2.2 model_validator：跨字段校验

```python
from pydantic import BaseModel, model_validator
from datetime import datetime

class Event(BaseModel):
    name: str
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def check_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("结束时间必须晚于开始时间")
        return self


# 测试
try:
    Event(name="会议", start_time=datetime(2026, 7, 13, 14, 0), end_time=datetime(2026, 7, 13, 13, 0))
except ValidationError as e:
    print(e.errors())
```

### 2.3 model_validator(mode="before")：转换整个 dict

```python
class UserRequest(BaseModel):
    name: str
    email: str

    @model_validator(mode="before")
    @classmethod
    def preprocess(cls, data):
        """在 Pydantic 处理整个 dict 前预处理"""
        if isinstance(data, dict):
            # 把所有字段名转小写
            return {k.lower(): v for k, v in data.items()}
        return data


# 测试
user = UserRequest.model_validate({"Name": "Alice", "EMAIL": "a@b.com"})
print(user.name, user.email)  # "Alice" "a@b.com"
```

### 2.4 常见错误：忘记 `@classmethod`

```python
# ❌ 错误：会报错（缺少 classmethod）
@field_validator("email")
def validate_email(cls, v):
    return v.lower()

# ✅ 正确
@field_validator("email")
@classmethod
def validate_email(cls, v):
    return v.lower()
```

### 2.5 常见错误：校验器抛出通用 Exception

```python
# ❌ 错误：抛通用异常，Pydantic 不会包装
@field_validator("age")
@classmethod
def validate_age(cls, v):
    if v < 0:
        raise Exception("年龄错误")  # 不推荐

# ✅ 正确：抛 ValueError 或 AssertionError
@field_validator("age")
@classmethod
def validate_age(cls, v):
    if v < 0:
        raise ValueError("年龄不能为负")
    return v
```

## 3. 关键要点总结

- `field_validator` 用于**单字段校验**：`mode="before"`（转换前）或 `mode="after"`（转换后）
- `model_validator` 用于**跨字段校验**：`mode="after"`（推荐）或 `mode="before"`
- 必须用 `@classmethod` 装饰器（Pydantic v2 要求）
- 校验器必须返回有效值（不能返回 `None`，除非字段是 Optional）
- 校验失败抛 `ValueError` 或 `AssertionError`（不要抛通用 `Exception`）
- dify 用校验器做**类型转换、跨字段约束、数据规范化**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
