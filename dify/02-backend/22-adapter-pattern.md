# 2.4.3 适配器模式：对接多种外部服务

> 理解适配器模式（Adapter Pattern），掌握 dify 中对接多种外部服务的实现方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握适配器模式的核心思想：转换接口
- 在 dify 中找到适配器（`plugin_strategy_adapter`、`human_input_adapter`）
- 理解 dify 的多模型、多存储、多检索的适配方式
- 设计自己的适配器对接外部 API

## 📚 前置知识

- [分层架构](./02-layered-architecture.md)
- Python 接口（Protocol、ABC）基础（详见 [Protocol 与 Generic](../01-fundamentals/09-protocol-generic.md)、[抽象基类 ABC](../01-fundamentals/35-abc.md)）
- 经典适配器模式（详见 [适配器](../../_fundamentals/06-design-patterns/06-adapter.md)）

## 1. 核心概念

### 1.1 什么是适配器模式？

适配器模式把**不兼容的接口**转换为业务期望的接口。

**现实类比**：电源转接头（欧标 ↔ 美标）、翻译官。

**软件类比**：
- 适配器 A：dify 的内部接口 ↔ OpenAI API
- 适配器 B：dify 的内部接口 ↔ Anthropic API
- 适配器 C：dify 的内部接口 ↔ 自建 LLM API

```
[业务代码] → 适配器接口（dify 内部）
                ↓
            [适配器实现]
                ↓
            [外部 API（OpenAI / Anthropic / ...）]
```

### 1.2 dify 中的适配器场景

dify 需要对接多种外部系统：

| 适配对象 | 适配器 | 位置 |
|---------|--------|------|
| LLM Providers（OpenAI、Anthropic、Azure...） | ModelProvider 抽象 | `graphon/model_runtime/` |
| 向量数据库（pgvector、Qdrant、Milvus...） | VectorFactory | `core/rag/datasource/` |
| 文件存储（S3、Azure Blob、本地） | Storage | `extensions/ext_storage.py` |
| 邮件服务（SMTP、SendGrid...） | EmailService | `extensions/ext_mail.py` |
| Agent 策略（插件、Python 内置） | PluginAgentStrategyAdapter | `core/workflow/nodes/agent/` |
| Human Input 表单 | HumanInputAdapter | `core/workflow/human_input_adapter.py` |

### 1.3 适配器 vs 包装器

| 适配器 | 包装器 |
|--------|--------|
| **转换接口**：A 接口 ↔ B 接口 | **增强接口**：保留原接口 + 添加功能 |
| 用于集成不兼容的系统 | 用于扩展已有功能 |
| 如：dify 内部 ↔ OpenAI API | 如：日志装饰器包装函数 |

## 2. 代码示例

### 2.1 基础适配器

```python
from abc import ABC, abstractmethod


# === 业务期望的接口 ===
class PaymentGateway(ABC):
    """dify 业务期望的统一支付接口。"""
    @abstractmethod
    def charge(self, amount: int, currency: str, customer_id: str) -> dict:
        """扣款，返回 {transaction_id, status}。"""


# === 外部 API A：Stripe ===
class StripeClient:
    """Stripe 的原始 API（不兼容）。"""
    def create_payment_intent(self, amount_cents: int, currency: str, customer: str) -> dict:
        # Stripe 自己的格式...
        return {"id": "pi_xxx", "status": "succeeded"}


class StripeAdapter(PaymentGateway):
    """把 Stripe 接口适配为 PaymentGateway。"""
    def __init__(self, stripe_client: StripeClient):
        self._client = stripe_client

    def charge(self, amount: int, currency: str, customer_id: str) -> dict:
        # 调用 Stripe 的原始 API，转换结果
        result = self._client.create_payment_intent(
            amount_cents=amount,
            currency=currency,
            customer=customer_id,
        )
        # 把 Stripe 的 {id, status} 转换为统一的 {transaction_id, status}
        return {
            "transaction_id": result["id"],
            "status": "success" if result["status"] == "succeeded" else "failed",
        }


# === 外部 API B：PayPal ===
class PayPalClient:
    def create_payment(self, total: float, currency: str, payer_id: str) -> dict:
        return {"payment_id": "PAY-xxx", "state": "approved"}


class PayPalAdapter(PaymentGateway):
    def __init__(self, paypal_client: PayPalClient):
        self._client = paypal_client

    def charge(self, amount: int, currency: str, customer_id: str) -> dict:
        result = self._client.create_payment(
            total=amount / 100,  # 注意：PayPal 用元，dify 用分
            currency=currency,
            payer_id=customer_id,
        )
        return {
            "transaction_id": result["payment_id"],
            "status": "success" if result["state"] == "approved" else "failed",
        }


# === 业务代码使用统一接口 ===
def process_payment(gateway: PaymentGateway, amount: int, currency: str, customer: str):
    return gateway.charge(amount, currency, customer)


# 可以切换实现而不改业务代码
stripe = StripeAdapter(StripeClient())
process_payment(stripe, 1000, "USD", "cus_001")

paypal = PayPalAdapter(PayPalClient())
process_payment(paypal, 1000, "USD", "cus_001")
```

