# 01 - 编程语言与基础工具

> 全栈后端开发的「地基」。所有其他分类的知识都依赖这里的内容。
> **主路径**：全局顺序与「必读/延后」以 [`../LEARNING-PLAN.md`](../LEARNING-PLAN.md) 为准。
> 下方清单是**本分类素材目录**；未列入主计划的篇默认不读。需要做小验证时，优先做主计划点名的 `NN-*-*.md`。

## 节奏说明（小验证怎么做）

- **默认主路径**：在真实仓库 `/Users/xu/code/github/dify`（后端代码在 `api/`）里完成——定位文件/函数、只读 NOTES、做**无害小改** / **找错再修** / **对照改写**，再用 pytest、`python -c`、阅读笔记等方式验收。
- **不是**默认从零新建独立小项目/包；「本地造轮子」若出现，只在各练习文末 **延伸（选做）**。
- **约束**：练习改动请在本地分支或改完还原，**不要**把学习用 hack commit 进 dify 主线；本学习库任务也不要求你改 dify 业务并提交。
- **预计**：每个 `NN-*-*.md` 小验证约 30～60 分钟（读完对应覆盖文档之后）。
- **路径漂移**：练习里给了优先真实路径；若你本地 dify 版本不一致，用文中的 `rg` 关键词在 `api/` 下重定位。

## 📚 Python 基础（主计划 Phase 1 子集）

> 全局顺序见 [`../LEARNING-PLAN.md`](../LEARNING-PLAN.md) Phase 1。初学者先做 01–07；08/11 与装饰器相关再学。下列其余模块默认**延后**。

