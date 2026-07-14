# 01 - 编程语言与基础工具

> 全栈后端开发的「地基」。所有其他分类的知识都依赖这里的内容。

## 📚 前置知识：Python 基础（必读）

> 如果你是 Python 初学者，先看这里；如果已经熟悉，可以跳过。

- [ ] [0.1 Python 变量与数据类型](./01-python-variables-and-types.md)
- [ ] [0.2 Python 函数基础](./02-python-functions.md)
- [ ] [0.3 Python 类与对象基础](./03-python-classes-basics.md)
- [ ] [0.4 Python 模块、包与导入](./04-python-modules-and-imports.md)
- [ ] [0.5 Python 控制流（if/for/while/with）](./05-python-control-flow.md)
- [ ] [0.6 Python 异常处理（try/except/raise）](./06-python-exceptions.md)

## 模块 1.1 Python 核心

- [ ] [1.1.7 Python 类型系统：`typing` 模块基础](./07-python-typing-basics.md)
- [ ] [1.1.8 `TypedDict` 与 `NotRequired`：结构化字典](./08-typeddict.md)
- [ ] [1.1.9 `Protocol` 与 `Generic`：行为抽象与泛型](./09-protocol-generic.md)
- [ ] [1.1.10 装饰器（Decorator）的原理与实践](./10-decorator.md)
- [ ] [1.1.11 上下文管理器（Context Manager）与 `with` 语句](./11-context-manager.md)
- [ ] [1.1.12 Python 异步编程：`asyncio` / `async/await`](./12-async-asyncio.md)
- [ ] [1.1.13 协程、Task、Future 与事件循环](./13-async-task-future.md)
- [ ] [1.1.14 生成器与 `yield`、异步生成器](./14-generator.md)
- [ ] [1.1.15 Python 包管理：`uv` 与 `pyproject.toml`](./15-uv-package-management.md)
- [ ] [1.1.16 魔术方法：`__init__` / `__repr__` / `__str__` / `__eq__`](./16-dunder-methods.md)
- [ ] [1.1.17 元类（Metaclass）与类创建过程](./33-metaclass.md)
- [ ] [1.1.18 描述符（Descriptor）协议](./34-descriptor.md)
- [ ] [1.1.19 抽象基类（abc 模块）](./35-abc.md)
- [ ] [1.1.20 `dataclass` 数据类](./36-dataclasses.md)
- [ ] [1.1.21 `itertools` 模块：迭代器工具箱](./37-itertools.md)
- [ ] [1.1.22 `functools` 模块：`lru_cache` / `partial` / `reduce` / `wraps`](./38-functools.md)
- [ ] [1.1.23 多线程 vs 多进程 vs 异步](./39-concurrency.md)
- [ ] [1.1.24 GIL 全局解释器锁](./40-gil.md)
- [ ] [1.1.25 Python 内存管理与 GC](./41-memory-management.md)
- [ ] [1.1.26 Python 性能调优：`cProfile` / `timeit` / `perf_counter`](./42-performance-tuning.md)

## 模块 1.2 数据序列化与配置

- [ ] [1.2.1 JSON 处理：序列化、反序列化、嵌套结构](./17-json-processing.md)
- [ ] [1.2.2 YAML / TOML 配置文件](./18-config-file-format.md)
- [ ] [1.2.3 环境变量与 12-Factor 配置原则](./19-env-vars.md)
- [ ] [1.2.4 `pydantic-settings`：类型安全的配置管理](./20-pydantic-settings.md)

## 模块 1.3 命令行与 Shell

- [ ] [1.3.1 Linux 常用命令：`grep` / `awk` / `sed` / `find`](./21-linux-commands.md)
- [ ] [1.3.2 Shell 脚本：变量、条件、循环、函数](./22-shell-scripting.md)
- [ ] [1.3.3 进程管理：`ps` / `top` / `kill` / `systemctl`](./23-process-management.md)
- [ ] [1.3.4 网络命令：`curl` / `wget` / `netstat` / `ss`](./24-network-commands.md)

## 模块 1.4 网络协议基础

- [ ] [1.4.1 HTTP/HTTPS 协议：方法、状态码、Header、Cookie](./25-http-protocol.md)
- [ ] [1.4.2 REST API 设计规范与最佳实践](./26-rest-api-design.md)
- [ ] [1.4.3 WebSocket 协议](./27-websocket.md)
- [ ] [1.4.4 Server-Sent Events（SSE）与流式响应](./28-sse.md)
- [ ] [1.4.5 gRPC 与 Protocol Buffers 入门](./29-grpc-protobuf.md)

## 模块 1.5 版本控制与协作

- [ ] [1.5.1 Git 进阶：`rebase` / `cherry-pick` / `bisect`](./30-git-advanced.md)
- [ ] [1.5.2 Git 工作流：Git Flow / GitHub Flow / Trunk-based](./31-git-workflow.md)
- [ ] [1.5.3 Conventional Commits 与语义化版本](./32-conventional-commits.md)

## 🎯 dify 仓库对应位置

- 后端 Python 代码：`/Users/xu/code/github/dify/api/`
- 包管理配置：`/Users/xu/code/github/dify/api/pyproject.toml`
- 配置加载：`/Users/xu/code/github/dify/api/configs/`
- 日志与工具库：`/Users/xu/code/github/dify/api/libs/`
