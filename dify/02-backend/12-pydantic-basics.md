# 2.3.1 Pydantic v2 数据建模：`BaseModel` 与字段类型

> 掌握 Pydantic v2 的 BaseModel 和字段类型，能看懂 dify 中所有数据模型。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Pydantic v2 的 BaseModel 基础用法
- 理解字段类型系统（基础类型、容器类型、嵌套模型）
- 在 dify 仓库中找到 Pydantic 模型（`api/core/app/entities/...`）
- 用 Pydantic 替换手写数据类（dataclass）

## 📚 前置知识

- Python 类型提示基础（type hints；详见 [typing 基础](../01-fundamentals/08-python-typing-basics.md)）
- [TypedDict](../01-fundamentals/09-typeddict.md)（TypedDict vs Pydantic）

## 1. 核心概念

### 1.1 为什么用 Pydantic？

Pydantic 用 Python 类型提示做**运行时数据校验**：

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

# 自动校验
user = User(name="Alice", age=30)  # OK
user = User(name="Alice", age="abc")  # ValidationError
```

**对比 dataclass**（详见 [dataclass](../01-fundamentals/26-dataclasses.md)）：

| 维度 | dataclass | Pydantic BaseModel |
|------|-----------|-------------------|
| 校验 | 无 | 自动 |
| 序列化 | 无 | `.model_dump()` / `.model_dump_json()` |
| 类型转换 | 无 | 自动（`"30"` → `30`） |
| JSON 解析 | 无 | `.model_validate_json()` |
| 性能 | 更快 | 较慢（Rust 实现已大幅提升） |

### 1.2 字段类型全景

Pydantic 支持 Python 几乎所有类型：

```python
from typing import Optional, List, Dict, Set, Tuple
from pydantic import BaseModel, Field

class Article(BaseModel):
    # 基础类型
    title: str
    views: int
    rating: float
    is_published: bool

    # 可选类型
    description: str | None = None  # 推荐写法
    # description: Optional[str] = None  # 等价写法

    # 容器类型
    tags: list[str] = []  # 推荐写法
    metadata: dict[str, str] = {}
    unique_ids: set[int] = set()

    # 嵌套模型
    author: User

    # 字面量类型
    status: Literal["draft", "published", "archived"] = "draft"

    # 数字约束
    age: int = Field(ge=0, le=150)
    name: str = Field(min_length=1, max_length=100)

    # 字符串约束
    email: str = Field(pattern=r"^[\w.-]+@[\w.-]+$")
```

### 1.3 dify 中的 Pydantic 模型

dify 用 Pydantic v2 定义**所有 DTO**：
- **请求/响应**：`controllers/console/app/app.py`
- **领域对象**：`core/app/entities/app_invoke_entities.py`
- **事件数据**：`core/app/entities/queue_entities.py`
- **任务状态**：`core/app/entities/task_entities.py`

## 2. 代码示例

### 2.1 基础 BaseModel

```python
from pydantic import BaseModel, Field
from datetime import datetime

class User(BaseModel):
    id: str
    name: str
    email: str
    age: int = 0  # 默认值
    created_at: datetime = Field(default_factory=datetime.now)  # 工厂函数默认值

# 创建实例
user = User(id="u001", name="Alice", email="a@b.com")
print(user.name)  # "Alice"

# 自动类型转换
user2 = User(id="u002", name="Bob", email="b@c.com", age="30")
print(user2.age)  # 30（自动转 int）

# 校验失败
try:
    User(id="u003", name="Carol", email="c@d.com", age="not_a_number")
except ValidationError as e:
    print(e.errors())
```

### 2.2 嵌套模型

```python
class Address(BaseModel):
    street: str
    city: str
    country: str = "China"


class Company(BaseModel):
    name: str
    headquarters: Address
    branches: list[Address] = []


company = Company(
    name="Dify",
    headquarters=Address(street="123 Main St", city="Beijing"),
    branches=[
        Address(street="456 Park Ave", city="Shanghai"),
    ],
)
print(company.headquarters.city)  # "Beijing"
print(company.branches[0].city)  # "Shanghai"
```

### 2.3 序列化与反序列化

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

user = User(name="Alice", age=30)

# 序列化为 dict
data = user.model_dump()  # {"name": "Alice", "age": 30}

# 序列化为 JSON 字符串
json_str = user.model_dump_json()  # '{"name":"Alice","age":30}'

# 从 dict 反序列化
user2 = User.model_validate(data)  # User(name='Alice', age=30)

# 从 JSON 反序列化
user3 = User.model_validate_json(json_str)  # User(name='Alice', age=30)

# 排除字段
data = user.model_dump(exclude={"age"})  # {"name": "Alice"}

# 仅包含字段
data = user.model_dump(include={"name"})  # {"name": "Alice"}
```

### 2.4 字段别名（alias）

```python
from pydantic import BaseModel, Field

class APIRequest(BaseModel):
    user_id: str = Field(alias="userId")  # 外部字段名 userId，内部 user_id

# 反序列化：接受 userId
req = APIRequest.model_validate({"userId": "u001"})
print(req.user_id)  # "u001"

# 序列化：输出 userId
print(req.model_dump(by_alias=True))  # {"userId": "u001"}
print(req.model_dump())  # {"user_id": "u001"}（默认用 Python 字段名）
```

### 2.5 常见错误：可变默认值

```python
# ❌ 错误：可变默认值（所有实例共享同一个 list）
class BadUser(BaseModel):
    tags: list[str] = []  # 实际上 Pydantic 会拷贝，但 dataclass 会共享

# ✅ 正确：用 Field(default_factory=...)
class GoodUser(BaseModel):
    tags: list[str] = Field(default_factory=list)
```

## 3. 关键要点总结

- Pydantic v2 用 Rust 实现，性能大幅提升
- `BaseModel` 提供**自动校验**、**类型转换**、**序列化/反序列化**
- 字段约束：`Field(default, ge, le, min_length, max_length, pattern)`
- 可变默认值必须用 `Field(default_factory=...)`
- dify 中所有 DTO、领域对象、事件都用 Pydantic 定义
- `ConfigDict(arbitrary_types_allowed=True)` 允许任意类型字段
- `field_validator` 用 mode="before"/"after" 控制校验时机

---

**文档版本**：v1.0
**最后更新**：2026-07-13
