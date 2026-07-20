# 10.5.1 LLM 调用追踪：Prompt / Response / Token

> LLM 应用的可观测性比传统微服务更复杂——需要追踪 Prompt、Response、Token、延迟、成本等多维信息。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 LLM 调用追踪的特有维度（Prompt、Response、Token）
- 掌握 dify 中 LLM trace 的数据结构
- 能用 dify 提供的 trace 接口追踪自定义 LLM 调用
- 为后续 LLM 成本分析打基础

## 📚 前置知识

- 10.3 链路追踪相关文档
- LLM 基本概念（Prompt / Completion / Token）
- 04-cache-and-queue Celery 异步任务

## 1. 核心概念

### 1.1 LLM 追踪的特有维度

相比传统微服务调用，LLM 调用需要追踪：

| 维度 | 含义 | 价值 |
|------|------|------|
| **Prompt** | 输入文本 | 调试输入问题、复现 bug |
| **Response** | 输出文本 | 评估质量、检测幻觉 |
| **Prompt Tokens** | 输入 Token 数 | 计算成本 |
| **Completion Tokens** | 输出 Token 数 | 计算成本 |
| **Model** | 使用的模型 | 成本分摊、性能对比 |
| **Provider** | 模型服务商 | SLA 监控、容灾切换 |
| **TTFT** | 首个 Token 时间 | 流式用户体验 |
| **TPS** | Token/秒 | 模型吞吐能力 |
| **Stop Reason** | 终止原因 | 检测异常（长度截断、内容过滤） |
| **Cached** | 是否命中缓存 | 优化效果 |

### 1.2 GenAI 语义约定

OpenTelemetry 定义了 GenAI 语义约定（`gen_ai.*`）：

| 属性 | 含义 |
|------|------|
| `gen_ai.system` | 模型系统（openai / anthropic / cohere） |
| `gen_ai.request.model` | 请求的模型名 |
| `gen_ai.usage.input_tokens` | 输入 Token 数 |
| `gen_ai.usage.output_tokens` | 输出 Token 数 |
| `gen_ai.response.model` | 实际返回的模型名 |

### 1.3 dify 的 LLM trace 数据流

```
LLM 节点执行
    ↓
LLM SDK 返回 usage 信息
    ↓
写入 WorkflowNodeExecutionModel.outputs["usage"]
    ↓
异步推送到 OpsTraceManager
    ↓
第三方追踪后端（Langfuse / Phoenix）
```

## 2. 代码示例

### 2.1 dify 中 LLM Token 用量的存储位置

dify 在每次 LLM 节点执行时，会把 usage 写入 `outputs` 列：

```python
# 伪代码：LLM 节点执行后
node_execution.outputs = {
    "usage": {
        "prompt_tokens": 1234,
        "completion_tokens": 567,
        "total_tokens": 1801,
    },
    "model": "gpt-4",
    "provider": "openai",
    "finish_reason": "stop",
}
```

### 2.2 追踪自定义 LLM 调用（dify 风格）

```python
from core.ops.ops_trace_manager import TraceTask, TraceQueueManager
from core.ops.entities.trace_entity import TraceTaskName

def call_llm_with_tracing(prompt: str, model: str = "gpt-4"):
    # 1. 调用 LLM
    response = openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    usage = response.usage

    # 2. 创建 trace task
    timer = {"start": start_time, "end": end_time}
    trace_task = TraceTask(
        trace_type=TraceTaskName.PROMPT_GENERATION_TRACE,
        tenant_id=tenant_id,
        user_id=user_id,
        app_id=app_id,
        instruction=prompt,
        generated_output=response.choices[0].message.content,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        model_provider="openai",
        model_name=model,
        latency=(end_time - start_time).total_seconds(),
        timer=timer,
    )

    # 3. 加入异步队列
    queue_manager = TraceQueueManager(app_id=app_id, user_id=user_id)
    queue_manager.add_trace_task(trace_task)

    return response.choices[0].message.content
```

### 2.3 提取 dify 中的流式响应指标

```python
# api/core/ops/ops_trace_manager.py 中的实现
def _extract_streaming_metrics(self, message_data) -> dict[str, Any]:
    if not message_data.message_metadata:
        return {}

    try:
        metadata = JSON_DICT_ADAPTER.validate_json(message_data.message_metadata)
        usage = metadata.get("usage", {})
        time_to_first_token = usage.get("time_to_first_token")
        time_to_generate = usage.get("time_to_generate")

        return {
            "gen_ai_server_time_to_first_token": time_to_first_token,
            "llm_streaming_time_to_generate": time_to_generate,
            "is_streaming_request": time_to_first_token is not None,
        }
    except (ValueError, AttributeError):
        return {}
```

## 3. 关键要点总结

- LLM 追踪特有维度：Prompt / Response / Token / TTFT / TPS
- dify 把 usage 信息写入 `WorkflowNodeExecutionModel.outputs`
- `PromptGenerationTraceInfo` 包含完整的 LLM 调用上下文
- 流式响应单独追踪 TTFT 和 TPS（`time_to_first_token` / `time_to_generate`）
- 节点级 trace 记录 cost、currency、iteration/loop ID 等复杂结构
- 多层防御性编程处理 JSON 解析和缺失字段

---

**文档版本**：v1.0
**最后更新**：2026-07-13
