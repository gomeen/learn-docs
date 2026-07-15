# Sighting（露面）原则与主题归属

> 用于解决「后置专题在前文出现却未给出学习入口」的问题。  
> 所有学习文档在**提及**其他专题文档才正式讲授的概念时，应使用 Sighting 写法。

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
| JSON | `17-json-processing.md` |
| YAML、TOML | `18-config-file-format.md` |
| 环境变量、12-Factor | `19-env-vars.md` |
| pydantic-settings | `20-pydantic-settings.md` |
| 元类 | `33-metaclass.md` |
| 描述符 | `34-descriptor.md` |
| ABC、abstractmethod | `35-abc.md` |
| dataclass | `36-dataclasses.md` |
| itertools | `37-itertools.md` |
| functools、lru_cache、partial、wraps 专题 | `38-functools.md` |
| 多线程/多进程/并发模型 | `39-concurrency.md` |
| GIL | `40-gil.md` |
| 内存管理、GC | `41-memory-management.md` |
| 性能调优、cProfile | `42-performance-tuning.md` |
| HTTP | `25-http-protocol.md` |
| REST | `26-rest-api-design.md` |
| WebSocket | `27-websocket.md` |
| SSE | `28-sse.md` |
| gRPC、Protobuf | `29-grpc-protobuf.md` |

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

### 3.3 公共基础设施（`_common/`）

| 主题 | 归属目录/文档 |
|------|----------------|
| Redis 数据结构/持久化/集群 | `_common/01-redis/` |
| MQ / Kafka / RabbitMQ | `_common/02-mq/` |
| 缓存策略/三大问题/限流 | `_common/03-cache-patterns/` |
| 分布式锁 | `_common/04-distributed-locks/` |
| XSS/CSRF/SQLi/SSRF/CORS | `_common/05-web-security/` |
| 对称/非对称/哈希/签名 | `_common/06-encryption/` |
| HTTP Auth / Session / JWT / OAuth | `_common/07-authentication/` |
| RBAC / ABAC / 多租户 | `_common/08-authorization/` |
| Docker | `_common/09-containerization/` |
| Nginx | `_common/10-network-proxy/` |
| CI/CD | `_common/11-cicd/` |
| 蓝绿/金丝雀/滚动 | `_common/12-deploy-strategies/` |

### 3.4 跨项目

- **dify 路径**中的通用中间件知识 → 优先链 `_common/` 对应文档，再链本项目 `*-in-dify` 实战篇。
- **ruoyi** 同理：理论在 `_common` / `_fundamentals`，实战在 `ruoyi-vue-pro/`。
- **Python 语言机制**（装饰器、async、dataclass…）无论出现在哪一分类，归属仍是 `dify/01-fundamentals/` 中对应篇（若读者路径是 dify）；ruoyi 路径中的 Python 少见，Java 主题归 `ruoyi-vue-pro/01-java-fundamentals/` 与 Spring 各章。

## 4. 编辑检查清单（每篇）

- [ ] 正文是否出现「归属在其他文档」的概念？
- [ ] 首次显著出现处是否有 `详见 […](…)`？
- [ ] 学习目标 / 关键要点 / 练习是否越权要求掌握后置主题？
- [ ] 若有越权练习 → 改为「学完 XXX 后再做」或移入归属文档
- [ ] 相对路径是否从**当前文件**出发正确？
