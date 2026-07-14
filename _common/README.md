# _common - 跨项目通用知识

> dify 和 ruoyi-vue-pro 两个项目**真正通用**的内容。无论后端用什么语言/框架，这些知识都适用。

## 🎯 与 _fundamentals 的区别

| 目录 | 内容 |
|------|------|
| `_fundamentals/` | **基础学科知识**（数据结构、算法、操作系统、网络）—— 与编程无关 |
| `_common/` | **后端通用组件**（Redis、MQ、安全、加密、CI/CD）—— 跨语言通用，但已涉及代码示例 |

## 📚 知识分类

| 分类 | 主题 | 目录 |
|------|------|------|
| **01** | Redis 通用知识 | [`01-redis/`](./01-redis/) |
| **02** | 消息队列 | [`02-mq/`](./02-mq/) |
| **03** | 缓存模式 | [`03-cache-patterns/`](./03-cache-patterns/) |
| **04** | 分布式锁 | [`04-distributed-locks/`](./04-distributed-locks/) |
| **05** | Web 安全 | [`05-web-security/`](./05-web-security/) |
| **06** | 加密 | [`06-encryption/`](./06-encryption/) |
| **07** | 认证 | [`07-authentication/`](./07-authentication/) |
| **08** | 授权 | [`08-authorization/`](./08-authorization/) |
| **09** | 容器化 | [`09-containerization/`](./09-containerization/) |
| **10** | 网络代理 | [`10-network-proxy/`](./10-network-proxy/) |
| **11** | CI/CD | [`11-cicd/`](./11-cicd/) |
| **12** | 部署策略 | [`12-deploy-strategies/`](./12-deploy-strategies/) |

## 🔗 与项目目录的关系

- **dify**（Python）：`../dify/04-cache-and-queue/`、`05-auth-and-security/`、`08-devops/` 都有指向这里的链接
- **ruoyi-vue-pro**（Java）：`../ruoyi-vue-pro/05-cache-and-mq/`、`06-security/`、`10-devops/` 都有指向这里的链接

## 💡 使用建议

- **先看 _common**：理解通用原理（任何后端开发都必备）
- **再看项目视角**：dify/ruoyi 中保留了**项目特定**的内容（如 dify 的 Celery、ruoyi 的 Redisson）
- **对比学习**：相同的概念在不同语言/框架下的实现差异
