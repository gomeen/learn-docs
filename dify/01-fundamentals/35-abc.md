# 1.1.19 抽象基类（abc 模块）

> 理解 Python 抽象基类（ABC）的用法，能看懂 dify 中所有继承 `ABC` 的接口设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 `ABC` 与 `ABCMeta` 的关系
- 用 `@abstractmethod` 定义抽象方法，强制子类实现
- 理解 `register` 虚子类的用法（适配类型检查）
- 在 dify 中识别所有 ABC 接口（如 `Tool`、`DatasourcePlugin`、`BaseVector`）

## 📚 前置知识

- Python 基础：类的继承、方法重写
- 01-fundamentals/03-classes-basics.md（类基础）
- 01-fundamentals/33-metaclass.md（元类，推荐了解）

## 1. 核心概念

### 1.1 为什么需要抽象基类

普通继承约定「子类必须实现父类的方法」是**文档层面的**——Python 不会强制检查。抽象基类（Abstract Base Class，ABC）通过 `@abstractmethod` 装饰器**强制**子类实现这些方法，否则实例化时直接报错。

**举例**：你想定义 `Tool` 接口规范，让所有工具（Google 搜索、天气查询、HTTP 请求）都必须实现 `invoke` 方法。

```python
# 没有 ABC：约定俗成，不强制
class Tool:
    def invoke(self):
        raise NotImplementedError
```

```python
# 有 ABC：强制子类必须实现
from abc import ABC, abstractmethod

class Tool(ABC):
    @abstractmethod
    def invoke(self):
        ...

class GoogleSearchTool(Tool):
    pass  # 没有实现 invoke

GoogleSearchTool()  # TypeError: Can't instantiate abstract class GoogleSearchTool
```

### 1.2 `ABC` 的本质

`ABC` 是一个**辅助类**，它的元类是 `ABCMeta`（元类原理见 [33-metaclass](./33-metaclass.md)）：

```python
from abc import ABC, ABCMeta

# 这两种写法等价
class Foo(ABC): pass
class Foo(metaclass=ABCMeta): pass
```

`ABCMeta` 的作用：在类创建时扫描所有 `@abstractmethod` 标记的方法。如果一个类含有未实现的抽象方法，调用 `cls(...)` 实例化时会抛出 `TypeError`。

### 1.3 `@abstractmethod` 的特性

被 `@abstractmethod` 装饰的方法可以**有实现**（提供默认行为），子类可以选择性重写。但只要有一个抽象方法没实现，类就不能实例化。

```python
from abc import ABC, abstractmethod

class Animal(ABC):
    @abstractmethod
    def speak(self):
        return "..."  # 默认实现，子类可覆盖

    @abstractmethod
    def move(self):
        ...

class Dog(Animal):
    # 实现了 move，但 speak 用了父类的默认实现
    def move(self):
        return "running"

Dog()  # 可以实例化（所有抽象方法都被实现了）
```

### 1.4 抽象属性

```python
from abc import ABC, abstractmethod

class Config(ABC):
    @property
    @abstractmethod
    def api_key(self) -> str:
        ...

class MyConfig(Config):
    @property
    def api_key(self) -> str:
        return "sk-xxx"

MyConfig()  # OK
```

> `@abstractmethod` 必须放在 `@property` **下面**才能正确地标记为抽象属性（`@property` 见 [10-decorator](./10-decorator.md) / [34-descriptor](./34-descriptor.md)）。

### 1.5 虚子类（Virtual Subclass）

有时两个类没有继承关系，但在语义上是「同类」，可以用 `register` 让它们互相兼容 `isinstance` 检查：

```python
from abc import ABC

class Drawable(ABC):
    pass

class MyClass:
    pass

Drawable.register(MyClass)
print(isinstance(MyClass(), Drawable))  # True（但没有真正的继承关系）
```

> dify 中较少使用 `register`，但 Pydantic / SQLAlchemy 内部用得很多。

## 2. 代码示例

### 2.1 基础 ABC 接口

```python
from abc import ABC, abstractmethod

class Storage(ABC):
    """统一的存储接口，dify 的 FileService 也有类似设计。"""
    @abstractmethod
    def save(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def load(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

class S3Storage(Storage):
    def save(self, key, data):
        print(f"upload to S3: {key}")

    def load(self, key):
        return b"data"

    def delete(self, key):
        print(f"delete from S3: {key}")

s = S3Storage()
s.save("test.txt", b"hello")
```

### 2.2 抽象方法 + 默认实现

```python
from abc import ABC, abstractmethod

class BaseRetriever(ABC):
    def retrieve(self, query: str) -> list[str]:
        """模板方法：固定流程，子类只关心 query → docs 的核心逻辑。"""
        docs = self._fetch(query)             # 抽象
        return self._post_process(docs)        # 默认实现

    @abstractmethod
    def _fetch(self, query: str) -> list[str]:
        ...

    def _post_process(self, docs):
        return [d.strip() for d in docs]       # 默认实现

class KeywordRetriever(BaseRetriever):
    def _fetch(self, query):
        return ["doc about " + query]
```

### 2.3 常见错误：抽象方法顺序写错

```python
from abc import ABC, abstractmethod

# ❌ 错误：abstractmethod 在 property 上方
class Foo(ABC):
    @abstractmethod
    @property
    def x(self): ...     # 实际只标记 x 为 property，不是抽象属性
```

```python
# ✅ 正确：property 在外层，abstractmethod 在内层
class Foo(ABC):
    @property
    @abstractmethod
    def x(self): ...
```

## 3. dify 仓库源码解读

