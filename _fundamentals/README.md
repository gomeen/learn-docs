# _fundamentals - 学科基础（理论层）

> **Mastery 层：讲清「为什么、底层怎么工作」**。跨语言、跨项目；偏计算机学科与经典理论，不绑定具体中间件产品或业务仓库。

## 🎯 三层知识模型

| 层 | 目录 | 回答什么 | 典型内容 |
|----|------|----------|----------|
| **学科基础** | 本目录 `_fundamentals/` | Why / How it works | 数据结构、OS、网络协议栈、存储引擎、GoF、密码学原理 |
| **工程公共** | [`../_common/`](../_common/) | What to use / How we build | Redis、安全模型、CI/CD、SQL 实用、测试与协作 |
| **项目实战** | `dify/`、`ruoyi-vue-pro/` | How this stack does it | Flask/Spring、Celery、Redisson、`*-in-dify` |

> 两层都是「通用知识」——差别不在是否通用，而在 **理论 vs 工程**。  
> 语言语法（Python / Java）不在本目录，分别见 `dify/01-fundamentals`、`ruoyi-vue-pro/01-java-fundamentals`。

## 📐 与 `_common` 的边界（写文档时用）

| 放 `_fundamentals` | 放 `_common` |
|--------------------|--------------|
| 协议栈、引擎、算法与密码学**机制** | 中间件、接口设计、部署与协作**用法** |
| 不依赖 Redis/Docker/某框架也能讲完 | 选型、落地、跨语言工程约定 |
| 面试/原理课重心 | 日常开发直接用到的组件与流程 |

**重叠主题的 Mastery 归属**（另一侧只允许 Sighting / Minimal）：

| 主题 | Mastery | 工程侧入口 |
|------|---------|------------|
| HTTP 语义 / 版本 / Header / HTTPS 握手 | 本目录 `04-computer-network` | `_common/14-api-protocols`（REST/SSE/gRPC） |
| WebSocket 协议细节 | `04-computer-network/09-websocket` | `_common/14` 可保留工程示例 |
| 范式、B+Tree、MVCC、隔离级别实现 | `05-database-theory` | `_common/21-sql`（SQL 与库表工程） |
| 哈希 / 对称 / 非对称 / 签名 / TLS | `07-encoding-and-crypto` | `_common/06-encryption`（应用与密钥管理视角） |
| GoF / SOLID 模式清单 | `06-design-patterns` | `_common/22-architecture`（DDD/分层） |

详见 [`../_common/SIGHTING.md`](../_common/SIGHTING.md)。

## 📚 知识分类

| 分类 | 主题 | 目录 |
|------|------|------|
| **01** | 数据结构 | [`01-data-structures/`](./01-data-structures/) |
| **02** | 算法基础 | [`02-algorithms/`](./02-algorithms/) |
| **03** | 操作系统 | [`03-operating-system/`](./03-operating-system/) |
| **04** | 计算机网络 | [`04-computer-network/`](./04-computer-network/) |
| **05** | 数据库原理 | [`05-database-theory/`](./05-database-theory/) |
| **06** | 设计模式 | [`06-design-patterns/`](./06-design-patterns/) |
| **07** | 编码与加密 | [`07-encoding-and-crypto/`](./07-encoding-and-crypto/) |
| **08** | 正则表达式 | [`08-regular-expression/`](./08-regular-expression/) |

## 📖 推荐学习顺序

```
_fundamentals（本目录）
    01-02 数据结构与算法
        ↓
    03-04 操作系统 + 计算机网络
        ↓
    05 数据库原理 · 06 设计模式
        ↓
    07 编码与加密 · 08 正则
        ↓
_common（工程公共：中间件 / 安全 / 部署 / SQL 实用 / 协作）
        ↓
项目目录（dify 或 ruoyi：语言 + 框架 + 仓库实战）
```

## 🔗 与项目目录的关系

- **dify**（Python）：[`../dify/01-fundamentals/`](../dify/01-fundamentals/)（语言）+ 本目录（理论）+ [`../_common/`](../_common/)（工程）
- **ruoyi-vue-pro**（Java）：[`../ruoyi-vue-pro/01-java-fundamentals/`](../ruoyi-vue-pro/01-java-fundamentals/) + 本目录 + `_common`

## 💡 学习建议

1. **入门后端**：先 01–04，再进 `_common` 的 Redis / 安全 / 部署
2. **面试冲刺**：重点 01–02–05–06
3. **查漏补缺**：按主题检索；出现工程概念时跟 Sighting 链到 `_common`
