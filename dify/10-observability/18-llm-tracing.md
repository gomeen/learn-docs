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

## 3. dify 仓库源码解读

### 3.1 dify 的 Prompt Generation Trace

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 1289-1354）：

```python
def prompt_generation_trace(self, **kwargs) -> PromptGenerationTraceInfo | dict:
    tenant_id = kwargs.get("tenant_id", "")
    user_id = kwargs.get("user_id", "")
    app_id = kwargs.get("app_id")
    operation_type = kwargs.get("operation_type", "")
    instruction = kwargs.get("instruction", "")
    generated_output = kwargs.get("generated_output", "")

    prompt_tokens = kwargs.get("prompt_tokens", 0)
    completion_tokens = kwargs.get("completion_tokens", 0)
    total_tokens = kwargs.get("total_tokens", 0)

    model_provider = kwargs.get("model_provider", "")
    model_name = kwargs.get("model_name", "")

    latency = kwargs.get("latency", 0.0)

    timer = kwargs.get("timer")
    start_time = timer.get("start") if timer else None
    end_time = timer.get("end") if timer else None

    total_price = kwargs.get("total_price")
    currency = kwargs.get("currency")

    error = kwargs.get("error")

    app_name = None
    workspace_name = None
    if app_id:
        app_name, workspace_name = _lookup_app_and_workspace_names(app_id, tenant_id)

    metadata = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "app_id": app_id or "",
        "app_name": app_name,
        "workspace_name": workspace_name,
        "operation_type": operation_type,
        "model_provider": model_provider,
        "model_name": model_name,
    }
    if node_execution_id := kwargs.get("node_execution_id"):
        metadata["node_execution_id"] = node_execution_id

    return PromptGenerationTraceInfo(
        trace_id=self.trace_id,
        inputs=instruction,
        outputs=generated_output,
        start_time=start_time,
        end_time=end_time,
        metadata=metadata,
        tenant_id=tenant_id,
        user_id=user_id,
        app_id=app_id,
        operation_type=operation_type,
        instruction=instruction,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model_provider=model_provider,
        model_name=model_name,
        latency=latency,
        total_price=total_price,
        currency=currency,
        error=error,
    )
```

**解读**：
- 第 2-7 行：基础业务信息（租户、用户、应用）
- 第 9-11 行：核心 trace 数据（输入、输出）
- 第 13-15 行：Token 用量（prompt/completion/total）
- 第 17-18 行：模型维度（provider/name）
- 第 20 行：延迟（latency）
- 第 24 行：成本（total_price / currency）
- 第 31-32 行：APP 和工作区名称（企业版才查询）
- 第 36-46 行：metadata 包含完整上下文
- 第 48-66 行：构造 `PromptGenerationTraceInfo` 实体
- **关键设计**：把所有相关信息聚合到一个对象，方便 trace 后端展示

### 3.2 dify 的工作流 Token 聚合

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 668-714）：

```python
@classmethod
def _calculate_workflow_token_split(
    cls, session: "Session", workflow_run_id: str, tenant_id: str
) -> tuple[int, int]:
    """Sum prompt/completion tokens across all node executions for a workflow run.

    Reads from the ``outputs`` column (where LLM nodes store ``usage.prompt_tokens``
    and ``usage.completion_tokens``) rather than ``execution_metadata``, which only
    carries ``total_tokens``.  Projects only the ``outputs`` column to avoid loading
    large JSON blobs unnecessarily.
    """

    from models.workflow import WorkflowNodeExecutionModel

    rows = (
        session.execute(
            select(WorkflowNodeExecutionModel.outputs).where(
                WorkflowNodeExecutionModel.tenant_id == tenant_id,
                WorkflowNodeExecutionModel.workflow_run_id == workflow_run_id,
            )
        )
        .scalars()
        .all()
    )

    total_prompt = 0
    total_completion = 0

    for raw in rows:
        if not raw:
            continue
        try:
            outputs = JSON_DICT_ADAPTER.validate_json(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            continue
        if not isinstance(outputs, dict):
            continue
        usage = outputs.get("usage")
        if not isinstance(usage, dict):
            continue
        prompt = usage.get("prompt_tokens")
        if isinstance(prompt, (int, float)):
            total_prompt += int(prompt)
        completion = usage.get("completion_tokens")
        if isinstance(completion, (int, float)):
            total_completion += int(completion)

    return (total_prompt, total_completion)
```

**解读**：
- 第 5-9 行：docstring 解释为什么读 `outputs` 而不是 `execution_metadata`
  - `outputs` 包含完整的 `usage.prompt_tokens` 和 `usage.completion_tokens`
  - `execution_metadata` 只有 `total_tokens`（不够细）