### 3.1 `Tool` 抽象基类

**文件位置**：`/Users/xu/code/github/dify/api/core/tools/__base/tool.py`
**核心代码**（行 1-50）：

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

if TYPE_CHECKING:  # pragma: no cover
    from models.model import File

from core.tools.__base.tool_runtime import ToolRuntime
from core.tools.entities.tool_entities import (
    ToolEntity,
    ToolInvokeMessage,
    ToolParameter,
    ToolProviderType,
)


class Tool(ABC):
    """
    The base class of a tool
    """

    def __init__(self, entity: ToolEntity, runtime: ToolRuntime):
        self.entity = entity
        self.runtime = runtime

    def fork_tool_runtime(self, runtime: ToolRuntime) -> Tool:
        """
        fork a new tool with metadata
        :return: the new tool
        """
        return self.__class__(
            entity=self.entity.model_copy(),
            runtime=runtime,
        )

    @abstractmethod
    def tool_provider_type(self) -> ToolProviderType:
        """
        get the tool provider type

        :return: the tool provider type
        """
```

**解读**：
- 第 3 行：`from abc import ABC, abstractmethod`
- 第 22 行：`class Tool(ABC)`——所有 dify 工具（Google Search、Slack、HTTP 请求等）的根接口
- 第 41 行：`@abstractmethod` 标记的 `tool_provider_type` 必须由子类实现，否则 `Tool()` 实例化会失败
- **设计意图**：dify 通过 ABC 强制所有第三方工具实现统一接口，保证 `ToolManager` 能用统一方式调度它们

### 3.2 `DatasourcePlugin` 抽象基类

**文件位置**：`/Users/xu/code/github/dify/api/core/datasource/__base/datasource_plugin.py`
**核心代码**（行 1-44）：

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from configs import dify_config
from core.datasource.__base.datasource_runtime import DatasourceRuntime
from core.datasource.entities.datasource_entities import (
    DatasourceEntity,
    DatasourceProviderType,
)


class DatasourcePlugin(ABC):
    entity: DatasourceEntity
    runtime: DatasourceRuntime
    icon: str

    def __init__(
        self,
        entity: DatasourceEntity,
        runtime: DatasourceRuntime,
        icon: str,
    ) -> None:
        self.entity = entity
        self.runtime = runtime
        self.icon = icon

    @abstractmethod
    def datasource_provider_type(self) -> str:
        """
        returns the type of the datasource provider
        """
        return DatasourceProviderType.LOCAL_FILE

    def fork_datasource_runtime(self, runtime: DatasourceRuntime) -> DatasourcePlugin:
        return self.__class__(
            entity=self.entity.model_copy(),
            runtime=runtime,
            icon=self.icon,
        )

    def get_icon_url(self, tenant_id: str) -> str:
        return f"{dify_config.CONSOLE_API_URL}/console/api/workspaces/current/plugin/icon?tenant_id={tenant_id}&filename={self.icon}"  # noqa: E501
```

**解读**：
- 第 13 行：`DatasourcePlugin(ABC)`——所有数据源插件（Notion、Slack、网页）的统一基类
- 第 28-33 行：`@abstractmethod` 标记的 `datasource_provider_type` 必须实现
- 第 35-40 行：`fork_datasource_runtime` 是**非抽象方法**，提供默认的 fork 实现，子类可以直接继承
- **整体设计**：ABC 提供「契约」（必须实现什么），普通方法提供「复用」（已经做好的部分）。这种模板方法模式在 dify 中极其常见

## 4. 关键要点总结

- `ABC` 是 `ABCMeta` 元类的辅助类，用于声明抽象基类
- `@abstractmethod` 装饰的方法**必须**被子类实现，否则 `cls()` 实例化报错
- 抽象方法可以提供默认实现，子类选择性重写
- `@property` + `@abstractmethod` 组合声明抽象属性（property 在外层）
- `register()` 用于虚子类（`isinstance` 通过，但无实际继承关系）
- **dify 大量使用 ABC**：Tool、DatasourcePlugin、BaseVector、IndexProcessorBase 等

## 5. 练习题

### 练习 1：基础（必做）

定义一个 `Notifier(ABC)`，包含抽象方法 `send(message: str)`，并实现两个子类：`EmailNotifier`、`SlackNotifier`。

```python
from abc import ABC, abstractmethod

class Notifier(ABC):
    @abstractmethod
    def send(self, message: str) -> None: ...

class EmailNotifier(Notifier):
    # TODO: 打印 "[email] sent: <message>"
    ...

class SlackNotifier(Notifier):
    # TODO: 打印 "[slack] sent: <message>"
    ...

for n in [EmailNotifier(), SlackNotifier()]:
    n.send("Hello!")
```

### 练习 2：进阶

阅读 `api/core/rag/datasource/vdb/vector_base.py`，找到 `BaseVector` ABC 的所有 `@abstractmethod`，并画出 dify 的向量数据库（如 Qdrant、Weaviate、Chroma）是如何继承它的。

### 练习 3：挑战（选做）

为练习 1 添加一个 `template` 方法 `notify_all(notifiers: list[Notifier], msg: str)`，要求遍历所有 notifier 调用 send，并捕获异常但不中断。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/tools/__base/tool.py`
- `/Users/xu/code/github/dify/api/core/datasource/__base/datasource_plugin.py`
- Python 官方文档 abc：https://docs.python.org/3/library/abc.html
- Real Python ABC 教程：https://realpython.com/python-abc/

---

**文档版本**：v1.0
**最后更新**：2026-07-13