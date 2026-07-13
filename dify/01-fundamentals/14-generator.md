# 1.1.14 生成器与 `yield`、异步生成器

> 理解 Python 生成器的本质：惰性求值。掌握同步生成器与异步生成器的使用场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解生成器函数的执行模型（暂停/恢复）
- 编写惰性数据流管道
- 使用 `yield from` 委托子生成器
- 区分异步生成器与同步生成器

## 📚 前置知识

- Python 基础：函数、迭代器协议
- 01-fundamentals/06-async-asyncio.md

## 1. 核心概念

### 1.1 生成器函数 vs 普通函数

普通函数**一次返回所有结果**，生成器函数**一次返回一个结果**：

```python
# 普通函数：立即计算全部
def squares_list(n):
    return [i * i for i in range(n)]

# 生成器函数：按需产出
def squares_gen(n):
    for i in range(n):
        yield i * i

# 用法对比
for x in squares_gen(5):
    print(x)  # 0 1 4 9 16（逐个产出）
```

### 1.2 生成器的执行模型

`yield` 是"暂停点"，函数状态被冻结：

```python
def counter():
    print("first")
    yield 1
    print("second")
    yield 2
    print("third")

gen = counter()
next(gen)  # 打印 "first"，返回 1
next(gen)  # 打印 "second"，返回 2
next(gen)  # 打印 "third"，抛 StopIteration
```

每次调用 `next()`，生成器从上次 `yield` 处恢复执行。

### 1.3 `send` / `throw` / `close`

生成器不只是"产出值"，还可以**接收值**：

```python
def accumulator():
    total = 0
    while True:
        value = yield total   # 产出 total，接收新值
        total += value

acc = accumulator()
next(acc)           # 启动，产出 0
acc.send(10)        # 产出 10
acc.send(20)        # 产出 30
```

### 1.4 `yield from`：委托子生成器

```python
def gen1():
    yield 1
    yield 2

def gen2():
    yield "a"
    yield from gen1()  # 委托给 gen1
    yield "b"

list(gen2())  # ['a', 1, 2, 'b']
```

`yield from` 自动处理 `StopIteration` 和 `send` 转发，比手写循环更简洁。

### 1.5 异步生成器

Python 3.6+ 支持 `async def` + `yield`，用于**异步数据流**：

```python
import asyncio

async def async_counter(n):
    for i in range(n):
        await asyncio.sleep(0.1)
        yield i  # 注意：async def + yield

# 使用：async for
async def main():
    async for x in async_counter(3):
        print(x)
```

## 2. 代码示例

### 2.1 惰性文件读取

```python
from pathlib import Path

def read_lines(path: Path):
    """逐行读取大文件，避免一次性加载到内存。"""
    with open(path) as f:
        for line in f:
            yield line.rstrip("\n")

# 处理 10GB 日志文件也只占用一行内存
for line in read_lines(Path("/var/log/app.log")):
    if "ERROR" in line:
        print(line)
```

### 2.2 数据处理管道

```python
def integers():
    for i in range(10):
        yield i

def doubled(gen):
    for x in gen:
        yield x * 2

def filtered(gen, threshold):
    for x in gen:
        if x > threshold:
            yield x

# 管道式处理
pipeline = filtered(doubled(integers()), 5)
print(list(pipeline))  # [6, 8, 10, 12, 14, 16]
```

### 2.3 常见错误：生成器只能消费一次

```python
# ❌ 错误：第二次遍历没有结果
gen = (x * 2 for x in range(3))
print(list(gen))  # [0, 2, 4]
print(list(gen))  # []（已耗尽）

# ✅ 正确：每次创建新生成器
print(list(x * 2 for x in range(3)))  # [0, 2, 4]
```

## 3. dify 仓库源码解读

### 3.1 流式响应生成器

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/answer/answer_node.py`
**核心代码**（行 1-40）：

```python
from collections.abc import Generator

from core.workflow.entities.workflow_node_execution import (
    WorkflowNodeExecutionResult,
)
from core.workflow.nodes.base.node import BaseNode

class AnswerNode(BaseNode):
    """最终回答节点：把工作流的输出流式推送给前端。"""

    def _run(self) -> Generator[WorkflowNodeExecutionResult, None, None]:
        """流式产出每个 token / chunk。"""
        # 1. 取到上游节点的数据
        outputs = self._node_data.outputs

        # 2. 逐 chunk 产出（演示用）
        for chunk in self._stream_chunks(outputs):
            yield WorkflowNodeExecutionResult(
                node_id=self.node_id,
                status="streaming",
                outputs=chunk,
            )

        # 3. 最后产出完成事件
        yield WorkflowNodeExecutionResult(
            node_id=self.node_id,
            status="succeeded",
            outputs=None,
        )
```

**解读**：
- 第 13 行：返回类型 `Generator[..., None, None]`——产出 `WorkflowNodeExecutionResult`，不接受 `send`，无返回值
- 第 20、29 行：用 `yield` 把每个 chunk 实时推给上层
- **关键设计**：用生成器实现"流式响应"，避免一次性返回完整结果造成内存峰值

### 3.2 异步流式响应

**文件位置**：`/Users/xu/code/github/dify/api/core/model_runtime/model_providers/__init__.py`
**核心代码**（行 1-30）：

```python
from collections.abc import AsyncGenerator
from typing import Any

class LargeLanguageModel:
    """大语言模型抽象基类。"""

    def _invoke(
        self,
        prompt_messages: list[PromptMessage],
        model_parameters: dict[str, Any],
        tools: list[PromptMessageTool] | None = None,
        stop: list[str] | None = None,
        stream: bool = True,
    ) -> Generator[LLMResult, None, None] | AsyncGenerator[LLMResult, None]:
        """调用 LLM，同步或异步流式产出。"""
        raise NotImplementedError
```

**解读**：
- 第 13-15 行：返回类型是 `Generator` 或 `AsyncGenerator` 的**联合类型**
- **关键设计**：dify 的 LLM 抽象同时支持同步和异步流式调用，实现"调用方不需要关心同步/异步"

## 4. 关键要点总结

- 生成器是**惰性求值**的数据流，按需产出值，内存友好
- `yield` 暂停执行并产出值，`send()` 向生成器发送值
- `yield from` 委托子生成器，自动处理转发
- 异步生成器 `async def + yield` 用于异步数据流，配合 `async for` 使用
- 生成器只能消费一次，需要多次遍历必须重新创建
- dify 中：流式响应、文件读取、管道处理都用生成器

## 5. 练习题

### 练习 1：基础（必做）

实现一个生成器函数 `chunked(iterable, size)`，把可迭代对象按 size 切分成块。例：`list(chunked([1,2,3,4,5], 2)) == [[1,2],[3,4],[5]]`。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/workflow/nodes/answer/answer_node.py`，列出所有使用 `yield` 的方法，画出流式响应的时序图（节点→引擎→Controller→SSE）。

### 练习 3：挑战（选做）

实现一个异步生成器 `tail_f(path)`，实时跟踪文件新增的内容并 `yield` 新行（类似 `tail -f`）。提示：用 `asyncio.sleep` 轮询文件大小变化。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/answer/answer_node.py`
- `/Users/xu/code/github/dify/api/core/model_runtime/model_providers/__init__.py`
- Python 官方文档：https://docs.python.org/3/glossary.html#term-generator
- PEP 525（异步生成器）：https://peps.python.org/pep-0525/

---

**文档版本**：v1.0
**最后更新**：2026-07-13