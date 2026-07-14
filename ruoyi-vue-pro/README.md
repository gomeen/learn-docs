# ruoyi-vue-pro 全栈学习路径

本目录是基于 [ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) 仓库的全栈学习索引。

## 🎯 项目简介

**ruoyi-vue-pro**（芋道）是基于 Spring Boot 多模块架构的企业级快速开发平台，覆盖用户/权限/工作流/CRM/ERP/IoT/AI 等 20+ 业务模块，是中国最活跃的开源后台脚手架之一。

## 🛠️ 核心技术栈

| 类别 | 技术 |
|------|------|
| 后端 | Java 8 + Spring Boot 2.7.18 + Spring Cloud（yudao-cloud） |
| ORM | MyBatis Plus（不是 MyBatis） |
| 数据库 | MySQL（多数据库支持） |
| 缓存 | Redis + Redisson |
| 权限 | Spring Security + Token + 多租户 |
| 工作流 | Flowable |
| 消息队列 | Redis / RabbitMQ / Kafka / RocketMQ（5 选 1） |
| 工具 | Lombok + MapStruct + Hutool |
| 前端 | Vue3 + Element Plus / Vben（ant-design-vue）/ Vue2 / uni-app |

## 📚 知识分类总览

| 分类 | 主题 | 目录 |
|------|------|------|
| **01** | Java 基础与工具 | [`01-java-fundamentals/`](./01-java-fundamentals/) |
| **02** | Spring Boot 核心 | [`02-spring-boot/`](./02-spring-boot/) |
| **03** | 自研 Starter 框架 | [`03-spring-boot-starters/`](./03-spring-boot-starters/) |
| **04** | 数据库与 MyBatis Plus | [`04-database/`](./04-database/) |
| **05** | 缓存与消息队列 | [`05-cache-and-mq/`](./05-cache-and-mq/) |
| **06** | 安全与多租户 | [`06-security/`](./06-security/) |
| **07** | 业务模块 | [`07-business-modules/`](./07-business-modules/) |
| **08** | 代码生成器 | [`08-code-generation/`](./08-code-generation/) |
| **09** | Flowable 工作流 | [`09-workflow/`](./09-workflow/) |
| **10** | DevOps 与部署 | [`10-devops/`](./10-devops/) |
| **11** | 前端（Vue3） | [`11-frontend/`](./11-frontend/) |

## 📖 推荐学习顺序

```
01-java-fundamentals（基础） 
    ↓
02-spring-boot（核心） + 04-database（数据库）
    ↓
03-spring-boot-starters（自研框架） + 05-cache-and-mq（中间件）
    ↓
06-security（安全/多租户）
    ↓
07-business-modules（业务模块） + 08-code-generation（代码生成）
    ↓
09-workflow（Flowable）
    ↓
10-devops（部署） + 11-frontend（前端）
```

## 🎯 使用方式

### 让 AI 生成学习文档的 Prompt 模板

```
请根据 /Users/xu/code/gomeen/learn-docs/ruoyi-vue-pro/<分类>/README.md 中的目录，
为「<知识点名称>」生成学习文档，
保存到 /Users/xu/code/gomeen/learn-docs/ruoyi-vue-pro/<分类>/<序号>-<主题>.md

要求：
1. 理论讲解（概念、原理、适用场景、与同类方案对比）
2. 代码示例（Java 为主，必要时附 SQL/Shell/Vue）
3. 结合 ruoyi-vue-pro 实际代码（/Users/xu/code/github/ruoyi-vue-pro）
4. 列出参考代码文件和行号
5. 2-3 个练习题
```

## 🔗 参考资源

- ruoyi-vue-pro 仓库：`/Users/xu/code/github/ruoyi-vue-pro`
- 官方文档：https://doc.iocoder.cn/
- 演示地址：https://doc.iocoder.cn/quick-start/

## 📊 与 dify 学习目录的对比

如果你已经学过 [dify 学习目录](../dify/README.md)，本目录可以复用以下知识：
- **数据库**（SQL、ORM、迁移）- dify 用 SQLAlchemy，本目录用 MyBatis Plus
- **缓存队列**（Redis、消息队列）- 完全通用
- **安全**（JWT、RBAC、OWASP）- 完全通用
- **DevOps**（Docker、K8s、CI/CD）- 完全通用
- **工程实践**（测试、日志、监控）- 大部分通用

需要从零学习的 Java 特有知识：
- **Java 基础**（语法、Lombok、Stream API）
- **Spring Boot 核心**（IoC、AOP、Starter、AutoConfig）
- **MyBatis Plus**（与 SQLAlchemy 思路不同）
- **Flowable 工作流**
- **Vue3 + Element Plus**（如果之前只学 Vue2）
