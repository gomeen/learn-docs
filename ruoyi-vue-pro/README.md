# ruoyi-vue-pro 全栈学习路径

本目录是基于 [ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) 仓库的全栈学习索引。

## 📐 在知识库中的位置

| 层 | 目录 | 本路径角色 |
|----|------|------------|
| 学科基础 | [`../_fundamentals/`](../_fundamentals/) | 算法 / 网络 / DB 原理 / 模式… |
| 工程公共 | [`../_common/`](../_common/) | Redis / 安全 / 部署…（各章「公共部分」表） |
| **项目实战** | **本目录** | Java + Spring + ruoyi 源码 |

默认顺序：`_fundamentals` → `_common` → 本目录。归属规则见 [`../_common/SIGHTING.md`](../_common/SIGHTING.md)。

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

## 🚀 学习节奏：快扫基础 → 小组实战验证

本路径**不是**「把每篇长文读完」：

1. **按阶段 README 顺序学**：读完一组文档后立刻做紧随的 `*-*.md`，再进入下一组。
2. **不要攒练习**：小验证在清单中间，不是全部文档读完再做。
3. **优先改仓库**：Spring / 业务 / 工作流 / 前端类验证优先在 `/Users/xu/code/github/ruoyi-vue-pro` 做小改动；Java 语言/JVM 可用本地小项目。

各阶段 README 的模块列表后挂有对应 checkpoint 链接。文件命名：知识点 `NN-topic.md`，练习 `NN-*-topic.md`（同一目录内按学习顺序连续编号）

### 单篇知识点结构（规范）

```markdown
# 标题

> 一句话说明

## 🎯 学习目标
## 📚 前置知识
## 1. 核心概念
## 2. 代码示例
## 3. 关键要点总结

---
**文档版本** / **最后更新**
```

不再要求每篇附带「仓库源码长解读」「练习题」「参考资料」三节；源码结合放在概念/示例中点到路径即可，练习统一收敛到 checkpoint。

### 小验证（checkpoint）结构

```markdown
# 小验证：{小组名}

> 覆盖：本组文档链接列表
> 预计：30～90 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景
## 需求
## 提示
## 验收标准
- [ ] ...
## 延伸（选做）
```

需求必须**具体可验收**（接口、日志、SQL、页面行为），禁止空泛总结题。

## 🎯 使用方式
### 学习顺序（重要）

打开各阶段目录下的 `README.md`，**严格从上到下**：

```
文档 A → 文档 B → ✅ NN-*-… → 文档 C → … → ✅ NN-*-… → …
```

小验证挂在对应文档组**后面**，不是集中在阶段末尾。遇到「✅ 小验证」就停下来做。


### 让 AI 生成学习文档的 Prompt 模板

```
请根据 /Users/xu/code/gomeen/learn-docs/ruoyi-vue-pro/<分类>/README.md 中的目录，
为「<知识点名称>」生成学习文档，
保存到 /Users/xu/code/gomeen/learn-docs/ruoyi-vue-pro/<分类>/<序号>-<主题>.md

要求：
1. 理论讲解（概念、原理、适用场景、与同类方案对比）——控制篇幅，便于快扫
2. 代码示例（Java 为主，必要时附 SQL/Shell/Vue）
3. 结合 ruoyi-vue-pro 实际代码路径说明（/Users/xu/code/github/ruoyi-vue-pro），点到关键类即可，不必大段贴源码
4. 文末「关键要点总结」收束 3～6 条
5. 结构仅含：学习目标、前置知识、核心概念、代码示例、关键要点总结
6. 不要写「仓库源码解读 / 练习题 / 参考资料」独立整节；练习放到该阶段 NN-*-*.md
```

### 让 AI 生成小验证的 Prompt 模板

```
请为 ruoyi-vue-pro/<分类>/ 下「<模块或文档列表>」生成小验证文档（命名 NN-*-*.md，插入该组文档之后的序号）
cp-NN-short-slug.md，结构含：背景、需求、提示、验收标准（checklist）、延伸。
需求须可在本地或 /Users/xu/code/github/ruoyi-vue-pro 落地验收。
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
