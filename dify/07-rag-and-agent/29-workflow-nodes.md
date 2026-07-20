# 7.5.2 节点类型：开始 / 结束 / LLM / 工具 / 条件 / 循环

> 系统掌握 dify 工作流中的所有节点类型及其作用。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出 dify 工作流的核心节点类型
- 描述每种节点的输入输出
- 理解节点如何被实例化（NodeFactory）
- 在 dify 中识别每个节点的源码位置

## 📚 前置知识

- [Workflow Engine](./28-workflow-engine.md)

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

## 3. 关键要点总结

- dify 工作流有 15+ 种节点类型
- 所有节点实现统一接口 `_run()`
- 通过 `NodeFactory` 工厂模式创建节点
- 节点配置用 Pydantic 定义，前端可生成表单
- 节点之间通过 VariablePool 传递数据

---

**文档版本**：v1.0
**最后更新**：2026-07-13
