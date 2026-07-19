# 01 - Python 语言与工程基础

> dify 后端的 **Python 语言与配置** 地基。跨语言通用技能见 `_common` / `_fundamentals`。

## 学习顺序（文件号 = 阅读顺序）

```
01–06  Python 入门
07–16  Python 核心（类型 / 异步 / 包管理 / 魔术方法）
17–26  Python 进阶（元类 → 性能调优）
27–30  序列化与配置
```

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
- [ ] [1.1.17 元类（Metaclass）与类创建过程](./17-metaclass.md)
- [ ] [1.1.18 描述符（Descriptor）协议](./18-descriptor.md)
- [ ] [1.1.19 抽象基类（abc 模块）](./19-abc.md)
- [ ] [1.1.20 `dataclass` 数据类](./20-dataclasses.md)
- [ ] [1.1.21 `itertools` 模块：迭代器工具箱](./21-itertools.md)
- [ ] [1.1.22 `functools` 模块：`lru_cache` / `partial` / `reduce` / `wraps`](./22-functools.md)
- [ ] [1.1.23 多线程 vs 多进程 vs 异步](./23-concurrency.md)
- [ ] [1.1.24 GIL 全局解释器锁](./24-gil.md)
- [ ] [1.1.25 Python 内存管理与 GC](./25-memory-management.md)
- [ ] [1.1.26 Python 性能调优：`cProfile` / `timeit` / `perf_counter`](./26-performance-tuning.md)

## 模块 1.2 数据序列化与配置

- [ ] [1.2.1 JSON 处理：序列化、反序列化、嵌套结构](./27-json-processing.md)
- [ ] [1.2.2 YAML / TOML 配置文件](./28-config-file-format.md)
- [ ] [1.2.3 环境变量与 12-Factor 配置原则](./29-env-vars.md)
- [ ] [1.2.4 `pydantic-settings`：类型安全的配置管理](./30-pydantic-settings.md)

## 🌐 公共部分（已迁出）

> 以下为跨语言通用技能，不绑定 Python / dify。

### Linux / Shell

| 主题 | 文档 |
|------|------|
| Linux 文本处理与查找 | [`_common/13-linux-cli/01-linux-commands`](../../_common/13-linux-cli/01-linux-commands.md) |
| Shell 脚本 | [`_common/13-linux-cli/02-shell-scripting`](../../_common/13-linux-cli/02-shell-scripting.md) |
| 进程管理 | [`_common/13-linux-cli/03-process-management`](../../_common/13-linux-cli/03-process-management.md) |
| 网络命令 | [`_common/13-linux-cli/04-network-commands`](../../_common/13-linux-cli/04-network-commands.md) |

→ [`_common/13-linux-cli/`](../../_common/13-linux-cli/README.md)

### API 与应用层协议

| 主题 | 文档 |
|------|------|
| HTTP/HTTPS | [`_common/14-api-protocols/01-http-protocol`](../../_common/14-api-protocols/01-http-protocol.md) |
| REST API 设计 | [`_common/14-api-protocols/02-rest-api-design`](../../_common/14-api-protocols/02-rest-api-design.md) |
| WebSocket | [`_common/14-api-protocols/03-websocket`](../../_common/14-api-protocols/03-websocket.md) |
| SSE 流式响应 | [`_common/14-api-protocols/04-sse`](../../_common/14-api-protocols/04-sse.md) |
| gRPC / Protobuf | [`_common/14-api-protocols/05-grpc-protobuf`](../../_common/14-api-protocols/05-grpc-protobuf.md) |

→ [`_common/14-api-protocols/`](../../_common/14-api-protocols/README.md)  
网络理论另见 [`_fundamentals/04-computer-network/`](../../_fundamentals/04-computer-network/)

### Git 与协作

| 主题 | 文档 |
|------|------|
| Git 进阶 | [`_common/15-git/01-git-advanced`](../../_common/15-git/01-git-advanced.md) |
| Git 工作流 | [`_common/15-git/02-git-workflow`](../../_common/15-git/02-git-workflow.md) |
| Conventional Commits / SemVer | [`_common/15-git/03-conventional-commits`](../../_common/15-git/03-conventional-commits.md) |

→ [`_common/15-git/`](../../_common/15-git/README.md)

## 🎯 dify 仓库对应位置

- 后端 Python 代码：`/Users/xu/code/github/dify/api/`
- 包管理配置：`/Users/xu/code/github/dify/api/pyproject.toml`
- 配置加载：`/Users/xu/code/github/dify/api/configs/`
- 日志与工具库：`/Users/xu/code/github/dify/api/libs/`
