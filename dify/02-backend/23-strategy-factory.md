# 2.4.4 策略模式与工厂模式

> 理解策略模式（Strategy）和工厂模式（Factory）的差异，掌握 dify 中的实际应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握策略模式和工厂模式的核心差异
- 在 dify 中找到工厂（`DifyNodeFactory`、`AgentFactory`、`ModerationFactory`）
- 在 dify 中找到策略（`SimplePromptTransform`、`AdvancedPromptTransform`）
- 设计可扩展的多算法/多实现系统

## 📚 前置知识

- [适配器模式](./22-adapter-pattern.md)
- [分层架构](./02-layered-architecture.md)
- Python 类继承基础
- 经典策略 / 工厂方法（详见 [策略](../../_fundamentals/06-design-patterns/13-strategy.md)、[工厂方法](../../_fundamentals/06-design-patterns/02-factory-method.md)）

## 1. 核心概念

### 1.1 策略模式 vs 工厂模式

| 维度 | 策略模式 | 工厂模式 |
|------|---------|---------|
| **目的** | 封装**算法**，运行时切换 | 封装**对象创建**，隐藏构造细节 |
| **关注点** | "怎么做"（HOW） | "创建什么"（WHAT） |
| **典型方法** | `strategy.execute()` | `factory.create(type)` |
| **dify 例子** | `SimplePromptTransform` / `AdvancedPromptTransform` | `DifyNodeFactory` / `ModerationFactory` |

### 1.2 策略模式

**核心思想**：把可变的算法封装成独立的对象，可以互相替换（本篇讲 dify 落地；经典定义详见前置中的 [策略](../../_fundamentals/06-design-patterns/13-strategy.md)）。

```python
# 业务场景：定价策略（ABC 详见 [抽象基类 ABC](../01-fundamentals/35-abc.md)）
class PricingStrategy(ABC):
    def calculate(self, order): ...

class VIPPricing(PricingStrategy): ...  # VIP 8 折
class NormalPricing(PricingStrategy): ...  # 无折扣
class SeasonalPricing(PricingStrategy): ...  # 季节性折扣
```

### 1.3 工厂模式

**核心思想**：把对象创建封装到一个方法中，调用方不直接 `new`。

```python
# 业务场景：根据 type 创建不同节点
class NodeFactory:
    def create(self, node_type: str, config: dict) -> Node:
        if node_type == "llm": return LLMNode(config)
        if node_type == "code": return CodeNode(config)
        ...
```

### 1.4 dify 的实际应用

dify 同时使用两种模式：

- **工厂**：`DifyNodeFactory`、`ModerationFactory`、`AgentFactory`、`VariableFactory`
- **策略**：`SimplePromptTransform` vs `AdvancedPromptTransform`、`InputModeration` vs `OutputModeration`

## 2. 代码示例

### 2.1 策略模式

```python
from abc import ABC, abstractmethod
from typing import Protocol


# 策略接口
class CompressionStrategy(Protocol):
    """压缩策略接口。"""
    def compress(self, data: bytes) -> bytes: ...


# 具体策略
class GzipCompression:
    def compress(self, data: bytes) -> bytes:
        import gzip
        return gzip.compress(data)


class ZstdCompression:
    def compress(self, data: bytes) -> bytes:
        import zstandard
        return zstandard.compress(data)


class NoCompression:
    """不压缩（用于已经压缩过的格式如 JPEG）。"""
    def compress(self, data: bytes) -> bytes:
        return data


# 上下文（使用策略的对象）
class FileStorage:
    def __init__(self, strategy: CompressionStrategy):
        self._strategy = strategy

    def save(self, name: str, data: bytes):
        compressed = self._strategy.compress(data)
        # ... 保存压缩后的数据
        return len(compressed)


# 使用：可以运行时切换策略
storage = FileStorage(strategy=GzipCompression())
storage.save("file.txt", b"hello world" * 100)

storage = FileStorage(strategy=ZstdCompression())  # 切换策略
storage.save("file.txt", b"hello world" * 100)
```

### 2.2 工厂模式

```python
from abc import ABC, abstractmethod


# 产品接口
class NotificationChannel(ABC):
    @abstractmethod
    def send(self, message: str): ...


# 具体产品
class EmailChannel(NotificationChannel):
    def send(self, message: str):
        print(f"[Email] {message}")


class SMSChannel(NotificationChannel):
    def send(self, message: str):
        print(f"[SMS] {message}")


class PushChannel(NotificationChannel):
    def send(self, message: str):
        print(f"[Push] {message}")


# 工厂
class NotificationFactory:
    """根据类型创建不同的通知渠道。"""

    _channels = {
        "email": EmailChannel,
        "sms": SMSChannel,
        "push": PushChannel,
    }

    @classmethod
    def create(cls, channel_type: str) -> NotificationChannel:
        if channel_type not in cls._channels:
            raise ValueError(f"Unknown channel: {channel_type}")
        return cls._channels[channel_type]()


# 使用
channel = NotificationFactory.create("email")  # 工厂创建
channel.send("Hello!")  # 统一接口调用
```

