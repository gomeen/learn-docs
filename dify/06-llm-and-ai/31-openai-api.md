# 5.2 OpenAI API 使用

> 使用 OpenAI Python SDK 调用 Responses API，并理解它在 dify 统一模型运行时中的位置。

## 🎯 学习目标

完成本文档后，你将能够：
- 使用环境变量安全配置 OpenAI API Key
- 调用 Responses API 完成同步与流式文本生成
- 区分 `instructions`、`input`、模型参数与响应文本
- 看懂 dify 如何把具体厂商调用收敛到统一运行时接口

## 📚 前置知识

- [Token、上下文窗口与计费](./03-tokens-context.md)
- [模型参数](./04-model-parameters.md)
- Python 环境变量、异常处理与生成器（详见 [环境变量](../../_common/17-config/02-env-vars.md)、[异常](../01-fundamentals/06-python-exceptions.md)、[生成器](../01-fundamentals/16-generator.md)）
- HTTP 请求与 JSON（详见 [HTTP 协议](../../_common/14-api-protocols/01-http-protocol.md)、[JSON](../01-fundamentals/20-json-processing.md)）

## 1. 核心概念

### 1.1 Responses API 的请求与响应

OpenAI Python SDK 通过客户端对象发起请求。客户端默认从 `OPENAI_API_KEY` 环境变量读取密钥，因此不要把密钥写入源码、日志或提交到 Git。

一次最小文本生成包含四部分：

| 部分 | 作用 | 示例 |
| --- | --- | --- |
| `model` | 选择具体模型 | `gpt-4o-mini` |
| `instructions` | 定义角色和全局约束 | “只返回 JSON” |
| `input` | 本次用户输入 | “解释什么是 SSE” |
| `output_text` | SDK 汇总后的文本输出 | 模型答案 |

`instructions` 更像稳定的系统规则，`input` 是每次变化的任务内容。生产系统还应记录请求 ID、耗时、模型名和用量，以便排错与成本分析。

### 1.2 同步、异步与流式调用

- **同步非流式**：等待完整结果，适合脚本与后台批处理。
- **异步非流式**：等待网络时不阻塞事件循环，适合高并发服务（详见 [async/asyncio](../01-fundamentals/14-async-asyncio.md)）。
- **流式**：逐事件返回增量文本，首字延迟低，适合聊天界面。

流式 Responses API 会产生多种事件。文本增量事件类型是 `response.output_text.delta`，增量内容位于 `event.delta`；客户端必须忽略不认识的事件类型。

### 1.3 API 调用的工程边界

业务代码不应散落着 `OpenAI()` 调用。更稳健的分层是：

```text
业务节点 → 统一模型接口 → Provider/Runtime 适配层 → OpenAI SDK/API
```

这样可以统一处理凭据、重试、流式结果、工具调用、用量统计与厂商切换。dify 的 `ModelInstance.invoke_llm` 就是上层可见的统一入口。

## 2. 代码示例

### 2.1 调用 Responses API

先安装依赖并设置环境变量：`pip install openai`、`export OPENAI_API_KEY="..."`。

```python
# 文件：openai_response.py
import os

from openai import OpenAI


def main() -> None:
    client = OpenAI()
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        instructions="你是 Python 教师，用三句话回答。",
        input="生成器与普通函数有什么区别？",
    )
    print(response.output_text)
    print("request_id:", response._request_id)


if __name__ == "__main__":
    main()
```

**说明**：`OpenAI()` 自动读取 `OPENAI_API_KEY`；`output_text` 是 SDK 对响应内容的便捷汇总，`_request_id` 可用于排查单次请求。

### 2.2 异步读取流式文本

```python
# 文件：openai_stream.py
import asyncio
import os

from openai import AsyncOpenAI


async def main() -> None:
    client = AsyncOpenAI()
    stream = await client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        input="用四行说明为什么聊天应用适合流式输出。",
        stream=True,
    )

    async for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
```

**说明**：不要假设流中只有文本。只消费目标事件，可避免把生命周期事件或工具事件误显示给用户。

## 3. 关键要点总结

- 使用环境变量保存 API Key，不在代码和日志中泄露凭据。
- Responses API 用 `instructions` 表达稳定约束，用 `input` 表达本次任务。
- 非流式读取 `response.output_text`；流式筛选 `response.output_text.delta`。
- 生产代码要处理超时、错误、请求 ID、用量与重试，且避免盲目重试非幂等操作。
- dify 通过统一调用入口把 OpenAI 等供应商适配为一致的输入和结果。

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