### 2.2 dify 风格的适配器（基于 Protocol）

```python
from typing import Protocol


# 业务接口（dify 内部）
class LLMClient(Protocol):
    """dify 内部统一的 LLM 调用接口。"""
    def invoke(self, prompt: str, **kwargs) -> str: ...


# OpenAI 适配器
class OpenAIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def chat_completions_create(self, model: str, messages: list, **kwargs) -> dict:
        # OpenAI 自己的调用方式
        import openai
        return openai.OpenAI(api_key=self.api_key).chat.completions.create(...)


class OpenAIAdapter:
    """把 OpenAI 适配为 dify 内部接口。"""
    def __init__(self, client: OpenAIClient, model: str = "gpt-4"):
        self._client = client
        self._model = model

    def invoke(self, prompt: str, **kwargs) -> str:
        # 转换：dify 的 prompt → OpenAI 的 messages
        messages = [{"role": "user", "content": prompt}]
        result = self._client.chat_completions_create(
            model=self._model,
            messages=messages,
            **kwargs,
        )
        # 转换：OpenAI 的响应 → 纯文本
        return result["choices"][0]["message"]["content"]


# 使用：业务代码只看到 invoke(prompt)
client = OpenAIAdapter(OpenAIClient(api_key="..."))
text = client.invoke("Hello, world!")
```

### 2.3 常见错误：适配器泄漏外部细节

```python
# ❌ 错误：适配器泄漏了 OpenAI 的字段名
class BadAdapter:
    def invoke(self, prompt: str) -> dict:  # 返回 OpenAI 格式的 dict
        return self._client.chat_completions_create(...)


# 业务代码：openai.choices[0].message.content
result = adapter.invoke("Hi")
text = result["choices"][0]["message"]["content"]  # 泄漏外部 API 细节！

# ✅ 正确：适配器只返回业务需要的格式
class GoodAdapter:
    def invoke(self, prompt: str) -> str:  # 返回纯字符串
        result = self._client.chat_completions_create(...)
        return result["choices"][0]["message"]["content"]


# 业务代码：只用 invoke 返回字符串
text = adapter.invoke("Hi")
```

## 3. dify 仓库源码解读

### 3.1 Agent Strategy 适配器

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/agent/plugin_strategy_adapter.py`
**核心代码**（节选）：

```python
class PluginAgentStrategyPresentationProvider:
    """把 dify 的 Agent 节点配置适配为插件系统的输入。

    PluginAgentStrategy 来自插件系统（外部）
    dify 的 Agent 节点配置是 dify 内部结构
    这个适配器负责双向转换：
    - dify 配置 → 插件参数
    - 插件结果 → dify 节点输出
    """
    def __init__(self, agent_strategy: PluginAgentStrategy):
        self._strategy = agent_strategy

    def get_parameters(self) -> list[dict]:
        """把插件的参数声明转换为 dify 的 UI 格式。"""
        # ...转换逻辑
        pass


class PluginAgentStrategyResolver:
    """根据 Agent 节点配置解析为具体的 PluginAgentStrategy 实例。"""

    def resolve(self, agent_strategy_provider: str, agent_strategy_name: str) -> PluginAgentStrategy:
        """从插件系统加载具体的策略。"""
        return get_plugin_agent_strategy(
            tenant_id=self._tenant_id,
            agent_strategy_provider_name=agent_strategy_provider,
            agent_strategy_name=agent_strategy_name,
        )
```

**解读**：
- 第 1-12 行：`PluginAgentStrategyPresentationProvider` 把插件系统的参数定义转为 dify 的 UI 格式
- 第 15-27 行：`PluginAgentStrategyResolver` 负责从插件系统加载策略
- **典型适配器**：隔离插件系统（外部）和 dify 内部的数据结构

### 3.2 HumanInput 适配器

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/human_input_adapter.py`
**核心代码**（节选）：

```python
def adapt_node_config_for_graph(graph_node_config: NodeConfigDict) -> NodeConfigDict:
    """把 dify 的 HumanInput 节点配置适配为 graphon 引擎的配置格式。

    适配点：
    - dify 的 DeliveryMethod（email/slack/teams）→ graphon 的 channel 字符串
    - dify 的 FormInputConfig → graphon 的 FormSchema
    - dify 的超时设置 → graphon 的 deadline
    """
    # ...
    pass


def adapt_human_input_node_data_for_graph(node_data: HumanInputNodeData) -> HumanInputNodeData:
    """类似的适配，但只针对节点数据。"""
    pass


def parse_human_input_delivery_methods(methods_config: list[dict]) -> list[DeliveryChannelConfig]:
    """把 dify 的 delivery methods 配置解析为运行时通道配置。"""
    return [
        DeliveryChannelConfig(
            channel_type=DeliveryChannelType(method["type"]),
            config=method.get("config", {}),
        )
        for method in methods_config
    ]
```

