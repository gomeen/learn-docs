# 1.2.1 JSON 处理：序列化、反序列化、嵌套结构

> 掌握 Python 标准库 `json` 的使用，能处理嵌套 JSON、自定义对象序列化、特殊类型转换。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练使用 `json.dumps` / `json.loads` / `json.dump` / `json.load`
- 处理 JSON 中的特殊类型（datetime、UUID、Decimal）
- 自定义 JSONEncoder 处理复杂对象
- 在 dify 中识别 JSON 处理模式

## 📚 前置知识

- Python 基础：字典、列表、字符串
- 01-fundamentals/07-python-typing-basics.md

## 1. 核心概念

### 1.1 JSON 基础：四种操作

```python
import json

# Python 对象 → JSON 字符串
data = {"name": "Alice", "age": 30}
s = json.dumps(data)            # '{"name": "Alice", "age": 30}'

# JSON 字符串 → Python 对象
obj = json.loads(s)             # {"name": "Alice", "age": 30}

# Python 对象 → JSON 文件
with open("/tmp/data.json", "w") as f:
    json.dump(data, f)

# JSON 文件 → Python 对象
with open("/tmp/data.json") as f:
    obj = json.load(f)
```

### 1.2 JSON 与 Python 类型映射

| JSON | Python |
|---|---|
| object | dict |
| array | list |
| string | str |
| number | int / float |
| true / false | True / False |
| null | None |

### 1.3 格式化输出：`indent` 与 `ensure_ascii`

```python
import json

data = {"name": "张三", "items": [1, 2, 3]}

# 紧凑（一行）
print(json.dumps(data))
# {"name": "张三", "items": [1, 2, 3]}

# 格式化（多行 + 中文）
print(json.dumps(data, indent=2, ensure_ascii=False))
# {
#   "name": "张三",
#   "items": [1, 2, 3]
# }
```

### 1.4 特殊类型的序列化

`json.dumps` 默认**不支持** `datetime`、`UUID`、`Decimal`、`set`：

```python
import json
from datetime import datetime

data = {"created_at": datetime.now()}
json.dumps(data)
# TypeError: Object of type datetime is not JSON serializable
```

**解决方式**：

```python
# 方式 1：先用 str() 转换
data_str = {k: str(v) for k, v in data.items()}

# 方式 2：自定义 default 函数
def default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

json.dumps(data, default=default)

# 方式 3：自定义 JSONEncoder
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

json.dumps(data, cls=CustomEncoder)
```

## 2. 代码示例

### 2.1 嵌套结构处理

```python
import json

# 嵌套 JSON（API 响应常见）
response = """
{
    "code": 0,
    "data": {
        "user": {
            "id": 1,
            "name": "Alice",
            "tags": ["admin", "vip"]
        },
        "stats": {
            "total": 100,
            "passed": 80
        }
    }
}
"""

resp = json.loads(response)

# 安全访问嵌套字段（防止 KeyError）
code = resp["code"]
user_name = resp["data"]["user"]["name"]
first_tag = resp["data"]["user"]["tags"][0]

# 用 .get() 安全访问
desc = resp.get("data", {}).get("user", {}).get("desc", "")
```

### 2.2 处理 datetime / UUID

```python
import json
from datetime import datetime
from uuid import UUID

class AppJSONEncoder(json.JSONEncoder):
    """dify 风格的 JSON 编码器。"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()  # "2026-07-13T10:30:00"
        if isinstance(obj, UUID):
            return str(obj)        # "550e8400-e29b-41d4-a716-446655440000"
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)

data = {
    "id": UUID("550e8400-e29b-41d4-a716-446655440000"),
    "created_at": datetime.now(),
    "tags": {"a", "b"},
}
print(json.dumps(data, cls=AppJSONEncoder))
# {"id": "550e8400-e29b-41d4-a716-446655440000", "created_at": "...", "tags": ["a", "b"]}
```

### 2.3 常见错误：忘记 `ensure_ascii=False`

