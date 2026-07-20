# _common - 工程公共（实践层）

> **Mastery 层：讲清「后端系统里怎么用、怎么选型」**。跨语言、跨项目；可有多语言示例，但不绑定单一业务仓库。

## 🎯 与 `_fundamentals` 的区别

| 目录 | 定位 | 内容气质 |
|------|------|----------|
| [`../_fundamentals/`](../_fundamentals/) | **学科基础** | 原理课：数据结构、OS、网络栈、存储引擎、GoF、密码学机制 |
| **本目录 `_common/`** | **工程公共** | 工程课：中间件、安全模型、API 设计、配置、测试、可观测、协作 |
| `dify/` / `ruoyi-vue-pro/` | **项目实战** | 某语言 + 某框架 + 仓库源码（如 Celery、Redisson、`*-in-dify`） |

**不要用「是否通用」区分两层**——两层都通用。  
用这句话判断归属：

- 不依赖具体中间件/产品，也能讲完「机器与协议如何工作」→ **`_fundamentals`**
- 讲「系统里怎么用、怎么选型、怎么落地」→ **`_common`**
- 依赖 Python/Java/某仓库路径 → **项目目录**

### 重叠主题：Mastery 只留一处

| 主题 | 理论 Mastery | 本目录角色 |
|------|----------------|------------|
| HTTP / HTTPS / WebSocket 协议细节 | `_fundamentals/04-computer-network` | `14-api-protocols`：REST / SSE / gRPC + 工程速查 |
| 范式 / B+Tree / MVCC / 隔离级别实现 | `_fundamentals/05-database-theory` | `21-sql`：SQL 与库表工程（软删、分片选型） |
| 哈希 / 对称 / 非对称 / 签名 / TLS | `_fundamentals/07-encoding-and-crypto` | `06-encryption`：应用视角与密钥管理入口 |
| GoF / SOLID | `_fundamentals/06-design-patterns` | `22-architecture`：DDD / 分层 / DI（链模式篇） |

完整 Sighting 规则见 [`SIGHTING.md`](./SIGHTING.md)。

## 📚 知识分类

### A. 中间件与分布式

| 分类 | 主题 | 目录 |
|------|------|------|
| **01** | Redis | [`01-redis/`](./01-redis/) |
| **02** | 消息队列 | [`02-mq/`](./02-mq/) |
| **03** | 缓存模式 | [`03-cache-patterns/`](./03-cache-patterns/) |
| **04** | 分布式锁 | [`04-distributed-locks/`](./04-distributed-locks/) |

### B. 安全

| 分类 | 主题 | 目录 |
|------|------|------|
| **05** | Web 安全 | [`05-web-security/`](./05-web-security/) |
| **06** | 加密（应用向） | [`06-encryption/`](./06-encryption/) |
| **07** | 认证 | [`07-authentication/`](./07-authentication/) |
| **08** | 授权 | [`08-authorization/`](./08-authorization/) |

### C. 交付与基础设施

| 分类 | 主题 | 目录 |
|------|------|------|
| **09** | 容器化 | [`09-containerization/`](./09-containerization/) |
| **10** | 网络代理 | [`10-network-proxy/`](./10-network-proxy/) |
| **11** | CI/CD | [`11-cicd/`](./11-cicd/) |
| **12** | 部署策略 | [`12-deploy-strategies/`](./12-deploy-strategies/) |
| **16** | Kubernetes / Helm | [`16-kubernetes/`](./16-kubernetes/) |

### D. 工程通识

| 分类 | 主题 | 目录 |
|------|------|------|
| **13** | Linux / Shell | [`13-linux-shell/`](./13-linux-shell/) |
| **14** | API 与应用层协议 | [`14-api-protocols/`](./14-api-protocols/) |
| **15** | Git 与协作规范 | [`15-git/`](./15-git/) |
| **17** | 配置管理 | [`17-config/`](./17-config/) |
| **18** | 测试理论 | [`18-testing/`](./18-testing/) |
| **19** | 可观测性 | [`19-observability/`](./19-observability/) |
| **20** | 工程实践与协作 | [`20-engineering/`](./20-engineering/) |
| **21** | SQL 与库表设计 | [`21-sql/`](./21-sql/) |
| **22** | 后端架构模式 | [`22-architecture/`](./22-architecture/) |

## 🔗 与项目目录的关系

- **dify**（Python）：中间件 / 安全 / DevOps / 测试理论等链到本目录；语言与 `*-in-dify` 留在 `../dify/`
- **ruoyi-vue-pro**（Java）：`05-cache-and-mq`、`06-security`、`10-devops` 等链到本目录；Java/Spring 专属留在项目路径

## 💡 使用建议

1. **先 `_fundamentals`，再本目录**（先原理后工程；面试可并行刷 01–02）
2. **本目录学通用做法** → 再回项目目录看栈内实现
3. **同一概念两边都有** → 只在 Mastery 归属文档做完整练习；另一侧只链过去
