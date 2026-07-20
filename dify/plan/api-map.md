# `api/` 目录速查

← [索引](../LEARNING-PLAN.md) · 常与 [Phase 1](./phase-1-python-map.md) / [Phase 2](./phase-2-main-paths.md) 同开

源码根：`/Users/xu/code/github/dify/api`

---

## 一级目录

| 目录 | 一句话 |
|------|--------|
| `controllers/` | HTTP 入口 |
| `services/` | 业务用例编排 |
| `core/` | 引擎（app / rag / workflow / agent / tools…） |
| `models/` | ORM 与表 |
| `tasks/` | Celery 任务 |
| `extensions/` | Flask 扩展装配（db / login / celery / blueprint…） |
| `libs/` | 跨模块工具与登录辅助 |
| `providers/` | 模型等供应商适配 |
| `configs/` | 配置 |
| `migrations/` | DB 迁移 |
| `tests/` | 测试 |

---

## Controller 分流

| 路径 | 用途 |
|------|------|
| `controllers/console` | 控制台（主跟读） |
| `controllers/service_api` | 对外 API Key |
| `controllers/web` | 站点 / 嵌入相关 |
| `controllers/inner_api` 等 | 内部接口（用到再看） |

---

## 业务词 → 入口（跟读用）

| 业务 | 先看 |
|------|------|
| 登录 | `controllers/console/auth/login.py` · `extensions/ext_login.py` · `services/account_service.py` |
| 应用 | `controllers/console/app/` · `services/app_service.py` |
| 对话生成 | `completion.py` / `message.py` / `generator.py` · `app_generate_service.py` · `core/app/` |
| 知识库 | `controllers/console/datasets/` · `core/rag/` · `tasks/document_indexing_*.py` |
| 工作流 | `controllers/console/app/workflow.py` · `core/workflow/` |
| Agent | `controllers/console/app/agent.py` · `core/agent/` · `core/tools/` |
| 异步 | `tasks/` · `extensions/ext_celery.py` · `celery_entrypoint.py` |

上游重命名时以本机树为准，改本页即可。
