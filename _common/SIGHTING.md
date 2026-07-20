# Sighting（露面）原则与主题归属

> 用于解决「后置专题在前文出现却未给出学习入口」的问题。  
> 所有学习文档在**提及**其他专题才正式讲授的概念时，应使用 Sighting 写法。

## 0. 三层与 Mastery 唯一

| 层 | 目录 | Mastery 写什么 |
|----|------|----------------|
| 学科基础 | `_fundamentals/` | 机制、协议、引擎、经典理论 |
| 工程公共 | `_common/` | 选型、用法、跨语言工程约定 |
| 项目实战 | `dify/` / `ruoyi-vue-pro/` | 框架 API + 本仓库源码 |

**硬规则补强**：同一概念的 **Mastery 只允许存在于一个归属文档**。其他文档只能 Sighting 或 Minimal。

## 1. 三种出现级别

| 级别 | 含义 | 允许位置 | 写法 |
|------|------|----------|------|
| **Sighting（露面）** | 源码/示例中出现，不展开机制 | 任意更早或并列文档 | 一句话说明用途 + `详见 [标题](相对路径)` |
| **Minimal（够用）** | 为理解本文目标必须说一点 | 有限 | 1～2 句直觉，**不写实现练习**，必须链到专题 |
| **Mastery（掌握）** | 原理、变体、关键要点、动手练习 | **仅**该主题归属文档 | 完整讲解 |

**硬规则**：

1. **学习目标 / 关键要点 / 练习题** 不得要求「掌握」后置专题。
2. 后置概念若必须出现 → 降为 Sighting 或 Minimal，并加链接。
3. **同一文档内同一主题只加一次** 主要链接（首次显著出现处），避免刷屏。
4. 链接指向该主题的**归属文档**（见下表），用相对路径。
5. 归属文档自身不需要再链到自己。

## 2. 推荐链接句式

行内：

```markdown
`@staticmethod` 是装饰器写法（详见 [装饰器](./10-decorator.md)），此处只把它当作「挂在类上的函数」来理解。
```

段落末：

```markdown
> 📌 **Sighting**：完整装饰器原理（闭包、`@wraps`、带参装饰器）见 [10-decorator](./10-decorator.md)。
```

练习改派：

```markdown
> 学完 [10-decorator](./10-decorator.md) 后再做：实现 `@timed` …
```

## 3. 主题归属（Canonical Home）

### 3.0 易重叠主题（优先查本表）

| 主题关键词 | Mastery 归属 | 工程/应用入口（非 Mastery） |
|------------|--------------|------------------------------|
| HTTP 方法/状态码/Header、HTTP 版本、HTTPS/TLS 握手 | `_fundamentals/04-computer-network/` | `_common/14-api-protocols/`（REST/SSE/gRPC） |
| WebSocket 协议 | `_fundamentals/04-computer-network/09-websocket.md` | `_common/14-api-protocols/03-websocket.md`（工程示例可 Minimal） |
| REST 设计、SSE、gRPC | `_common/14-api-protocols/` | — |
| 关系代数、范式细节、InnoDB/PG 存储、B+Tree、MVCC、隔离级别实现 | `_fundamentals/05-database-theory/` | `_common/21-sql/` |
| SQL CRUD/JOIN、软删、分片选型、库表工程 | `_common/21-sql/` | — |
| 字符编码、序列化格式、哈希/对称/非对称/签名原理、TLS | `_fundamentals/07-encoding-and-crypto/` | `_common/06-encryption/` |
| 密钥管理落地、业务侧加密选型 | `_common/06-encryption/05-key-management.md` | 原理链 fundamentals |
| GoF 模式、SOLID 清单 | `_fundamentals/06-design-patterns/` | `_common/22-architecture/` 中仅 Sighting |
| DDD、分层、仓储、DI、领域事件 | `_common/22-architecture/` | — |
| 进程/线程/内存/IO 模型 | `_fundamentals/03-operating-system/` | `_common/13-linux-shell/`（命令工具） |
| Shell/Git/测试理论/可观测/协作 | `_common/13`–`20` | — |

### 3.1 dify / Python 基础（`dify/01-fundamentals/`）

| 主题关键词 | 归属文档 |
|------------|----------|
| 变量、类型、list/dict | `01-python-variables-and-types.md` |
| 函数、*args、**kwargs、LEGB | `02-python-functions.md` |
| class、实例、继承入门 | `03-python-classes-basics.md` |
| import、包 | `04-python-modules-and-imports.md` |
| if/for/while、推导式、with 用法 | `05-python-control-flow.md` |
| try/except/raise、自定义异常 | `06-python-exceptions.md` |
| typing、Optional、Union、Callable | `07-python-typing-basics.md` |
| TypedDict | `08-typeddict.md` |
| Protocol、Generic | `09-protocol-generic.md` |
| 装饰器、@wraps、@login_required 原理 | `10-decorator.md` |
| 上下文管理器、contextmanager、__enter__ | `11-context-manager.md` |
| async/await、asyncio | `12-async-asyncio.md` |
| Task、Future、事件循环 | `13-async-task-future.md` |
| 生成器、yield、异步生成器 | `14-generator.md` |
| uv、pyproject.toml | `15-uv-package-management.md` |
| 魔术方法、dunder | `16-dunder-methods.md` |
| JSON（Python `json`） | `17-json-processing.md` |
| pydantic-settings | `18-pydantic-settings.md` |
| 元类 | `19-metaclass.md` |
| 描述符 | `20-descriptor.md` |
| ABC、abstractmethod | `21-abc.md` |
| dataclass | `22-dataclasses.md` |
| itertools | `23-itertools.md` |
| functools、lru_cache、partial、wraps 专题 | `24-functools.md` |
| 多线程/多进程/并发模型 | `25-concurrency.md` |
| GIL | `26-gil.md` |
| 内存管理、GC | `27-memory-management.md` |
| 性能调优、cProfile | `28-performance-tuning.md` |