**解读**：
- 第 1-12 行：`adapt_node_config_for_graph` 节点级配置适配
- 第 15-17 行：`adapt_human_input_node_data_for_graph` 节点数据适配
- 第 20-27 行：`parse_human_input_delivery_methods` 把 dify 的 delivery methods 解析为运行时配置
- **适配维度**：UI 配置 ↔ 运行时配置 ↔ 第三方系统（email/Slack/Teams）

### 3.3 文件上传适配器

**文件位置**：`/Users/xu/code/github/dify/api/factories/file_factory.py`
**核心代码**（节选）：

```python
from graphon.file import File
from graphon.file.file_manager import file_manager


def build_from_mapping(mapping: dict, tenant_id: str) -> File:
    """根据 dict 构建 File 对象。

    适配 dify 上传 API 的 dict 格式 → graphon 的 File 对象
    """
    # 提取 dify 格式的字段
    transfer_method = mapping.get("transfer_method", "remote_url")
    if transfer_method == "remote_url":
        url = mapping.get("url")
        return File.from_url(url=url, tenant_id=tenant_id)
    elif transfer_method == "local_file":
        upload_file_id = mapping.get("upload_file_id")
        return file_manager.fetch(upload_file_id=upload_file_id, tenant_id=tenant_id)
    elif transfer_method == "tool_file":
        tool_file_id = mapping.get("tool_file_id")
        # ... 另一种适配
    else:
        raise ValueError(f"Unsupported transfer method: {transfer_method}")
```

**解读**：
- 第 7-22 行：根据 `transfer_method` 字段选择不同的适配路径
- 第 12-13 行：远程 URL 适配为 `File.from_url()`
- 第 14-15 行：本地文件 ID 适配为 `file_manager.fetch()`
- **典型工厂 + 适配器组合**：根据输入类型选择不同的适配实现（工厂详见 [策略与工厂](./23-strategy-factory.md)）

## 4. 关键要点总结

- 适配器模式把**不兼容的接口**转换为业务期望的接口
- dify 的适配器场景：LLM、向量库、文件存储、Agent 插件、Human Input 等
- 适配器**隔离外部 API 细节**，业务代码只看到统一接口
- 适配器基于 **Protocol**（结构化子类型）或 **ABC**（抽象基类）
- dify 的 `plugin_strategy_adapter.py`、`human_input_adapter.py` 是典型例子
- 适配器**不应泄漏外部细节**（返回原始 dict）
- 工厂 + 适配器组合：根据输入类型选择不同的适配实现

## 5. 练习题

### 练习 1：基础（必做）

设计一个 `EmailService` 适配器：
- 定义统一的 `EmailService` 接口（`send(to, subject, body)`）
- 实现 `SMTPEmailAdapter`（用 `smtplib`）
- 实现 `SendGridEmailAdapter`（用 HTTP API）
- 编写一个 `EmailServiceFactory`，根据配置返回不同适配器

### 练习 2：进阶

阅读 `api/core/workflow/nodes/agent/plugin_strategy_adapter.py`：
1. 列出所有适配器类
2. 它们各自把什么格式转换为另一种格式？
3. 为什么 dify 需要"插件系统"的适配器，而不是直接调用插件？

### 练习 3：挑战（选做）

为 dify 设计一个 `VectorStore` 适配器：

```python
class VectorStoreAdapter(Protocol):
    def similarity_search(self, query_embedding: list[float], top_k: int) -> list[SearchResult]: ...
    def add_documents(self, documents: list[Document]) -> None: ...
    def delete(self, ids: list[str]) -> None: ...

class PgVectorAdapter: ...  # pgvector 实现
class QdrantAdapter: ...   # Qdrant 实现
class MilvusAdapter: ...   # Milvus 实现
```

要求：
- 三个适配器实现同样的接口
- 通过配置切换（`dify_config.VECTOR_STORE = "pgvector" | "qdrant" | "milvus"`）
- 单元测试可以用 InMemoryVectorStore 替换

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/agent/plugin_strategy_adapter.py` — Agent 插件适配
- `/Users/xu/code/github/dify/api/core/workflow/human_input_adapter.py` — HumanInput 适配
- `/Users/xu/code/github/dify/api/factories/file_factory.py` — 文件上传适配
- `/Users/xu/code/github/dify/api/core/model_manager.py` — 模型管理器
- `/Users/xu/code/github/dify/api/extensions/ext_storage.py` — 文件存储适配

---

**文档版本**：v1.0
**最后更新**：2026-07-13