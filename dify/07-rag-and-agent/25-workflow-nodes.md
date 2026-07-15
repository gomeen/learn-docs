# 7.5.2 节点类型：开始 / 结束 / LLM / 工具 / 条件 / 循环

> 系统掌握 dify 工作流中的所有节点类型及其作用。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出 dify 工作流的核心节点类型
- 描述每种节点的输入输出
- 理解节点如何被实例化（NodeFactory）
- 在 dify 中识别每个节点的源码位置

## 📚 前置知识

- [Workflow Engine](./24-workflow-engine.md)

## 1. 核心概念

### 1.1 dify 的核心节点类型

| 节点 | 作用 | 典型场景 |
|------|------|----------|
| **Start** | 工作流入口 | 接收用户输入 |
| **End** | 工作流出口 | 返回最终结果 |
| **LLM** | 大模型调用 | 生成文本 |
| **Knowledge Retrieval** | 知识库检索 | RAG |
| **Agent** | Agent 节点 | 工具调用 |
| **Tool** | 单个工具调用 | 简单 API |
| **Code** | 执行 Python 代码 | 数据处理 |
| **If-Else** | 条件分支 | 流程分支 |
| **Iteration** | 循环遍历 | 批量处理 |
| **Parameter Extractor** | LLM 提取结构化参数 | 表单解析 |
| **Question Classifier** | LLM 分类 | 意图识别 |
| **HTTP Request** | 外部 API 调用 | 集成 |
| **Template Transform** | 字符串模板 | 文本格式化 |
| **Variable Aggregator** | 变量合并 | 多分支汇聚 |
| **Assigner** | 变量赋值 | 状态管理 |
| **Human Input** | 人工介入 | 审批流 |

### 1.2 节点的统一接口

所有节点实现统一接口（`BaseNode`）：

```python
class BaseNode(ABC):
    @abstractmethod
    def _run(self) -> NodeRunResult:
        """执行节点逻辑"""
        pass
```

输入：上游节点的输出（从 VariablePool 读取）
输出：写入 VariablePool，供下游节点使用

## 2. 代码示例

### 2.1 自定义一个简单节点

```python
from typing import Generator


class GreetingNode:
    """示例节点：生成问候语"""

    node_type = "greeting"

    def __init__(self, config: dict):
        self.template = config.get("template", "Hello, {name}!")

    def run(self, inputs: dict) -> dict:
        # 读输入
        name = inputs.get("name", "World")
        # 处理
        greeting = self.template.format(name=name)
        # 写输出
        return {"greeting": greeting}


# 使用
node = GreetingNode({"template": "Hi, {name}! 欢迎来到 dify。"})
result = node.run({"name": "Alice"})
print(result)  # {"greeting": "Hi, Alice! 欢迎来到 dify。"}
```

### 2.2 节点的工厂创建

```python
NODE_REGISTRY = {
    "greeting": GreetingNode,
    "llm": LLMNode,
    "tool": ToolNode,
}


def create_node(node_type: str, config: dict):
    """工厂方法：根据类型创建节点"""
    if node_type not in NODE_REGISTRY:
        raise ValueError(f"Unknown node type: {node_type}")
    return NODE_REGISTRY[node_type](config)
```

### 2.3 节点与变量池交互

```python
class LLMNode:
    """LLM 节点示例"""

    def __init__(self, config: dict, variable_pool):
        self.config = config
        self.pool = variable_pool

    def run(self):
        # 1. 从变量池读输入
        prompt_template = self.config["prompt_template"]
        variables = self.pool.get_all()  # 获取所有变量
        prompt = prompt_template.format(**variables)

        # 2. 调用 LLM
        response = llm.invoke(prompt)

        # 3. 写入变量池
        self.pool.set(self.config["output_var"], response)
```

### 2.4 常见错误：节点硬编码变量名

```python
# ❌ 错误：硬编码变量名
def run(self):
    user_name = self.pool.get("user_name")  # 写死了
    return {"result": f"Hello {user_name}"}

# ✅ 正确：用配置指定变量名
def run(self):
    input_var = self.config["input_var"]
    user_name = self.pool.get(input_var)
    return {"result": f"Hello {user_name}"}
```

## 3. dify 仓库源码解读

