# 02 - 后端架构与框架

> Dify 后端使用 Flask + DDD 分层架构，本分类是 dify 业务代码的核心设计模式。
> **主路径**：全局顺序与「必读/延后」以 [`../LEARNING-PLAN.md`](../LEARNING-PLAN.md) 为准。
> 下方清单是**本分类素材目录**；未列入主计划的篇默认不读。需要做小验证时，优先做主计划点名的 `NN-*-*.md`。

## 🌐 公共部分

| 主题 | 公共文档 | 本项目特定 |
|------|----------|------------|
| DDD / 分层 / 仓储 / DI / 领域事件 | [`_common/22-architecture`](../../_common/22-architecture/) | `01-ddd-in-dify.md` |

## 前置依赖

- 以 [`../LEARNING-PLAN.md`](../LEARNING-PLAN.md) Phase 2 为准（**不要**先刷完 `01-fundamentals` 全部）
- Flask 竖切（2.1）不依赖 SQLAlchemy 全书；查库竖切（2.6）再开 `03-database` 子集

## 模块 2.1 领域驱动设计（DDD）

- [ ] [2.1.1 DDD 核心概念：实体、值对象、聚合根](../../_common/22-architecture/01-ddd-concepts.md)
- [ ] [2.1.2 分层架构：Controller → Service → Repository → Domain](../../_common/22-architecture/02-layered-architecture.md)
- [ ] [2.1.3 仓储模式（Repository Pattern）](../../_common/22-architecture/03-repository-pattern.md)
- [ ] [2.1.4 领域服务与应用服务的边界](../../_common/22-architecture/04-domain-service.md)
- [ ] [2.1.5 依赖注入：构造函数注入与控制反转](../../_common/22-architecture/05-dependency-injection.md)
- [ ] [2.1.6 领域事件与事件驱动](../../_common/22-architecture/06-domain-event.md)
- [ ] [2.1.7 DDD 在 dify 中的实践：Workflow 执行链路分析](./01-ddd-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [02-*-ddd-in-dify: DDD 在 dify 中的分层](./02-*-ddd-in-dify.md)
  - 覆盖：01-ddd-in-dify.md


## 模块 2.2 Flask 框架

- [ ] [2.2.1 Flask 基础：路由、视图、请求响应对象](./03-flask-basics.md)
- [ ] [2.2.2 Flask 上下文机制：`g` / `request` / `session` / `current_app`](./04-flask-context.md)
- [ ] [2.2.3 蓝图（Blueprint）组织大型应用](./05-flask-blueprint.md)
- [ ] [2.2.4 Flask-RESTX：Namespace、Resource、Swagger](./06-flask-restx.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [07-*-flask-core: Flask 基础与 RESTX](./07-*-flask-core.md)
  - 覆盖：03-flask-basics.md, 04-flask-context.md, 05-flask-blueprint.md, 06-flask-restx.md


- [ ] [2.2.5 请求钩子：`before_request` / `after_request` / `teardown`](./08-flask-hooks.md)
- [ ] [2.2.6 自定义错误处理与异常体系](./09-flask-error-handling.md)
- [ ] [2.2.7 dify 的 Controller 层设计模式](./10-flask-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [11-*-flask-hooks-errors: Flask 钩子、错误处理与 dify Controller](./11-*-flask-hooks-errors.md)
  - 覆盖：08-flask-hooks.md, 09-flask-error-handling.md, 10-flask-in-dify.md


## 模块 2.3 Pydantic v2 数据建模

- [ ] [2.3.1 BaseModel 与字段类型](./12-pydantic-basics.md)
- [ ] [2.3.2 字段校验器：`field_validator` / `model_validator`](./13-pydantic-validators.md)
- [ ] [2.3.3 DTO 与 API Schema 设计模式](./14-pydantic-dto.md)
- [ ] [2.3.4 Pydantic 配置：`ConfigDict` / `extra="forbid"`](./15-pydantic-config.md)
- [ ] [2.3.5 dify 的 Pydantic 使用规范](./16-pydantic-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [17-*-pydantic: Pydantic v2 与 DTO](./17-*-pydantic.md)
  - 覆盖：12-pydantic-basics.md, 13-pydantic-validators.md, 14-pydantic-dto.md, 15-pydantic-config.md, 16-pydantic-in-dify.md


## 模块 2.4 后端架构模式

- [ ] [2.4.1 多租户架构：`tenant_id` 贯穿全链路](./18-multi-tenancy.md)
- [ ] [2.4.2 中间件架构与拦截器模式](./19-middleware-pattern.md)
- [ ] [2.4.3 适配器模式：对接多种外部服务](./20-adapter-pattern.md)
- [ ] [2.4.4 策略模式与工厂模式](./21-strategy-factory.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [22-*-architecture-patterns: 多租户 · 中间件 · 适配器 · 策略工厂](./22-*-architecture-patterns.md)
  - 覆盖：18-multi-tenancy.md, 19-middleware-pattern.md, 20-adapter-pattern.md, 21-strategy-factory.md


## 🎯 dify 仓库对应位置

- Controllers：`/Users/xu/code/github/dify/api/controllers/`
- Services：`/Users/xu/code/github/dify/api/services/`
- Core（领域层）：`/Users/xu/code/github/dify/api/core/`
- Pydantic 模型：`/Users/xu/code/github/dify/api/core/workflow/entities/`
- 中间件：`/Users/xu/code/github/dify/api/extensions/middleware/`
- Controller 规范：`/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`