- 第 11-19 行：**只 SELECT `outputs` 列**——避免加载大 JSON blob
- 第 21-22 行：累加器
- 第 24-29 行：**多层防御性编程**（每个字段都检查类型和存在性）
- **关键设计**：用 `outputs.usage` 而不是单独的 `usage` 表，简化数据模型

### 3.3 dify 的节点执行 trace

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 1356-1458）：

```python
def node_execution_trace(self, **kwargs) -> WorkflowNodeTraceInfo | dict[str, Any]:
    node_data: dict[str, Any] = kwargs.get("node_execution_data", {})
    if not node_data:
        return {}

    # ... 省略 credentials 查找逻辑 ...

    return WorkflowNodeTraceInfo(
        trace_id=self.trace_id,
        message_id=message_id,
        start_time=node_data.get("created_at"),
        end_time=node_data.get("finished_at"),
        metadata=metadata,
        workflow_id=node_data.get("workflow_id", ""),
        workflow_run_id=node_data.get("workflow_execution_id", ""),
        tenant_id=node_data.get("tenant_id", ""),
        node_execution_id=node_data.get("node_execution_id", ""),
        node_id=node_data.get("node_id", ""),
        node_type=node_data.get("node_type", ""),
        title=node_data.get("title", ""),
        status=node_data.get("status", ""),
        error=node_data.get("error"),
        elapsed_time=node_data.get("elapsed_time", 0.0),
        index=node_data.get("index", 0),
        predecessor_node_id=node_data.get("predecessor_node_id"),
        total_tokens=node_data.get("total_tokens", 0),
        total_price=node_data.get("total_price", 0.0),
        currency=node_data.get("currency"),
        model_provider=node_data.get("model_provider"),
        model_name=node_data.get("model_name"),
        prompt_tokens=node_data.get("prompt_tokens"),
        completion_tokens=node_data.get("completion_tokens"),
        tool_name=node_data.get("tool_name"),
        iteration_id=node_data.get("iteration_id"),
        iteration_index=node_data.get("iteration_index"),
        loop_id=node_data.get("loop_id"),
        loop_index=node_data.get("loop_index"),
        parallel_id=node_data.get("parallel_id"),
        node_inputs=node_data.get("node_inputs"),
        node_outputs=node_data.get("node_outputs"),
        process_data=node_data.get("process_data"),
        invoked_by=self._get_user_id_from_metadata(metadata),
    )
```

**解读**：
- 第 5-6 行：空数据时返回空 dict（避免异常）
- 第 26-29 行：节点基础信息（id / type / title / status）
- 第 33-34 行：成本信息（`total_price` / `currency`）
- 第 35-38 行：LLM 相关信息（provider / name / tokens）
- 第 39 行：工具调用名（Tool 节点专用）
- 第 40-45 行：**循环 / 迭代节点的 ID**——支持复杂工作流的 trace 重建
- 第 46-47 行：节点输入输出（用于调试）
- **关键设计**：节点级 trace 同时记录 LLM 数据和结构信息（iteration/loop/parallel）

## 4. 关键要点总结

- LLM 追踪特有维度：Prompt / Response / Token / TTFT / TPS
- dify 把 usage 信息写入 `WorkflowNodeExecutionModel.outputs`
- `PromptGenerationTraceInfo` 包含完整的 LLM 调用上下文
- 流式响应单独追踪 TTFT 和 TPS（`time_to_first_token` / `time_to_generate`）
- 节点级 trace 记录 cost、currency、iteration/loop ID 等复杂结构
- 多层防御性编程处理 JSON 解析和缺失字段

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `LLMCallTracer` 装饰器：自动捕获 LLM 调用的 prompt、response、token 数、延迟，并写入 dify 的 `WorkflowNodeExecutionModel.outputs`。

### 练习 2：进阶

阅读 `api/core/ops/ops_trace_manager.py` 的 `_calculate_workflow_token_split`，解释 dify 为什么选择把 usage 存到 `outputs` 列而不是单独的 `usage` 表？

### 练习 3：挑战（选做）

扩展 dify 的 `PromptGenerationTraceInfo`，新增 `cost_breakdown` 字段：把 `total_price` 拆分为 `prompt_cost` 和 `completion_cost`，并按模型价格表自动计算。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
- `/Users/xu/code/github/dify/api/core/ops/entities/trace_entity.py`
- OpenTelemetry GenAI 语义约定：https://opentelemetry.io/docs/specs/semconv/gen-ai/
- Langfuse LLM 追踪：https://langfuse.com/docs/observability

---

**文档版本**：v1.0
**最后更新**：2026-07-13