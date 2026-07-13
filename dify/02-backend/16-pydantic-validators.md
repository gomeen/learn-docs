# 2.3.2 字段校验器：`field_validator` / `model_validator`

> 掌握 Pydantic 的字段级和模型级校验器，能实现复杂的业务校验。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `field_validator` 和 `model_validator` 的区别
- 理解 `mode="before"` vs `mode="after"` 的校验时机
- 实现跨字段校验（如确认密码、开始/结束日期）
- 在 dify 仓库中找到校验器的实际使用

## 📚 前置知识

- 02-backend/15-pydantic-basics.md（Pydantic BaseModel）
- Python 函数与装饰器

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

## 3. dify 仓库源码解读

### 3.1 field_validator：`validate_tag_ids`

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/app/app.py`
**核心代码**（行 95-100）：

```python
@field_validator("tag_ids", mode="before")
@classmethod
def validate_tag_ids(cls, value: list[str] | None) -> list[str] | None:
    if not value:
        return None
    # 处理 tags_ids 参数（可能来自 query string）
    # ...
```

**解读**：
- 第 1 行：`mode="before"` 在类型转换前执行
- 第 2 行：`@classmethod` 是 Pydantic v2 的强制要求
- 第 3 行：参数和返回值类型必须明确（用于类型检查）
- **用途**：当 `tag_ids` 是空列表时，返回 `None`（业务约定：空 = 未过滤）

### 3.2 field_validator：枚举转换

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/app/app.py`
**核心代码**（行 100-130）：

```python
@field_validator("mode", mode="before")
@classmethod
def validate_mode(cls, value: str) -> str:
    """mode 字段是 AppListMode 字面量类型，校验前规范化。"""
    if value is None:
        return DEFAULT_APP_LIST_MODE
    return value


@field_validator("sort_by", mode="before")
@classmethod
def validate_sort_by(cls, value: str) -> str:
    """sort_by 是 Literal 类型，校验前校验。"""
    if value not in ["last_modified", "recently_created", "earliest_created"]:
        raise ValueError(f"Invalid sort_by: {value}")
    return value
```

**解读**：
- 第 1 行：`mode="before"` 在类型转换前运行
- 第 5-7 行：处理 `None` 默认值
- 第 13-17 行：自定义枚举校验（在字面量类型校验之前）

### 3.3 复杂的 model_validator：图片上传

**文件位置**：`/Users/xu/code/github/dify/api/services/entities/knowledge_entities/knowledge_entities.py`
**核心代码**（节选）：

```python
class FilePayload(BaseModel):
    type: Literal["image", "document", "audio", "video"]
    transfer_method: Literal["remote_url", "local_file"]
    url: str | None = None
    upload_file_id: str | None = None

    @model_validator(mode="after")
    def check_required_fields(self):
        """根据 transfer_method 校验必填字段。"""
        if self.transfer_method == "remote_url" and not self.url:
            raise ValueError("remote_url 需要 url 字段")
        if self.transfer_method == "local_file" and not self.upload_file_id:
            raise ValueError("local_file 需要 upload_file_id 字段")
        return self
```

**解读**：
- 第 11 行：`mode="after"` 在所有字段校验完成后执行
- 第 13-15 行：跨字段约束——`transfer_method` 决定 `url`/`upload_file_id` 哪个必填
- 第 17 行：返回 `self`（必须返回）

## 4. 关键要点总结

- `field_validator` 用于**单字段校验**：`mode="before"`（转换前）或 `mode="after"`（转换后）
- `model_validator` 用于**跨字段校验**：`mode="after"`（推荐）或 `mode="before"`
- 必须用 `@classmethod` 装饰器（Pydantic v2 要求）
- 校验器必须返回有效值（不能返回 `None`，除非字段是 Optional）
- 校验失败抛 `ValueError` 或 `AssertionError`（不要抛通用 `Exception`）
- dify 用校验器做**类型转换、跨字段约束、数据规范化**

## 5. 练习题

### 练习 1：基础（必做）

定义 `UserRegistration` 模型：
- `username`: 3-20 字符，仅字母数字下划线
- `email`: 邮箱格式
- `password`: 至少 8 字符，包含数字和字母
- `password_confirm`: 与 password 相同

用 `model_validator` 校验 `password == password_confirm`。

### 练习 2：进阶

阅读 `api/controllers/console/app/app.py` 中所有 `field_validator`：
1. 列出所有使用 `mode="before"` 的校验器
2. 它们分别在做什么预处理？
3. 哪些校验器是规范化（如 lowercase）？哪些是校验（如范围）？

### 练习 3：挑战（选做）

设计 `WorkflowRunQuery` 模型，要求：
- `start_date` 和 `end_date` 都是可选
- 如果都提供，必须 `end_date > start_date`
- 如果只提供 `start_date`，默认 `end_date = now()`
- 用 `model_validator(mode="before")` 实现

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/app/app.py` — 校验器示例
- `/Users/xu/code/github/dify/api/services/entities/knowledge_entities/knowledge_entities.py` — 跨字段校验
- `/Users/xu/code/github/dify/api/core/app/entities/app_invoke_entities.py` — 复杂模型
- Pydantic v2 Validators：https://docs.pydantic.dev/latest/concepts/validators/

---

**文档版本**：v1.0
**最后更新**：2026-07-13