- [ ] [0.1 Python 变量与数据类型](./01-python-variables-and-types.md)
- [ ] [0.2 Python 函数基础](./02-python-functions.md)
- [ ] [0.3 Python 类与对象基础](./03-python-classes-basics.md)
- [ ] [0.4 Python 模块、包与导入](./04-python-modules-and-imports.md)
- [ ] [0.5 Python 控制流（if/for/while/with）](./05-python-control-flow.md)
- [ ] [0.6 Python 异常处理（try/except/raise）](./06-python-exceptions.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [07-*-python-basics: Python 入门基础](./07-*-python-basics.md)
  - 覆盖：01–06 · **在 `api/libs/` 读工具函数并做无害小改**（`mini_config` 仅延伸）


## 模块 1.1 Python 核心

- [ ] [1.1.7 Python 类型系统：`typing` 模块基础](./08-python-typing-basics.md)
- [ ] [1.1.8 `TypedDict` 与 `NotRequired`：结构化字典](./09-typeddict.md)
- [ ] [1.1.9 `Protocol` 与 `Generic`：行为抽象与泛型](./10-protocol-generic.md)
- [ ] [1.1.10 装饰器（Decorator）的原理与实践](./11-decorator.md)
- [ ] [1.1.11 上下文管理器（Context Manager）与 `with` 语句](./12-context-manager.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [13-*-typing-decorator-context: 类型系统 · 装饰器 · 上下文管理器](./13-*-typing-decorator-context.md)
  - 覆盖：08–12 · **TypedDict/Protocol/`@wraps`/contextmanager 对照真实 `context/`、`controllers/*/wraps.py`**


- [ ] [1.1.12 Python 异步编程：`asyncio` / `async/await`](./14-async-asyncio.md)
- [ ] [1.1.13 协程、Task、Future 与事件循环](./15-async-task-future.md)
- [ ] [1.1.14 生成器与 `yield`、异步生成器](./16-generator.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [17-*-async-generators: 异步 · Task/Future · 生成器](./17-*-async-generators.md)
  - 覆盖：14–16 · **SSE 同步生成器 + embedding async 接口 + ThreadPoolExecutor**（纯 asyncio 脚本仅延伸）


- [ ] [1.1.15 Python 包管理：`uv` 与 `pyproject.toml`](./18-uv-package-management.md)
- [ ] [1.1.16 魔术方法：`__init__` / `__repr__` / `__str__` / `__eq__`](./19-dunder-methods.md)

## 模块 1.2 数据序列化与配置

> 与上文 15–16 同组验证：（包管理、dunder、JSON、Settings）。

- [ ] [1.2.1 JSON 处理：序列化、反序列化、嵌套结构](./20-json-processing.md)
- [ ] [1.2.2 YAML / TOML 配置文件](../../_common/17-config/01-config-file-format.md)
- [ ] [1.2.3 环境变量与 12-Factor 配置原则](../../_common/17-config/02-env-vars.md)
- [ ] [1.2.4 `pydantic-settings`：类型安全的配置管理](./21-pydantic-settings.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [22-*-packaging-config: 包管理 · 魔术方法 · JSON · Settings](./22-*-packaging-config.md)
  - 覆盖：18–21 · **`pyproject.toml` + `configs/` pydantic-settings + OAuth JSON/dataclass**


## 模块 1.1 续：Python 进阶

- [ ] [1.1.17 元类（Metaclass）与类创建过程](./23-metaclass.md)
- [ ] [1.1.18 描述符（Descriptor）协议](./24-descriptor.md)
- [ ] [1.1.19 抽象基类（abc 模块）](./25-abc.md)
- [ ] [1.1.20 `dataclass` 数据类](./26-dataclasses.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [27-*-oop-advanced: 元类 · 描述符 · ABC · dataclass](./27-*-oop-advanced.md)
  - 覆盖：23–26 · **Moderation ABC + dataclass + TypeDecorator；元类/描述符教材造轮子仅延伸**


- [ ] [1.1.21 `itertools` 模块：迭代器工具箱](./28-itertools.md)
- [ ] [1.1.22 `functools` 模块：`lru_cache` / `partial` / `reduce` / `wraps`](./29-functools.md)
- [ ] [1.1.23 多线程 vs 多进程 vs 异步](./30-concurrency.md)
- [ ] [1.1.24 GIL 全局解释器锁](./31-gil.md)
- [ ] [1.1.25 Python 内存管理与 GC](./32-memory-management.md)
- [ ] [1.1.26 Python 性能调优：`cProfile` / `timeit` / `perf_counter`](./33-performance-tuning.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [34-*-stdlib-concurrency-perf: itertools/functools · 并发 · GIL · 内存/性能](./34-*-stdlib-concurrency-perf.md)
  - 覆盖：28–33 · **`chunked`/islice、`lru_cache`、ThreadPool、gevent 入口对照**


## 🌐 公共部分（已迁至 `_common`）

> 下列主题与具体语言/框架无关，正文在 [`../../_common/`](../../_common/)。学习 dify 时建议仍按此顺序阅读。

| 主题 | 公共文档 |
|------|----------|
| Linux 命令与 Shell | [`_common/13-linux-shell`](../../_common/13-linux-shell/) |
| API / HTTP / REST / WebSocket / SSE / gRPC | [`_common/14-api-protocols`](../../_common/14-api-protocols/) |
| Git 进阶、工作流、Conventional Commits | [`_common/15-git`](../../_common/15-git/) |

### 模块 1.3 命令行与 Shell

- [ ] [1.3.1 Linux 常用命令：`grep` / `awk` / `sed` / `find`](../../_common/13-linux-shell/01-linux-commands.md)
- [ ] [1.3.2 Shell 脚本：变量、条件、循环、函数](../../_common/13-linux-shell/02-shell-scripting.md)
- [ ] [1.3.3 进程管理：`ps` / `top` / `kill` / `systemctl`](../../_common/13-linux-shell/03-process-management.md)
- [ ] [1.3.4 网络命令：`curl` / `wget` / `netstat` / `ss`](../../_common/13-linux-shell/04-network-commands.md)

### 模块 1.4 网络协议基础

- [ ] [1.4.1 HTTP/HTTPS 协议：方法、状态码、Header、Cookie](../../_common/14-api-protocols/01-http-protocol.md)
- [ ] [1.4.2 REST API 设计规范与最佳实践](../../_common/14-api-protocols/02-rest-api-design.md)
- [ ] [1.4.3 WebSocket 协议](../../_common/14-api-protocols/03-websocket.md)
- [ ] [1.4.4 Server-Sent Events（SSE）与流式响应](../../_common/14-api-protocols/04-sse.md)
- [ ] [1.4.5 gRPC 与 Protocol Buffers 入门](../../_common/14-api-protocols/05-grpc-protobuf.md)

### 模块 1.5 版本控制与协作

- [ ] [1.5.1 Git 进阶：`rebase` / `cherry-pick` / `bisect`](../../_common/15-git/01-git-advanced.md)
- [ ] [1.5.2 Git 工作流：Git Flow / GitHub Flow / Trunk-based](../../_common/15-git/02-git-workflow.md)
- [ ] [1.5.3 Conventional Commits 与语义化版本](../../_common/15-git/03-conventional-commits.md)

## 🎯 dify 仓库对应位置

- 后端 Python 代码：`/Users/xu/code/github/dify/api/`
- 包管理配置：`/Users/xu/code/github/dify/api/pyproject.toml`
- 配置加载：`/Users/xu/code/github/dify/api/configs/`
- 日志与工具库：`/Users/xu/code/github/dify/api/libs/`
