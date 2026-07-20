# Phase 1 — Python 够用 + 产品/代码地图

← [索引](../LEARNING-PLAN.md) · 上一 → [Phase 0](./phase-0-docker.md) · 下一 → [Phase 2](./phase-2-main-paths.md)

**量级：** 2–4 周 · **入学：** Phase 0 毕业  
**地图速查：** [`api-map.md`](./api-map.md)

---

## 目标

| 轨 | 目标 |
|----|------|
| **A Python** | 能读懂 `api` 里常见 30 行（class / def / 异常 / import） |
| **B 地图** | 产品对象 ↔ `api/` 一级目录能对上 |

双轨并行；每周各推进一点，见 [00-guide](./00-guide.md)。

---

## 轨 A · Python 必读

| 序 | 文档 | 验证 |
|----|------|------|
| 1 | [`../01-fundamentals/01-python-variables-and-types.md`](../01-fundamentals/01-python-variables-and-types.md) | |
| 2 | [`02-python-functions.md`](../01-fundamentals/02-python-functions.md) | |
| 3 | [`03-python-classes-basics.md`](../01-fundamentals/03-python-classes-basics.md) | |
| 4 | [`04-python-modules-and-imports.md`](../01-fundamentals/04-python-modules-and-imports.md) | |
| 5 | [`05-python-control-flow.md`](../01-fundamentals/05-python-control-flow.md) | |
| 6 | [`06-python-exceptions.md`](../01-fundamentals/06-python-exceptions.md) | |
| 7 | **做** [`07-*-python-basics.md`](../01-fundamentals/07-*-python-basics.md) | 验收通过 |
| 8 | [`08-python-typing-basics.md`](../01-fundamentals/08-python-typing-basics.md) | |
| 9 | [`11-decorator.md`](../01-fundamentals/11-decorator.md) | Flask 会用到 |
| 10 | **做** [`13-*-typing-decorator-context.md`](../01-fundamentals/13-*-typing-decorator-context.md) 中装饰器相关即可 | |

**卡壳再读：** [`09-typeddict`](../01-fundamentals/09-typeddict.md)、[`12-context-manager`](../01-fundamentals/12-context-manager.md)、[`20-json-processing`](../01-fundamentals/20-json-processing.md)

**延后（本阶段禁止）：** 14–17 异步全书、23–27 元类/描述符、30–33 并发/GIL。流式对话（Phase 2.5）再开异步/生成器。

---

## 轨 B · 产品地图

1. UI 各点一遍：创建应用、对话、知识库、工作流、模型供应商（会用即可）  
2. 粗读：`dify/README.md`、`dify/api/AGENTS.md`  
3. 自己填「词 → 目录」（先猜再验证）：

| 业务词 | 常见入口 |
|--------|----------|
| Console HTTP | `controllers/console/` |
| 业务编排 | `services/` |
| 对话 / 工作流 / RAG / Agent | `core/app` · `workflow` · `rag` · `agent` |
| 表结构 | `models/` |
| 异步任务 | `tasks/` + `extensions/ext_celery.py` |
| 登录 | `extensions/ext_login.py` · `libs/login` |
| 模型供应商 | `providers/` · `core/model_manager.py` |

完整表见 [`api-map.md`](./api-map.md)。

**卡壳再读：** [`../02-backend/01-ddd-in-dify.md`](../02-backend/01-ddd-in-dify.md)（只建语感，不做完整 DDD）  
HTTP 状态码 → [`../../_common/14-api-protocols/01-http-protocol.md`](../../_common/14-api-protocols/01-http-protocol.md)

---

## 本周目标模板

- [ ] Python：上表连续 1 组 + checkpoint 片段  
- [ ] 为 `controllers` / `services` / `core` / `models` / `tasks` 各写一句职责  
- [ ] 打开任一 `controllers/console/**/*.py`，指出路由装饰器与调用的 service  

---

## 毕业验收（全勾 → Phase 2）

- [ ] Dify 是什么 ≥3 句；核心对象 ≥5 个  
- [ ] 「改登录 / 改发消息 / 改知识库」能指一级目录  
- [ ] 独立读一段含 class + 异常的源码并口述  
- [ ] `07-*-python-basics` 达标  

进度：[`progress.md`](./progress.md)