### 3.1 节点目录结构

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/`
**核心目录**：

```
nodes/
├── __init__.py
├── agent/                  # Agent 节点
├── agent_v2/               # Agent v2
├── datasource/             # 数据源节点（HTTP/数据库）
├── human_input/            # 人工输入节点
├── knowledge_index/        # 知识索引节点
├── knowledge_retrieval/    # 知识检索节点
├── trigger_plugin/         # 插件触发
├── trigger_schedule/       # 定时触发
└── trigger_webhook/        # Webhook 触发
```

**解读**：
- 每个子目录对应一种节点类型
- 大部分节点（LLM、If-Else、Iteration 等）在 `graphon` 库中（dify 的核心依赖）
- dify 的 `nodes/` 目录专注于 dify 特定的节点：知识库、Agent、触发器

### 3.2 NodeFactory 工厂

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/node_factory.py`（节选）
**核心代码**：

```python
class DifyNodeFactory:
    """dify 工作流的节点工厂"""

    def __init__(
        self,
        graph_init_params: GraphInitParams,
        graph_runtime_state: GraphRuntimeState,
    ) -> None:
        self.graph_init_params = graph_init_params
        self.graph_runtime_state = graph_runtime_state

    def create_node(self, node_config: Mapping[str, Any]) -> Node:
        """根据节点配置创建具体节点"""
        node_type = node_config.get("type")
        node_class = resolve_workflow_node_class(node_type)
        return node_class(...)
```

**解读**：
- `NodeFactory` 是工厂模式
- `resolve_workflow_node_class` 根据 `node_type` 找到具体节点类
- 通过 `graph_init_params` 和 `graph_runtime_state` 注入运行时依赖

### 3.3 KnowledgeRetrievalNode 节点

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/knowledge_retrieval/knowledge_retrieval_node.py`
**核心代码**（节选）：

```python
class KnowledgeRetrievalNode(BaseNode):
    """知识检索节点"""

    node_type = BuiltinNodeTypes.KNOWLEDGE_RETrieval

    def _run(self) -> NodeRunResult:
        # 1. 从变量池读 query
        query = self.graph_runtime_state.variable_pool.get_text(
            self.node_data.query_variable_selector
        )

        # 2. 调用 DatasetRetrieval
        documents = DatasetRetrieval.retrieve(
            retrieval_method=self.node_data.retrieval_mode,
            dataset_id=self.node_data.dataset_id,
            query=query,
            top_k=self.node_data.top_k,
            ...
        )

        # 3. 把结果写入变量池
        return NodeRunResult(outputs={
            "result": [doc.page_content for doc in documents],
            "documents": documents,
        })
```

**解读**：
- `_run` 是节点的核心方法
- 节点的所有数据通过 `self.node_data` 访问（Pydantic 模型）
- 输出通过 `NodeRunResult` 返回，由引擎写入变量池

### 3.4 KnowledgeRetrievalNodeData 实体

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/knowledge_retrieval/entities.py`
**核心代码**：

```python
class KnowledgeRetrievalNodeData(BaseModel):
    """知识检索节点的配置"""

    dataset_ids: list[str]
    query_variable_selector: list[str]  # 引用变量池中的 query
    top_k: int = 5
    score_threshold: float = 0.5
    retrieval_mode: str = "semantic_search"  # or full_text / hybrid
    rerank_enable: bool = False
    rerank_model: dict | None = None
    weights: dict | None = None
    metadata_filtering_conditions: list[dict] | None = None
```

**解读**：
- 节点的配置用 Pydantic 定义，自带校验
- `query_variable_selector` 是变量选择器（指向变量池中的具体变量）
- 这种"声明式"配置让前端可以直接生成表单

## 4. 关键要点总结

- dify 工作流有 15+ 种节点类型
- 所有节点实现统一接口 `_run()`
- 通过 `NodeFactory` 工厂模式创建节点
- 节点配置用 Pydantic 定义，前端可生成表单
- 节点之间通过 VariablePool 传递数据

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `UppercaseNode`：输入 `text` 变量，输出 `result` 变量 = text.upper()。

### 练习 2：进阶

实现一个 `ConditionalNode`：读取两个变量 `a` 和 `b`，根据 `a > b` 选择不同的输出分支。

### 练习 3：挑战（选做）

阅读 `node_factory.py` 完整实现，理解 dify 如何注册和查找节点类。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/`
- `/Users/xu/code/github/dify/api/core/workflow/node_factory.py`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/knowledge_retrieval/knowledge_retrieval_node.py`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/knowledge_retrieval/entities.py`

---

**文档版本**：v1.0
**最后更新**：2026-07-13