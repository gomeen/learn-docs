# 6.17 工具错误处理：失败与重试

> 理解工具调用失败的常见原因和 dify 的错误处理模式，能写出鲁棒的 tool-use 循环。

## 🎯 学习目标

完成本文文档后，你将能够：
- 列出工具调用失败的 5 类典型错误
- 区分"业务异常"、"参数错误"、"凭据过期"等不同失败模式的处理方式
- 理解 dify 的 `ToolInvokeMeta.error_instance` 和 `ToolEngine` 异常分支
- 设计工具调用重试与降级策略

## 📚 前置知识

- [Function Calling](./17-function-calling.md)
- [多工具路由](./19-multi-tool-routing.md)
- Python 异常处理（详见 [异常](../01-fundamentals/06-python-exceptions.md)）

## 1. 核心概念

### 1.1 工具调用失败的 5 类典型错误

```mermaid
graph TD
    A[工具调用失败] --> B[参数错误]
    A --> C[凭据问题]
    A --> D[网络 / 第三方 API]
    A --> E[业务逻辑]
    A --> F[超时]
    B --> B1[缺必填字段 / 类型不匹配]
    C --> C1[API Key 无效 / OAuth 过期]
    C --> C2[租户没安装该工具]
    D --> D1[HTTP 5xx / 连接拒绝]
    E --> E1[业务规则拒绝]
    E --> E2[内部异常]
    F --> F1[慢响应 / 死锁]
```

每类的处理策略不同：

| 类别 | 失败时机 | 是否可重试 | 处理方式 |
| --- | --- | --- | --- |
| 参数错误 | 模型产出 | 否 | 让 LLM 看到错误消息后自我修正 |
| 凭据问题 | 调用前/调用中 | 部分可（OAuth 刷新） | 提示用户更新凭据 |
| 网络/5xx | 调用中 | **是**（指数退避） | 立即重试 2-3 次 |
| 业务逻辑 | 调用中 | 视情况 | 返回错误让 LLM 调整策略 |
| 超时 | 等待响应 | 视情况 | 短超时重试；长超时改异步 |

### 1.2 dify 的两层错误捕获

dify 在 `core/tools/tool_engine.py` 的 `agent_invoke` 方法里有 **两层** 异常处理：

```mermaid
graph TD
    A[ToolEngine.agent_invoke] --> B[_invoke 内部]
    B --> B1[工具内部异常被 _invoke 捕获]
    B1 --> B2[包成 ToolEngineInvokeError meta 抛出]
    B2 --> C[外层 try/except 块]
    C --> C1[ToolProviderCredentialValidationError<br/>→ 凭据问题]
    C --> C2[ToolNotFoundError / ToolNotSupportedError<br/>→ 找不到工具]
    C --> C3[ToolParameterValidationError<br/>→ 参数问题]
    C --> C4[ToolInvokeError / ToolEngineInvokeError<br/>→ 业务错误]
    C --> C5[Exception<br/>→ 兜底]
```

- **内层 `_invoke`**：记录元数据（耗时、错误信息），把异常包装为 `ToolEngineInvokeError`
- **外层 `agent_invoke`**：把异常翻译成"自然语言错误消息"回传给 LLM（不是直接崩溃）

### 1.3 "让 LLM 自我修正"的回路

最关键的设计：把错误变成**纯文本消息**塞回 `tool_result`，让 LLM 在下一轮看到错误后调整参数：

```mermaid
sequenceDiagram
    participant LLM
    participant Agent
    participant Tool
    LLM->>Agent: tool_call: get_weather(city="北京")
    Agent->>Tool: get_weather(city="北京")
    Tool-->>Agent: 抛 ValueError("城市必须是英文")
    Agent->>Agent: 包成纯文本错误消息
    Agent-->>LLM: tool_result: "Error: 城市必须是英文"
    LLM->>Agent: 下一轮：tool_call: get_weather(city="Beijing")
    Agent->>Tool: get_weather(city="Beijing")
    Tool-->>Agent: "Beijing: 22°C"
    Agent-->>LLM: 成功结果
```

**核心洞察**：错误消息**对 LLM 可见**才能触发自我修正，所以错误描述要"对模型友好"（说清楚什么字段错了、应该怎么改），而非堆栈或 errno。

## 2. 代码示例

### 2.1 工具结果 vs 工具错误的统一处理

