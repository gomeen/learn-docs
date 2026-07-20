# Dify 学习计划（索引）

> **从这里选当前阶段，只打开对应分册。** 不要一次读完所有 Phase。  
> 源码：`/Users/xu/code/github/dify`（文中简称 `dify/`）  
> 勾选：`[ ]` 未完成 · `[x]` 完成

**当前进度（自己改）：** Phase `0` · 本周主题：`____________`

---

## 先读（约 5 分钟）

| 文档 | 内容 |
|------|------|
| [`plan/00-guide.md`](./plan/00-guide.md) | 目标、范围、每周节奏、跟读流程、文档分层 |

读完 guide 后，**只打开当前 Phase 分册**。

---

## 阶段分册

| Phase | 分册 | 量级 | 入学 |
|-------|------|------|------|
| **0** | [`plan/phase-0-docker.md`](./plan/phase-0-docker.md) | 1–2 周 | 有 dify 仓库 |
| **1** | [`plan/phase-1-python-map.md`](./plan/phase-1-python-map.md) | 2–4 周 | Phase 0 毕业 |
| **2** | [`plan/phase-2-main-paths.md`](./plan/phase-2-main-paths.md)（2.1/2.2/2.5 见 [`plan/phase-2/`](./plan/phase-2/) 加厚分册） | 4–8 周 | Phase 1 毕业 |
| **3** | [`plan/phase-3-contribute.md`](./plan/phase-3-contribute.md) | 与 2 重叠 | 2.1–2.2 后可轻量开始 |
| **4** | [`plan/phase-4-rag.md`](./plan/phase-4-rag.md) | 2–4 周 | Phase 2 毕业 |
| **5** | [`plan/phase-5-workflow-agent.md`](./plan/phase-5-workflow-agent.md) | 3–6 周 | 建议 Phase 4 后 |
| **6** | [`plan/phase-6-broad.md`](./plan/phase-6-broad.md) | 长期 | Phase 0–5 主项毕业 |

### 搞懂四级

| 级别 | 含义 | Phase |
|------|------|-------|
| 地图级 | 子系统 + `api/` 目录职责 | 0–1 |
| 主链路级 | 登录/对话能跟能改 | 2 |
| 贡献级 | 小 issue / 测试 / PR | 3 |
| 引擎级 | RAG + Workflow/Agent | 4–5 |
| 广覆盖 | 点菜加深 | 6 |

---

## 工具页

| 文档 | 用途 |
|------|------|
| [`plan/api-map.md`](./plan/api-map.md) | `api/` 目录速查（跟代码时打开） |
| [`plan/progress.md`](./plan/progress.md) | 阶段勾选、小改动日志、贡献日志 |
| [`../CHECKLIST-understand.md`](../CHECKLIST-understand.md) | 通用后端会/不会（阶段末回填，不当开读顺序） |

---

## 规则（三条）

1. **同时只做一个 Phase**（Phase 3 可与 2 轻量并行）  
2. **`01/`–`11/` 是素材库**，只读分册里写的「必读」；未列出的默认不读  
3. **未毕业不进下一阶段** —— 验收在各自分册末尾  

---

## 维护

- 主路径以本索引 + `plan/` 分册为准  
- 上游目录变更：改对应分册里的源码路径  
- 版本：v1.1 · 拆分于 2026-07-20  