### 2.3 策略 + 工厂组合

```python
# 工厂根据配置选择策略
class CompressionFactory:
    _strategies = {
        "gzip": GzipCompression,
        "zstd": ZstdCompression,
        "none": NoCompression,
    }

    @classmethod
    def create(cls, strategy_type: str) -> CompressionStrategy:
        return cls._strategies[strategy_type]()


# 配置文件选择策略
import os
strategy_type = os.environ.get("COMPRESSION", "gzip")
strategy = CompressionFactory.create(strategy_type)

storage = FileStorage(strategy=strategy)
```

### 2.4 常见错误：工厂里写业务逻辑

```python
# ❌ 错误：工厂里混入业务逻辑
class BadFactory:
    @classmethod
    def create(cls, type: str):
        if type == "email":
            channel = EmailChannel()
            channel.set_signature("Company X")  # 业务逻辑
            channel.set_template("default")     # 业务逻辑
            return channel
        ...

# ✅ 正确：工厂只负责创建，对象初始化用 builder 或 __init__
class GoodFactory:
    @classmethod
    def create(cls, type: str, **kwargs) -> NotificationChannel:
        return cls._channels[type](**kwargs)

channel = GoodFactory.create("email", signature="Company X", template="default")
```

## 3. dify 仓库源码解读

### 3.1 工厂：`ModerationFactory`

**文件位置**：`/Users/xu/code/github/dify/api/core/moderation/factory.py`
**核心代码**（行 1-30）：

```python
from core.extension.extensible import ExtensionModule
from core.moderation.base import Moderation, ModerationInputsResult, ModerationOutputsResult
from extensions.ext_code_based_extension import code_based_extension


class ModerationFactory:
    """Moderation 工厂：从代码扩展系统加载具体的 Moderation 实现。"""

    def __init__(self, name: str, app_id: str, tenant_id: str, config: dict[str, Any]):
        extension_class = code_based_extension.extension_class(ExtensionModule.MODERATION, name)
        self.__extension_instance = extension_class(app_id, tenant_id, config)

    @classmethod
    def validate_config(cls, name: str, tenant_id: str, config: dict[str, Any]):
        """校验配置（不创建实例）。"""
        extension_class = code_based_extension.extension_class(ExtensionModule.MODERATION, name)
        extension_class.validate_config(tenant_id, config)
```

**解读**：
- 第 1-3 行：导入相关模块
- 第 7-13 行：`__init__` 通过扩展系统加载 Moderation 实现
- 第 15-20 行：`validate_config` 静态方法只校验配置不创建实例
- **特点**：工厂通过 `extension_class` 动态加载，符合"开放封闭原则"

### 3.2 工厂：`AgentFactory`

**文件位置**：`/Users/xu/code/github/dify/api/factories/agent_factory.py`
**核心代码**（行 1-15）：

```python
from core.agent.strategy.plugin import PluginAgentStrategy
from core.plugin.impl.agent import PluginAgentClient


def get_plugin_agent_strategy(
    tenant_id: str, agent_strategy_provider_name: str, agent_strategy_name: str
) -> PluginAgentStrategy:
    """从插件系统加载 Agent 策略。

    这是一个工厂函数：
    - 输入：tenant_id、provider_name、strategy_name
    - 输出：PluginAgentStrategy 实例
    - 调用方不需要知道 PluginAgentClient 的细节
    """
    manager = PluginAgentClient()
    agent_provider = manager.fetch_agent_strategy_provider(tenant_id, agent_strategy_provider_name)
    for agent_strategy in agent_provider.declaration.strategies:
        if agent_strategy.identity.name == agent_strategy_name:
            return PluginAgentStrategy(tenant_id, agent_strategy, agent_provider.meta.version)

    raise ValueError(f"Agent strategy {agent_strategy_name} not found")
```

**解读**：
- 第 8-12 行：函数式工厂——根据名字返回具体策略
- 第 13-15 行：找不到时抛 `ValueError`
- **模式**：dify 用纯函数而非类实现工厂（更 Pythonic）

### 3.3 工厂：`DifyNodeFactory`

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/node_factory.py`
**核心代码**（节选）：

```python
class DifyNodeFactory:
    """节点工厂：根据 node_type 创建对应的 Node 实例。"""

    def create_node(self, node_config: NodeConfigDict, ...) -> Node:
        """工厂方法：根据配置创建不同类型的节点。"""
        node_type = node_config.get("data", {}).get("type")
        if node_type == "start":
            return StartNode(...)
        elif node_type == "llm":
            return LLMNode(...)
        elif node_type == "code":
            return CodeNode(...)
        # ... 20+ 种节点
        else:
            raise ValueError(f"Unknown node type: {node_type}")


