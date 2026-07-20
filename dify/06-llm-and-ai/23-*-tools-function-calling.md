# 小验证：Function Calling 与 dify 工具系统

> 覆盖：
> - [14-function-calling](./17-function-calling.md)
> - [15-tool-schema](./18-tool-schema.md)
> - [16-multi-tool-routing](./19-multi-tool-routing.md)
> - [17-tool-error-handling](./20-tool-error-handling.md)
> - [18-parallel-tool-calls](./21-parallel-tool-calls.md)
> - [19-tools-in-dify](./22-tools-in-dify.md)
>
> 预计：60～90 分钟 · 本地练习或改 dify 仓库

## 背景

工具调用把 LLM 接到真实世界。验证：定义 JSON Schema 工具，并模拟一次 tool loop。

## 需求

1. 本地实现 `tool_loop` 模拟器（无真实 LLM 也可）：输入「模型假想输出」的 function_call，路由到 Python 函数，返回 tool 结果再拼回消息列表。
2. 至少注册 2 个工具（如 `get_weather(city)`、`add(a,b)`），用 JSON Schema 描述参数。
3. 模拟：参数错误、工具抛异常、并行两次调用；保证错误对模型可见且不崩进程。
4. 对照 `api/core/tools/`，`NOTES.md` 写 Tool/Provider 的职责边界。

## 提示

- Schema：`type/object/properties/required`
- 仓库：`api/core/tools/`
- 并行：消息列表里多个 tool_call id

## 验收标准

- [ ] 2+ 工具可被路由执行
- [ ] 异常被转为 tool 错误结果而非堆栈直出
- [ ] 并行调用示例可运行
- [ ] NOTES 指向仓库类/文件

## 延伸（选做）

为工具增加 timeout 与重试次数配置。
