# 7.5.6 工作流 DSL 规范（YAML 格式）

> 理解工作流的 DSL（Domain Specific Language）：用 YAML/JSON 描述工作流。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释工作流 DSL 的作用
- 读懂 dify 工作流导出的 YAML
- 写一个简单的 DSL 文件
- 理解 DSL 在 dify 中的序列化/反序列化

## 📚 前置知识

- 07-rag-and-agent/24-workflow-engine.md 至 28-workflow-execution.md
- YAML / JSON 基础

## 1. 核心概念

### 1.1 什么是 DSL？

DSL（Domain Specific Language，领域特定语言）是用特定格式描述某个领域事物的方式。dify 的工作流 DSL 是 JSON/YAML 格式：

```yaml
version: "0.1.0"
nodes:
  - id: start
    type: start
    data:
      variables:
        - name: query
          type: text
  - id: llm_1
    type: llm
    data:
      prompt: "{{start.query}}"
      model: gpt-4
edges:
  - source: start
    target: llm_1
```

### 1.2 DSL 的核心要素

| 字段 | 含义 |
|------|------|
| `version` | DSL 版本（向后兼容） |
| `nodes` | 节点列表 |
| `edges` | 边列表（节点连接关系） |
| `graph` | 图的整体配置 |

### 1.3 dify DSL 样例

```yaml
version: "0.3.0"
kind: app
app:
  mode: workflow
  name: "我的工作流"
workflow:
  graph:
    nodes:
      - id: "start"
        type: "start"
        data:
          variables:
            - label: "用户问题"
              variable: "user_query"
              type: "text-input"
              required: true
      - id: "llm_1"
        type: "llm"
        data:
          model:
            provider: openai
            name: gpt-4
          prompt_template:
            - role: system
              text: "你是一个助手"
            - role: user
              text: "{{start.user_query}}"
      - id: "end"
        type: "end"
        data:
          outputs:
            - variable: "result"
              value_selector: ["llm_1", "text"]
    edges:
      - source: "start"
        target: "llm_1"
      - source: "llm_1"
        target: "end"
```

## 2. 代码示例

### 2.1 解析 DSL

```python
import yaml


def parse_dsl(dsl_text: str) -> dict:
    """解析 YAML DSL"""
    return yaml.safe_load(dsl_text)


# 测试
dsl = """
version: "0.1.0"
nodes:
  - id: start
    type: start
  - id: llm_1
    type: llm
edges:
  - source: start
    target: llm_1
"""
config = parse_dsl(dsl)
print(config["nodes"])  # [{'id': 'start', 'type': 'start'}, ...]
```

### 2.2 校验 DSL

```python
def validate_dsl(config: dict) -> list[str]:
    """简单校验 DSL"""
    errors = []
    if "version" not in config:
        errors.append("Missing version")
    if "nodes" not in config or not config["nodes"]:
        errors.append("Missing or empty nodes")

    # 检查节点 ID 唯一
    ids = [n["id"] for n in config.get("nodes", [])]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate node IDs")

    # 检查 edge 引用的节点必须存在
    node_id_set = set(ids)
    for edge in config.get("edges", []):
        if edge["source"] not in node_id_set:
            errors.append(f"Edge source not found: {edge['source']}")
        if edge["target"] not in node_id_set:
            errors.append(f"Edge target not found: {edge['target']}")

    return errors
```

### 2.3 DSL 转 Graph 对象

```python
def dsl_to_graph(config: dict):
    """把 DSL 转成图对象"""
    from dataclasses import dataclass

    @dataclass
    class Node:
        id: str
        type: str
        data: dict

    @dataclass
    class Edge:
        source: str
        target: str

    @dataclass
    class Graph:
        nodes: list[Node]
        edges: list[Edge]
        start_id: str

    nodes = [Node(**n) for n in config["nodes"]]
    edges = [Edge(**e) for e in config.get("edges", [])]

    # 找 start 节点
    start = next((n for n in nodes if n.type == "start"), None)
    if not start:
        raise ValueError("No start node")

    return Graph(nodes=nodes, edges=edges, start_id=start.id)
```

### 2.4 导出 DSL

```python
def graph_to_dsl(graph) -> str:
    """把 Graph 对象导出为 YAML DSL"""
    config = {
        "version": "0.1.0",
        "nodes": [
            {"id": n.id, "type": n.type, "data": n.data}
            for n in graph.nodes
        ],
        "edges": [
            {"source": e.source, "target": e.target}
            for e in graph.edges
        ],
    }
    return yaml.dump(config, allow_unicode=True, sort_keys=False)
```