def get_node_type_classes_mapping() -> Mapping[str, type[Node]]:
    """获取所有节点类型到类的映射（用于自动注册）。"""
    return _NODE_TYPE_CLASSES_MAPPING
```

**解读**：
- 第 4-15 行：`create_node` 是核心工厂方法
- 第 6-13 行：if/elif 链决定创建哪种节点
- 第 19-22 行：`get_node_type_classes_mapping` 提供类型→类的全局映射
- **演进**：从 if/elif 链到全局映射，difable 后续可能改为注册表模式

### 3.4 策略：`SimplePromptTransform` vs `AdvancedPromptTransform`

**文件位置**：`/Users/xu/code/github/dify/api/core/prompt/simple_prompt_transform.py`
**核心代码**（节选）：

```python
class SimplePromptTransform:
    """简单提示词转换策略：

    把 prompt template + inputs 转换为模型的 messages 列表。
    支持 chat / completion 两种模式。
    """
    def get_prompt(self) -> list:
        if self.model_mode == ModelMode.CHAT:
            return self._get_chat_prompt()
        elif self.model_mode == ModelMode.COMPLETION:
            return self._get_completion_prompt()


class AdvancedPromptTransform:
    """高级提示词转换策略：

    支持：
    - 上下文管理（TokenBufferMemory）
    - 工具调用
    - 多模态（图片、文件）
    - 历史对话
    """
    def get_prompt(self) -> list:
        # 更复杂的转换逻辑
        # 包含记忆、工具、多模态处理
        ...
```

**解读**：
- **策略对比**：
  - `SimplePromptTransform`：只处理简单的 template + inputs
  - `AdvancedPromptTransform`：处理复杂场景（记忆、工具、多模态）
- **选择策略**：根据 app.mode（chat / advanced-chat / agent）选择不同策略
- **典型应用**：dify 的 app 有不同复杂度，需要不同的 prompt 转换策略

## 4. 关键要点总结

- **策略模式**：封装可互换的算法（如 `SimplePromptTransform` vs `AdvancedPromptTransform`）
- **工厂模式**：封装对象创建（如 `DifyNodeFactory`、`AgentFactory`、`ModerationFactory`）
- **策略 vs 工厂**：策略关注"怎么做"，工厂关注"创建什么"
- dify 用**纯函数工厂**（`get_plugin_agent_strategy`）和**类工厂**（`DifyNodeFactory`）两种风格
- dify 用 `extension_class()` **动态加载**机制（开放封闭原则）
- **组合使用**：工厂创建策略对象，策略执行业务算法
- **演进**：从 if/elif 链到全局映射，difable 后续可能改为注册表

## 5. 练习题

### 练习 1：基础（必做）

设计一个 `CacheStrategy`：
- `MemoryCache`：内存字典
- `RedisCache`：Redis 客户端
- 策略接口：`get(key)`、`set(key, value, ttl)`、`delete(key)`
- `CacheFactory.create(type: str)` 工厂方法

### 练习 2：进阶

阅读 `api/core/prompt/simple_prompt_transform.py` 和 `advanced_prompt_transform.py`：
1. 它们共同的接口是什么？
2. 它们各自处理什么场景？
3. dify 在哪里选择使用哪个策略？（grep `SimplePromptTransform` 和 `AdvancedPromptTransform` 的调用点）

### 练习 3：挑战（选做）

设计一个 `VectorIndexStrategy`：
- `FlatIndex`：暴力搜索（精确）
- `IVFIndex`：倒排索引（近似）
- `HNSWIndex`：图索引（近似快速）
- 工厂 `VectorIndexFactory.create(index_type, dim, **kwargs)`

要求：
- 策略接口：`add(vector, id)`、`search(query, top_k)`
- 工厂根据配置返回不同策略
- 单元测试可以用 `MockIndex` 替换

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/moderation/factory.py` — ModerationFactory
- `/Users/xu/code/github/dify/api/factories/agent_factory.py` — AgentFactory（函数式）
- `/Users/xu/code/github/dify/api/core/workflow/node_factory.py` — DifyNodeFactory
- `/Users/xu/code/github/dify/api/core/prompt/simple_prompt_transform.py` — SimplePromptTransform 策略
- `/Users/xu/code/github/dify/api/core/prompt/advanced_prompt_transform.py` — AdvancedPromptTransform 策略
- GoF《设计模式》策略模式 + 工厂模式章节

---

**文档版本**：v1.0
**最后更新**：2026-07-13