```python
# ❌ 中文被转义成 \u 序列
json.dumps({"name": "张三"})
# '{"name": "\\u5f20\\u4e09"}'

# ✅ 保留中文
json.dumps({"name": "张三"}, ensure_ascii=False)
# '{"name": "张三"}'
```

## 3. dify 仓库源码解读

### 3.1 工作流触发日志的 JSON 序列化

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 110-130）：

```python
# 6. Create trigger log entry first (for tracking)
trigger_log = WorkflowTriggerLog(
    tenant_id=trigger_data.tenant_id,
    app_id=trigger_data.app_id,
    workflow_id=workflow.id,
    root_node_id=trigger_data.root_node_id,
    trigger_metadata=(
        trigger_data.trigger_metadata.model_dump_json() if trigger_data.trigger_metadata else "{}"
    ),
    trigger_type=trigger_data.trigger_type,
    workflow_run_id=None,
    outputs=None,
    trigger_data=trigger_data.model_dump_json(),
    inputs=json.dumps(dict(trigger_data.inputs)),
    status=WorkflowTriggerStatus.PENDING,
    queue_name=dispatcher.get_queue_name(),
    retry_count=0,
    created_by_role=created_by_role,
    created_by=created_by,
    celery_task_id=None,
    error=None,
    elapsed_time=None,
    total_tokens=None,
)
```

**解读**：
- 第 8 行：`trigger_metadata.model_dump_json()`——Pydantic 模型直接序列化
- 第 14 行：`json.dumps(dict(trigger_data.inputs))`——把 inputs 字典转 JSON 字符串存入数据库
- **关键设计**：数据库列存 JSON 字符串（Text 类型），查询时再 `json.loads()` 反序列化——灵活但牺牲部分查询性能

### 3.2 工作流响应序列化

**文件位置**：`/Users/xu/code/github/dify/api/services/workflow/entities.py`
**核心代码**（行 1-30）：

```python
import json
from typing import Any

from pydantic import BaseModel, Field

class AsyncTriggerResponse(BaseModel):
    """异步触发工作流的响应。"""
    workflow_trigger_log_id: str
    task_id: str
    status: str
    queue: str

    def to_json(self) -> str:
        return self.model_dump_json()
```

**解读**：
- 第 13 行：`to_json()` 委托给 Pydantic 的 `model_dump_json()`
- **关键设计**：dify 用 Pydantic 处理所有 API 序列化，自动处理 datetime / UUID / Enum 等类型

## 4. 关键要点总结

- 四个函数：`dumps`/`loads`（字符串）、`dump`/`load`（文件）
- 设置 `ensure_ascii=False` 保留中文
- `indent=N` 格式化输出（调试日志时有用）
- 默认不支持 `datetime` / `UUID` / `Decimal` / `set`，需要自定义 `default` 函数或 `JSONEncoder`
- dify 中**统一使用 Pydantic** 处理 API 序列化，标准库 `json` 用于底层 JSON 字段存取

## 5. 练习题

### 练习 1：基础（必做）

将下面 Python 对象序列化为 JSON：包含 datetime、UUID、set 三种类型，要求都能正确序列化（提示：用自定义 `default`）。

```python
data = {
    "id": UUID("550e8400-e29b-41d4-a716-446655440000"),
    "created_at": datetime.now(),
    "tags": {"python", "dify"},
}
```

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/services/async_workflow_service.py` 中的 `trigger_log` 构造，理解 dify 中"把整个数据对象 JSON 化存到数据库列"的设计意图。这种做法的优缺点是什么？

### 练习 3：挑战（选做）

实现一个 `JSONDiff` 工具类：给定两个 JSON 对象（dict），输出"路径 + 操作"的差异列表。例：`{"a": 1, "b": {"c": 2}}` vs `{"a": 1, "b": {"c": 3}}` 输出 `[("b.c", "modify", 2, 3)]`。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`
- `/Users/xu/code/github/dify/api/services/workflow/entities.py`
- Python 官方文档：https://docs.python.org/3/library/json.html
- Pydantic 序列化：https://docs.pydantic.dev/latest/concepts/serialization/

---

**文档版本**：v1.0
**最后更新**：2026-07-13