# 1.1.8 `TypedDict` 与 `NotRequired`：结构化字典

> 掌握用 `TypedDict` 给字典加上"形状"，既保留 dict 的灵活性，又获得类型安全。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `TypedDict` 与普通 `dict` 的区别
- 使用 `TypedDict` 为复杂 JSON / 配置定义类型
- 用 `NotRequired` 标记可选字段
- 识别 dify 中"实体类"的常见模式

## 📚 前置知识

- 01-fundamentals/01-python-typing-basics.md
- Python 基础：字典、类

## 1. 核心概念

### 1.1 为什么需要 `TypedDict`？

普通 `dict[str, Any]` 没有形状约束：

```python
def create_user(data: dict[str, Any]) -> None:
    print(data["name"])  # IDE 不知道是否有 "name"
```

`TypedDict` 给 dict 定义**键名与值类型**，让 IDE 和 mypy 能检查键名拼写错误。

### 1.2 基本语法

```python
from typing import TypedDict

class UserDict(TypedDict):
    id: int
    name: str
    email: str

# 使用
user: UserDict = {"id": 1, "name": "Alice", "email": "a@b.com"}

# 类型检查通过
print(user["name"])  # IDE 知道是 str
```

### 1.3 可选字段：`NotRequired` / `total=False`

两种方式声明"某些字段可以缺失"：

```python
from typing import TypedDict, NotRequired

# 方式 1：NotRequired（Python 3.11+，推荐）
class UserOptional(TypedDict):
    id: int
    name: str
    email: NotRequired[str]  # 可以省略
    age: NotRequired[int]

# 方式 2：total=False（所有字段都可选）
class UserPartial(TypedDict):
    id: int
    name: str
    email: str
```

### 1.4 `TypedDict` vs `dataclass` vs `Pydantic BaseModel`

| 特性 | TypedDict | dataclass | Pydantic |
|---|---|---|---|
| 运行时验证 | 无 | 无 | 有 |
| 类型提示 | 有 | 有 | 有 |
| 性能开销 | 零 | 零 | 有（验证） |
| 序列化支持 | 需手动 | 需手动 | 内置 |
| 适用场景 | 配置/JSON 传递 | 内部数据模型 | API 入参/出参 |

**dify 中常见模式**：
- **TypedDict**：节点配置、跨层数据传输
- **dataclass**（详见 [36-dataclasses](./36-dataclasses.md)）：简单数据容器
- **Pydantic**：API Schema、外部数据验证

## 2. 代码示例

### 2.1 基础用法

```python
from typing import TypedDict, NotRequired

class ApiResponse(TypedDict):
    code: int
    message: str
    data: NotRequired[dict]  # 错误响应时可能没有 data

def handle_response(resp: ApiResponse) -> str:
    if resp["code"] == 0:
        # mypy 知道 data 字段存在但需要运行时检查
        return f"Success: {resp.get('data', {})}"
    return f"Error: {resp['message']}"
```

### 2.2 嵌套 `TypedDict`

```python
from typing import TypedDict, NotRequired

class Address(TypedDict):
    city: str
    country: str

class UserProfile(TypedDict):
    id: int
    name: str
    address: Address               # 嵌套另一个 TypedDict
    tags: list[str]
    metadata: NotRequired[dict[str, str]]  # 嵌套 dict

def print_address(user: UserProfile) -> None:
    addr = user["address"]
    print(f"{user['name']} lives in {addr['city']}, {addr['country']}")
```

### 2.3 常见错误：当作类实例化

```python
# ❌ 错误：TypedDict 不是类，不能实例化
user = UserDict(id=1, name="Alice")  # 运行时不会校验

# ✅ 正确：当成 dict 字面量
user: UserDict = {"id": 1, "name": "Alice"}
```

## 3. dify 仓库源码解读

### 3.1 节点配置：`HttpRequestNodeConfig`

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/http_request/entities.py`
**核心代码**（行 1-40）：

```python
from typing import Any, NotRequired, TypedDict

class HttpRequestNodeConfig(TypedDict):
    """HTTP 请求节点的配置。"""
    id: str
    tenant_id: str
    app_id: str
    workflow_id: NotRequired[str]

class HttpRequestNodeData(TypedDict):
    """HTTP 请求节点的运行时数据。"""
    title: str
    desc: NotRequired[str]
    url: str
    method: str
    headers: list[dict[str, str]]
    params: NotRequired[dict[str, str]]
    body: NotRequired[dict[str, Any]]
    timeout: NotRequired[int]
```

**解读**：
- 第 6-10 行：`HttpRequestNodeConfig` 描述节点的**身份信息**（id、tenant_id 等）
- 第 12-21 行：`HttpRequestNodeData` 描述节点的**业务数据**（url、method 等）
- `NotRequired` 用于"老数据可能没有该字段"的兼容场景
- **整体设计意图**：用 TypedDict 而非 Pydantic，因为这些 dict 来自数据库 JSON 字段，不需要重复验证

### 3.2 实体类的整体组织

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/http_request/entities.py`
**核心代码**（行 1-30）：

```python
from collections.abc import Mapping
from typing import Any, NotRequired, TypedDict

from core.workflow.nodes.base.entities import BaseNodeData

class HttpRequestNodeData(BaseNodeData):
    """继承自 BaseNodeData，所有节点共享基础字段。"""
    method: str
    url: str
    authorization: NotRequired[dict[str, Any]]
    headers: str
    params: str
    body: NotRequired[dict[str, Any]]
    timeout: NotRequired[Mapping[str, int]]
```

**解读**：
- 第 8 行：继承自 `BaseNodeData`，复用通用字段（title、desc 等）
- 第 12 行：`Mapping[str, int]` 表示只读映射，比 `dict` 更宽松
- **关键设计**：通过 TypedDict 继承形成"节点配置 schema 体系"，便于校验和 IDE 跳转

## 4. 关键要点总结

- `TypedDict` 给字典加上"形状"，**运行时零开销**
- 用 `NotRequired[K]`（Python 3.11+）或 `total=False` 标记可选字段
- `TypedDict` 不是类，不能实例化，只能用 dict 字面量赋值
- dify 中常用于：节点配置、数据库 JSON 字段、跨层数据传输
- 不需要运行时验证时优先 `TypedDict`，需要验证时用 Pydantic

## 5. 练习题

### 练习 1：基础（必做）

定义一个 `WorkflowRunDict` 类型，包含字段：`id` (str)、`status` (str)、`inputs` (dict)、`outputs` (NotRequired[dict])、`created_at` (int)。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/workflow/nodes/http_request/entities.py`，列出所有 TypedDict 类，并画图表示它们的继承关系。

### 练习 3：挑战（选做）

定义一个嵌套 TypedDict `ChatCompletionRequest`，包含 `model` (str)、`messages` (list[MessageDict])、`temperature` (NotRequired[float])。再定义 `MessageDict` 包含 `role` (Literal["user","assistant","system"]) 和 `content` (str)。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/http_request/entities.py`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/base/entities.py`
- Python 官方文档：https://docs.python.org/3/library/typing.html#typing.TypedDict
- PEP 655（NotRequired）：https://peps.python.org/pep-0655/

---

**文档版本**：v1.0
**最后更新**：2026-07-13