```python
# 文件：example_tool_error.py
import json
import time
from typing import Callable, Any
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    """统一的工具结果封装"""
    content: str
    is_error: bool = False
    meta: dict = field(default_factory=dict)


def safe_invoke(name: str, args: dict, impl: Callable, *, max_retries: int = 2) -> ToolResult:
    """统一处理：参数校验 + 重试 + 错误包装"""
    # 1. 业务层参数校验
    if "city" not in args:
        return ToolResult(
            content=f"Error: missing required parameter 'city'. "
                    f"Please provide it as a string.",
            is_error=True,
            meta={"tool_name": name, "error_type": "missing_param"},
        )

    # 2. 业务层带重试的执行
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            start = time.time()
            result = impl(**args)
            return ToolResult(
                content=json.dumps(result, ensure_ascii=False),
                is_error=False,
                meta={"tool_name": name, "elapsed": time.time() - start, "attempt": attempt + 1},
            )
        except (ConnectionError, TimeoutError) as e:
            # 网络/超时——可重试
            last_err = e
            time.sleep(0.1 * (2 ** attempt))  # 指数退避
            continue
        except ValueError as e:
            # 业务校验错误——直接返回，不要重试
            return ToolResult(
                content=f"Error: {e}",
                is_error=True,
                meta={"tool_name": name, "error_type": "validation"},
            )

    # 重试耗尽
    return ToolResult(
        content=f"Error: failed after {max_retries + 1} attempts: {last_err}",
        is_error=True,
        meta={"tool_name": name, "error_type": "network", "attempts": max_retries + 1},
    )


# 模拟一个不稳定的工具
def get_weather(city: str) -> str:
    if city == "Beijing":
        return {"city": city, "temp": 22, "unit": "C"}
    if city == "broken":
        raise ConnectionError("network failed")
    raise ValueError(f"unknown city: {city}. please use an English city name.")


# 模拟 LLM 的多次调用
calls = [
    {"name": "get_weather", "args": {}},                    # 缺参数
    {"name": "get_weather", "args": {"city": "北京"}},     # 业务校验失败
    {"name": "get_weather", "args": {"city": "broken"}},   # 网络失败（会重试）
    {"name": "get_weather", "args": {"city": "Beijing"}},  # 成功
]
for c in calls:
    r = safe_invoke(c["name"], c["args"], get_weather)
    tag = "OK  " if not r.is_error else "ERR "
    print(f"{tag} {c['args']} -> {r.content}  meta={r.meta}")
```

**说明**：
- 第 18-25 行：**业务层参数校验在工具调用前完成**——尽早失败，避免重试浪费
- 第 31-37 行：网络/超时异常自动重试，使用指数退避
- 第 38-43 行：业务校验错误（`ValueError`）**不重试**——重试无意义，直接返回
- 第 47-50 行：重试耗尽后返回带 attempt 计数的错误消息，方便上层判断
- 第 67-69 行：4 个测试场景覆盖了"缺参数 / 业务失败 / 网络失败重试 / 成功"四种情况

### 2.2 常见错误：凭据过期时无限重试

```python
# ❌ 错误：把所有错误都当网络错误重试
def safe_invoke(name, args, impl):
    for attempt in range(5):
        try:
            return impl(**args)
        except Exception:  # 凭据错误也被重试
            time.sleep(2 ** attempt)
            continue
# 问题：凭据错误重试 5 次浪费 30 秒

# ✅ 正确：区分可重试与不可重试
RETRYABLE = (ConnectionError, TimeoutError)
NON_RETRYABLE = (ValueError, PermissionError, KeyError)

def safe_invoke(name, args, impl, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            return impl(**args)
        except NON_RETRYABLE as e:
            # 立即返回
            return {"error": str(e), "retryable": False}
        except RETRYABLE as e:
            time.sleep(0.1 * 2 ** attempt)
    return {"error": "max retries", "retryable": True}
```

## 3. 关键要点总结

- 工具失败分 5 类：参数错误、凭据、网络、业务、超时——处理策略不同
- **关键设计**：把异常翻译成自然语言错误消息回传给 LLM，让 LLM 自我修正
- 重试只对**可重试错误**（网络/超时）有意义，凭据和参数错误重试无意义
- dify 用 `ToolInvokeMeta` 统一封装成功/失败结果，上层用 `error` 字段是否非空判断
- 用**领域异常类**（如 `ToolParameterValidationError`）区分错误类别，而非通用 `ValueError`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
