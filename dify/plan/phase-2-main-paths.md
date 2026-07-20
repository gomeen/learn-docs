# Phase 2 — 后端主链路竖切（核心）

← [索引](../LEARNING-PLAN.md) · 上一 → [Phase 1](./phase-1-python-map.md) · 可并行 → [Phase 3](./phase-3-contribute.md) · 下一 → [Phase 4](./phase-4-rag.md)

**量级：** 4–8 周 · **入学：** Phase 1 毕业  
**跟读通式：** [00-guide](./00-guide.md) · **api 地图：** [`api-map.md`](./api-map.md)

---

## 目标

按序完成 **2.1 → 2.8**；一条未毕业不开启下一条。  
Python **缺啥补啥**，不刷 `01` 全书。

**加厚分册（优先打开）：** 2.1 / 2.2 / 2.5 含上手操作、时序提纲、卡点表。

| 切片 | 文档 | 主题 |
|------|------|------|
| **2.1** | [`phase-2/2.1-flask.md`](./phase-2/2.1-flask.md) | Flask 入口 ⭐ 加厚 |
| **2.2** | [`phase-2/2.2-login.md`](./phase-2/2.2-login.md) | 登录 ⭐ 加厚 |
| 2.3 | 下文 | 多租户 Minimal |
| 2.4 | 下文 | App + 1 个 provider |
| **2.5** | [`phase-2/2.5-chat.md`](./phase-2/2.5-chat.md) | 对话 / 流式 ⭐ 加厚 |
| 2.6 | 下文 | ORM |
| 2.7 | 下文 | Redis |
| 2.8 | 下文 | Celery |
| 总毕业 | [文末](#phase-2-总毕业) | 主链路级 |

---

## 2.1 · 2.2 · 2.5

请直接打开加厚分册（本页不重复正文）：

- [`phase-2/2.1-flask.md`](./phase-2/2.1-flask.md)  
- [`phase-2/2.2-login.md`](./phase-2/2.2-login.md) — 完成后可开始轻量 [Phase 3](./phase-3-contribute.md)  
- [`phase-2/2.5-chat.md`](./phase-2/2.5-chat.md) — 建议先完成 2.3、2.4  

---

## 2.3 工作空间 / 多租户 Minimal

**必读**

1. [`../02-backend/18-multi-tenancy.md`](../02-backend/18-multi-tenancy.md)  
2. [`../03-database/11-multi-tenant-query.md`](../03-database/11-multi-tenant-query.md)

**源码：** `controllers/console/workspace/` · `current_account_with_tenant` · 搜 `tenant_id`

**上手（简）：** 登录后切换/查看工作空间 → Network 找带 workspace/tenant 的请求 → 在 service 查询里找 `tenant_id` 条件。

**毕业**

- [ ] 多工作空间数据如何隔离（一句话 + 代码证据）  
- [ ] 知道租户上下文即可，不做完整 RBAC  

**延后：** enterprise RBAC、billing  

---

## 2.4 应用 + 唯一一条 Provider

**必读**

1. [`../06-llm-and-ai/01-llm-overview.md`](../06-llm-and-ai/01-llm-overview.md)  
2. [`../06-llm-and-ai/33-model-runtime.md`](../06-llm-and-ai/33-model-runtime.md)  
3. [`../06-llm-and-ai/34-model-provider.md`](../06-llm-and-ai/34-model-provider.md)  
4. **只选一个：** [`31-openai-api`](../06-llm-and-ai/31-openai-api.md) 或 [`30-anthropic-api`](../06-llm-and-ai/30-anthropic-api.md)

**延后：** 全部 providers、MCP 全套、billing 优化  

**源码：** `controllers/console/app/app.py` · `model_config.py` · `services/app_service.py` · `app_model_config_service.py` · `core/model_manager.py` · `provider_manager.py` · `providers/`（只钻启用的一个）

**上手（简）：** UI 配一个供应商 → 创建/打开 App 选模型 → Network 看保存配置的请求 → 从 controller 跟到 model 配置存储。

**毕业**

- [ ] UI 配好模型并在应用中选中  
- [ ] 配置存哪 + 运行时取模型入口  

→ 然后做 [2.5 对话](./phase-2/2.5-chat.md)

---

## 2.6 SQLAlchemy 与一次查询

**必读**

1. [`../../_common/21-sql/01-sql-basics.md`](../../_common/21-sql/01-sql-basics.md)  
2. [`../03-database/02-sqlalchemy-mapping.md`](../03-database/02-sqlalchemy-mapping.md)  
3. [`../03-database/03-sqlalchemy-query.md`](../03-database/03-sqlalchemy-query.md)  
4. [`../03-database/07-sqlalchemy-session.md`](../03-database/07-sqlalchemy-session.md)  
5. 验证：[`../03-database/05-*-sqlalchemy-basics.md`](../03-database/05-*-sqlalchemy-basics.md)

**卡壳再读：** relations / loading / [`04-sql-transaction`](../../_common/21-sql/04-sql-transaction.md)

**源码：** `extensions/ext_database.py` · `models/base.py` · `account.py` 或 `model.py` · 已跟过的 service 里的 session

**上手（简）：** 从 2.2 的 `AccountService` 或 2.5 写 message 的路径里，标出一次 `db.session` / query；对照 `models/` 类。

**毕业**

- [ ] 一条相关 SELECT 语义  
- [ ] ORM 类 ↔ 表  
- [ ] session 提交/失败理解  

**延后：** Alembic 全套、分库分表  

---

## 2.7 Redis 现身

**必读**

1. [`../../_common/01-redis/01-data-structures.md`](../../_common/01-redis/01-data-structures.md)（速览）  
2. [`../04-cache-and-queue/01-redis-in-dify.md`](../04-cache-and-queue/01-redis-in-dify.md)  
3. [`../04-cache-and-queue/03-redis-py.md`](../04-cache-and-queue/03-redis-py.md)

**卡壳：** [`../../_common/03-cache-patterns/01-strategies.md`](../../_common/03-cache-patterns/01-strategies.md)

**源码：** 搜 `redis`（extensions / libs / services）· compose 中 redis 与 api/worker

**上手（简）：** `rg -n "redis" extensions libs --glob '*.py' | head`；结合 2.2 登录限流是否走 redis（若有）。

**毕业**

- [ ] 至少一类真实用途（缓存/broker/限流/会话，以代码为准）  
- [ ] worker 与 redis 的关系  

---

## 2.8 Celery 一条任务

**必读**

1. [`../04-cache-and-queue/05-celery-architecture.md`](../04-cache-and-queue/05-celery-architecture.md)  
2. [`../04-cache-and-queue/06-celery-tasks.md`](../04-cache-and-queue/06-celery-tasks.md)  
3. [`../04-cache-and-queue/14-celery-in-dify.md`](../04-cache-and-queue/14-celery-in-dify.md)  
4. 验证：[`../04-cache-and-queue/10-*-celery-and-events.md`](../04-cache-and-queue/10-*-celery-and-events.md)（能做的部分）

**源码：** `ext_celery.py` · `celery_entrypoint.py` · `tasks/document_indexing_task.py` · compose `worker` / `worker_beat`

**上手（简）：** 上传知识库文档触发索引（或你环境里会进队列的操作）→ `docker compose logs -f worker` 看任务名。

**毕业**

- [ ] 同步 vs 丢 worker  
- [ ] 触发一次异步操作，worker 日志见任务名  

**延后：** 幂等/重试/beat 全参数  

---

## Phase 2 总毕业

- [ ] 闭卷：登录全链路（见 [2.2](./phase-2/2.2-login.md)）  
- [ ] 闭卷：发聊天消息到模型调用前（见 [2.5](./phase-2/2.5-chat.md)）  
- [ ] 两份路径清单能复述  
- [ ] **≥2 次**有意小改动并自测（记入 [`progress.md`](./progress.md)）  
- [ ] [`CHECKLIST`](../../CHECKLIST-understand.md) 中 P0 开始出现「会」  

### 本阶段延后总表

- `06` prompt/MCP 全书 · `07` 引擎细读（→ 4–5）  
- `09`/`10`/`11` 扫荡（→ 3/6） · `02` 模式合集  

→ 主链路毕业后进入 [Phase 4 RAG](./phase-4-rag.md)
