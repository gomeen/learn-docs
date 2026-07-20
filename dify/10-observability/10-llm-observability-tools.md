# 10.5.4 Langfuse / Helicone 等 LLM 专用工具

> LLM 应用的可观测性有别于传统微服务，需要专门的工具。dify 通过 OpsTraceManager 集成 10+ 主流 LLM 观测平台。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解主流 LLM 可观测性工具的特性和差异
- 理解 dify 的插件化追踪架构
- 能为 dify 配置 Langfuse / Helicone 等追踪后端
- 知道如何选择合适的 LLM 观测工具

## 📚 前置知识

- 10.5.1 LLM 调用追踪（`07-llm-tracing.md`）
- 10.3.4 dify 的链路追踪实现（`05-tracing-in-dify.md`）
- LLM 应用基础

## 1. 核心概念

### 1.1 主流 LLM 可观测性工具对比

| 工具 | 厂商 | 类型 | 特点 |
|------|------|------|------|
| **Langfuse** | Langfuse | 开源 + 云 | 专为 LLM 设计、UI 友好、成本追踪 |
| **Helicone** | Helicone | 开源 + 云 | 轻量级、实时成本监控 |
| **Phoenix** | Arize | 开源 | 专注于 LLM 调试、嵌入可视化 |
| **Arize** | Arize | 商业 + 开源版 | 企业级、ML 评估 |
| **LangSmith** | LangChain | 商业 | 与 LangChain 深度集成 |
| **Opik** | Comet | 开源 | 实验追踪 + LLM 评估 |
| **MLflow** | Databricks | 开源 | ML 通用、可自托管 |
| **Weave** | W&B | 商业 | 实验追踪 + LLM |

### 1.2 选型维度

| 维度 | 考虑因素 |
|------|----------|
| **部署模式** | SaaS（云服务）vs Self-hosted（自托管） |
| **成本** | 按调用量计费 vs 免费额度 |
| **隐私** | 数据是否离开本地 |
| **集成** | 与现有框架（LangChain / LlamaIndex）的兼容性 |
| **功能** | trace / 评估 / 数据集 / prompt 管理 |
| **生态** | 社区活跃度、文档质量 |

### 1.3 dify 的插件化架构

dify 通过 `OpsTraceProviderConfigMap` 实现插件化追踪后端：

```python
# api/core/ops/ops_trace_manager.py
match tracing_provider:
    case TracingProviderEnum.LANGFUSE:
        return LangFuseDataTrace, LangfuseConfig, ...
    case TracingProviderEnum.HELICONE:
        return HeliconeDataTrace, HeliconeConfig, ...
    # ...
```

**优势**：
- 新增追踪后端只需要添加一个 case
- 所有后端共享同一套数据模型
- 业务代码无感知

## 2. 代码示例

### 2.1 配置 Langfuse 作为追踪后端

```bash
# .env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com  # 或自托管地址
```

通过 dify 控制台：
1. 进入应用设置
2. 选择 "Tracing"
3. 选择 Provider: Langfuse
4. 填入 API Key
5. 启用追踪

### 2.2 配置 Helicone（OpenAI 代理模式）

```python
# 通过 OpenAI 代理方式使用 Helicone
import openai

client = openai.OpenAI(
    base_url="https://oai.hconeai.com/v1",
    api_key=os.environ["HELICONE_API_KEY"],
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    extra_headers={
        "Helicone-User-Id": "user-123",  # 用户维度追踪
        "Helicone-Property-App": "my-app",
    },
)
```

### 2.3 通过 OTEL 协议集成任意追踪后端

```python
# 使用 OpenTelemetry，把 trace 推送到任意后端
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# 推送到 Helicone / Langfuse / Phoenix 等支持 OTLP 的后端
exporter = OTLPSpanExporter(endpoint="https://collector.example.com:4317")
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)
```

### 2.4 常见错误：trace 太多导致成本失控

```bash
# ❌ 错误：100% trace 全部上传
OTEL_SAMPLING_RATE=1.0  # 所有请求都追踪

# ✅ 正确：生产环境按比例采样
OTEL_SAMPLING_RATE=0.1  # 10% 采样，足够分析问题
```

## 3. 关键要点总结

- 主流 LLM 追踪工具：Langfuse / Helicone / Phoenix / Arize / LangSmith 等
- dify 通过 `OpsTraceProviderConfigMap` 支持 10+ 追踪后端
- 插件化架构：`match/case` + lazy import + LRU 缓存
- 选型维度：部署模式、成本、隐私、集成、生态
- 注意 trace 采样率，避免成本失控
- dify 通过异步队列 + Celery 实现高吞吐 trace

---

**文档版本**：v1.0
**最后更新**：2026-07-13