### 2.5 常见错误：变量引用格式错误

```yaml
# ❌ 错误：变量引用格式错误
prompt: "{{ start.query }}"  # 多余空格

# ✅ 正确：dify 格式
prompt: "{{start.query}}"
```

## 3. dify 仓库源码解读

### 3.1 DSL 模型定义

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/`（节选）
**核心代码**（示意）：

```python
from pydantic import BaseModel, Field


class NodeConfigDict(BaseModel):
    """节点配置字典"""
    id: str
    type: str
    data: dict


class EdgeConfigDict(BaseModel):
    """边配置字典"""
    source: str
    target: str
    sourceHandle: str | None = None
    targetHandle: str | None = None


class GraphConfigDict(BaseModel):
    """图配置字典"""
    nodes: list[NodeConfigDict]
    edges: list[EdgeConfigDict]
```

**解读**：
- dify 用 Pydantic 定义 DSL 的数据结构
- 每个字典都是 typed dict，自带校验
- 反序列化时如果格式不对，直接报错

### 3.2 Graph 初始化

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/`（节选）
**核心代码**（示意）：

```python
class Graph:
    """从 DSL 构建图"""

    @classmethod
    def init(
        cls,
        graph_config: Mapping[str, Any],
        node_factory: NodeFactory,
        root_node_id: str,
    ) -> "Graph":
        # 1. 解析节点
        nodes = {}
        for node_config in graph_config["nodes"]:
            node = node_factory.create_node(node_config)
            nodes[node.id] = node

        # 2. 解析边
        edges = []
        for edge_config in graph_config["edges"]:
            edges.append(Edge(
                source=edge_config["source"],
                target=edge_config["target"],
            ))

        return cls(nodes=nodes, edges=edges, root_node_id=root_node_id)
```

**解读**：
- `Graph.init()` 把 DSL 转成运行时图对象
- 通过 `node_factory` 把每个节点配置实例化成具体 Node 类
- 这就是 DSL → Runtime 的反序列化过程

### 3.3 WorkflowGraphTopology

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/graph_topology.py`（行 1-50）
**核心代码**：

```python
class WorkflowGraphTopology:
    def __init__(self, *, node_ids: set[str], incoming: Mapping[str, Sequence[str]]) -> None:
        self._node_ids = node_ids
        self._incoming = incoming

    @classmethod
    def from_graph(cls, graph: Mapping[str, Any]) -> WorkflowGraphTopology:
        node_ids = cls._node_ids_from_graph(graph)
        incoming: dict[str, list[str]] = defaultdict(list)
        edges = graph.get("edges")
        if isinstance(edges, list):
            for edge in edges:
                if not isinstance(edge, Mapping):
                    continue
                source = edge.get("source")
                target = edge.get("target")
                if isinstance(source, str) and isinstance(target, str):
                    incoming[target].append(source)
        return cls(node_ids=node_ids, incoming=incoming)
```

**解读**：
- `WorkflowGraphTopology.from_graph` 直接接受 DSL 字典
- 把 DSL 转成拓扑结构（反向邻接表）
- 这是 DSL 反序列化的另一种用法：用于校验图结构

## 4. 关键要点总结

- dify DSL 是 YAML/JSON 格式
- 核心字段：`version` / `nodes` / `edges`
- 变量引用格式：`{{node_id.variable_name}}`
- 通过 Pydantic 做反序列化和校验
- DSL 是 dify 工作流"导入/导出"功能的基础

## 5. 练习题

### 练习 1：基础（必做）

写一个 YAML 格式的 dify DSL：包含 Start → LLM → End 三个节点，LLM 用 start 的 query 作为输入。

### 练习 2：进阶

实现一个 DSL 校验器，检查：
- 每个节点有 id 和 type
- 每个 edge 引用的节点都存在
- 图中没有循环（DAG 校验）

### 练习 3：挑战（选做）

写一个 DSL → Graph 转换器，支持条件分支（If-Else）和循环（Iteration）节点。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/graph_topology.py`
- `/Users/xu/code/github/dify/api/core/workflow/workflow_entry.py`
- dify 官方文档：DSL 规范

---

**文档版本**：v1.0
**最后更新**：2026-07-13