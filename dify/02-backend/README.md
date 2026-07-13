# 02 - 后端架构与框架

> Dify 后端使用 Flask + DDD 分层架构，本分类是 dify 业务代码的核心设计模式。

## 前置依赖

- `01-fundamentals` 全部
- `03-database` 中的 SQLAlchemy 基础（与本分类并行学习）

## 模块 2.1 领域驱动设计（DDD）

- [ ] [2.1.1 DDD 核心概念：实体、值对象、聚合根](./01-ddd-concepts.md)
- [ ] [2.1.2 分层架构：Controller → Service → Repository → Domain](./02-layered-architecture.md)
- [ ] [2.1.3 仓储模式（Repository Pattern）](./03-repository-pattern.md)
- [ ] [2.1.4 领域服务与应用服务的边界](./04-domain-service.md)
- [ ] [2.1.5 依赖注入：构造函数注入与控制反转](./05-dependency-injection.md)
- [ ] [2.1.6 领域事件与事件驱动](./06-domain-event.md)
- [ ] [2.1.7 DDD 在 dify 中的实践：Workflow 执行链路分析](./07-ddd-in-dify.md)

## 模块 2.2 Flask 框架

- [ ] [2.2.1 Flask 基础：路由、视图、请求响应对象](./08-flask-basics.md)
- [ ] [2.2.2 Flask 上下文机制：`g` / `request` / `session` / `current_app`](./09-flask-context.md)
- [ ] [2.2.3 蓝图（Blueprint）组织大型应用](./10-flask-blueprint.md)
- [ ] [2.2.4 Flask-RESTX：Namespace、Resource、Swagger](./11-flask-restx.md)
- [ ] [2.2.5 请求钩子：`before_request` / `after_request` / `teardown`](./12-flask-hooks.md)
- [ ] [2.2.6 自定义错误处理与异常体系](./13-flask-error-handling.md)
- [ ] [2.2.7 dify 的 Controller 层设计模式](./14-flask-in-dify.md)

## 模块 2.3 Pydantic v2 数据建模

- [ ] [2.3.1 BaseModel 与字段类型](./15-pydantic-basics.md)
- [ ] [2.3.2 字段校验器：`field_validator` / `model_validator`](./16-pydantic-validators.md)
- [ ] [2.3.3 DTO 与 API Schema 设计模式](./17-pydantic-dto.md)
- [ ] [2.3.4 Pydantic 配置：`ConfigDict` / `extra="forbid"`](./18-pydantic-config.md)
- [ ] [2.3.5 dify 的 Pydantic 使用规范](./19-pydantic-in-dify.md)

## 模块 2.4 后端架构模式

- [ ] [2.4.1 多租户架构：`tenant_id` 贯穿全链路](./20-multi-tenancy.md)
- [ ] [2.4.2 中间件架构与拦截器模式](./21-middleware-pattern.md)
- [ ] [2.4.3 适配器模式：对接多种外部服务](./22-adapter-pattern.md)
- [ ] [2.4.4 策略模式与工厂模式](./23-strategy-factory.md)

## 🎯 dify 仓库对应位置

- Controllers：`/Users/xu/code/github/dify/api/controllers/`
- Services：`/Users/xu/code/github/dify/api/services/`
- Core（领域层）：`/Users/xu/code/github/dify/api/core/`
- Pydantic 模型：`/Users/xu/code/github/dify/api/core/workflow/entities/`
- 中间件：`/Users/xu/code/github/dify/api/extensions/middleware/`
- Controller 规范：`/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`
