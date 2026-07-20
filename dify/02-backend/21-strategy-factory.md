# 2.4.4 策略模式与工厂模式

> 理解策略模式（Strategy）和工厂模式（Factory）的差异，掌握 dify 中的实际应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握策略模式和工厂模式的核心差异
- 在 dify 中找到工厂（`DifyNodeFactory`、`AgentFactory`、`ModerationFactory`）
- 在 dify 中找到策略（`SimplePromptTransform`、`AdvancedPromptTransform`）
- 设计可扩展的多算法/多实现系统

## 📚 前置知识

- [适配器模式](./20-adapter-pattern.md)
- [分层架构](../../_common/22-architecture/02-layered-architecture.md)
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
# 业务场景：定价策略（ABC 详见 [抽象基类 ABC](../01-fundamentals/25-abc.md)）
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

## 3. 关键要点总结

- **策略模式**：封装可互换的算法（如 `SimplePromptTransform` vs `AdvancedPromptTransform`）
- **工厂模式**：封装对象创建（如 `DifyNodeFactory`、`AgentFactory`、`ModerationFactory`）
- **策略 vs 工厂**：策略关注"怎么做"，工厂关注"创建什么"
- dify 用**纯函数工厂**（`get_plugin_agent_strategy`）和**类工厂**（`DifyNodeFactory`）两种风格
- dify 用 `extension_class()` **动态加载**机制（开放封闭原则）
- **组合使用**：工厂创建策略对象，策略执行业务算法
- **演进**：从 if/elif 链到全局映射，difable 后续可能改为注册表

---

**文档版本**：v1.0
**最后更新**：2026-07-13
