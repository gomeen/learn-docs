# Phase 5 — Workflow + Agent

← [索引](../LEARNING-PLAN.md) · 上一 → [Phase 4](./phase-4-rag.md) · 下一 → [Phase 6](./phase-6-broad.md)

**量级：** 3–6 周 · **入学：** 建议 Phase 4 后（更常用工作流可与 4 对调）

---

## 目标

- Workflow：一次运行 **API → 图执行**  
- Agent：一次 **tool call** 路径  

---

## 5.A Workflow

**必读**

1. [`../07-rag-and-agent/28-workflow-engine.md`](../07-rag-and-agent/28-workflow-engine.md)  
2. [`../07-rag-and-agent/29-workflow-nodes.md`](../07-rag-and-agent/29-workflow-nodes.md)  
3. [`../07-rag-and-agent/30-workflow-variables.md`](../07-rag-and-agent/30-workflow-variables.md)  
4. [`../07-rag-and-agent/32-workflow-execution.md`](../07-rag-and-agent/32-workflow-execution.md)  
5. [`../07-rag-and-agent/36-workflow-in-dify.md`](../07-rag-and-agent/36-workflow-in-dify.md)  
6. [`../07-rag-and-agent/41-chatflow-vs-workflow.md`](../07-rag-and-agent/41-chatflow-vs-workflow.md)

**源码：** `controllers/console/app/workflow.py` · `core/workflow/workflow_entry.py` · `core/workflow/nodes/` · `core/app/workflow/` · 相关 service  

---

## 5.B Agent

**必读**

1. [`../07-rag-and-agent/21-agent-concepts.md`](../07-rag-and-agent/21-agent-concepts.md)  
2. [`../07-rag-and-agent/22-react-deep-dive.md`](../07-rag-and-agent/22-react-deep-dive.md)  
3. [`../07-rag-and-agent/26-agent-in-dify.md`](../07-rag-and-agent/26-agent-in-dify.md)  
4. [`../06-llm-and-ai/17-function-calling.md`](../06-llm-and-ai/17-function-calling.md) + [`22-tools-in-dify.md`](../06-llm-and-ai/22-tools-in-dify.md)

**源码：** `core/agent/` · `core/tools/` · `controllers/console/app/agent.py` · `services/agent_service.py`

**延后：** multi-agent 全章、MCP 全套、自定义节点专家级  

---

## 毕业验收

- [ ] Workflow：API → entry → 节点，有文件列表  
- [ ] Agent：一次 tool 触发与结果回注  
- [ ] Chatflow vs Workflow 各 2 点差异  

→ [Phase 6 广覆盖](./phase-6-broad.md)