YAML/TOML、环境变量与 12-Factor → **`_common/17-config/`**（非本表）。

### 3.2 设计模式（`_fundamentals/06-design-patterns/`）

| 主题 | 归属 |
|------|------|
| 单例 | `01-singleton.md` |
| 工厂方法 | `02-factory-method.md` |
| 抽象工厂 | `03-abstract-factory.md` |
| 建造者 | `04-builder.md` |
| 适配器 | `06-adapter.md` |
| 装饰器模式 | `07-decorator.md` |
| 代理 | `08-proxy.md` |
| 策略 | `13-strategy.md` |
| 模板方法 | `14-template-method.md` |
| 观察者 | `15-observer.md` |
| 责任链 | `17-chain.md` |
| SOLID | `24-solid.md` |

### 3.3 学科基础其他（`_fundamentals/` 摘要）

| 主题 | 归属 |
|------|------|
| 数据结构 / 算法 | `01-data-structures/`、`02-algorithms/` |
| 进程线程、虚拟内存、IO 模型 | `03-operating-system/` |
| OSI/TCP、HTTP 体系、DNS | `04-computer-network/` |
| 存储引擎、MVCC、索引结构 | `05-database-theory/` |
| 编码、序列化、密码学原理 | `07-encoding-and-crypto/` |
| 正则 | `08-regular-expression/` |

### 3.4 工程公共（`_common/`）

| 主题 | 归属目录/文档 |
|------|----------------|
| Redis 数据结构/持久化/集群 | `_common/01-redis/` |
| MQ / Kafka / RabbitMQ | `_common/02-mq/` |
| 缓存策略/三大问题/限流 | `_common/03-cache-patterns/` |
| 分布式锁 | `_common/04-distributed-locks/` |
| XSS/CSRF/SQLi/SSRF/CORS | `_common/05-web-security/` |
| 加密应用 / 密钥管理入口 | `_common/06-encryption/`（原理 → fundamentals 07） |
| HTTP Auth / Session / JWT / OAuth | `_common/07-authentication/` |
| RBAC / ABAC / 多租户 | `_common/08-authorization/` |
| Docker | `_common/09-containerization/` |
| Nginx | `_common/10-network-proxy/` |
| CI/CD | `_common/11-cicd/` |
| 蓝绿/金丝雀/滚动 | `_common/12-deploy-strategies/` |
| Linux / Shell / 进程 / 网络命令 | `_common/13-linux-shell/` |
| REST、SSE、gRPC；HTTP 工程速查 | `_common/14-api-protocols/` |
| Git 进阶、工作流、Conventional Commits | `_common/15-git/` |
| Kubernetes / Helm | `_common/16-kubernetes/` |
| YAML/TOML、环境变量、12-Factor | `_common/17-config/` |
| 测试金字塔 / TDD / 覆盖率 / 性能与安全测试 | `_common/18-testing/` |
| 日志级别、指标、Prometheus、追踪、告警 | `_common/19-observability/` |
| 命名/重构/CR/PR/ADR/估时等工程实践 | `_common/20-engineering/` |
| SQL 实用与库表设计（软删/锁/分片） | `_common/21-sql/` |
| DDD / 分层 / 仓储 / DI / 领域事件 | `_common/22-architecture/` |

### 3.5 跨项目

- **dify** 中的通用中间件/安全/部署 → 先链 `_common/`，再链本项目 `*-in-dify`。
- **ruoyi** 同理：理论在 `_fundamentals` / `_common`，实战在 `ruoyi-vue-pro/`。
- **Python 语言机制** → `dify/01-fundamentals/`；**Java** → `ruoyi-vue-pro/01-java-fundamentals/` 与 Spring 各章。
- 出现「原理 + 工程」双主题时：原理链 fundamentals，工程链 common，**不要各写一整套 Mastery**。

## 4. 编辑检查清单（每篇）

- [ ] 正文是否出现「归属在其他文档」的概念？
- [ ] 首次显著出现处是否有 `详见 […](…)`？
- [ ] 学习目标 / 关键要点 / 练习是否越权要求掌握后置主题？
- [ ] 若有越权练习 → 改为「学完 XXX 后再做」或移入归属文档
- [ ] 相对路径是否从**当前文件**出发正确？
- [ ] 若与 fundamentals/common 重叠 → 是否遵守 §3.0 Mastery 唯一？
