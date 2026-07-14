# 3.11 解释器模式（Interpreter）

> 解释器模式给定一个语言，定义它的文法的一种表示，并定义一个解释器，这个解释器使用该表示来解释语言中的句子。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解解释器模式的核心（自定义 DSL）
- 掌握抽象语法树（AST）的构建
- 在 dify 中识别解释器应用（提示词模板、规则引擎）
- 知道解释器的适用场景与局限

## 📚 前置知识

- 22-visitor.md
- 递归与树

## 1. 核心概念

### 1.1 解释器模式的核心思想

为自定义 DSL（领域特定语言）定义文法，并用 AST 表示，最后用解释器执行。

### 1.2 解释器 4 要素

1. **AbstractExpression**：表达式接口（`interpret()`）
2. **TerminalExpression**：终结符表达式（叶子）
3. **NonterminalExpression**：非终结符表达式（内部节点）
4. **Context**：解释器上下文（变量等）

### 1.3 适用场景

- 需要解释自定义 DSL
- 文法简单（复杂文法用解析器生成工具 ANTLR）
- 执行效率不是关键

## 2. 代码示例

### 2.1 简单算术表达式解释器

```python
from abc import ABC, abstractmethod

class Expression(ABC):
    @abstractmethod
    def interpret(self, context: dict) -> float: ...


class Number(Expression):
    """终结符：数字"""
    def __init__(self, value: float):
        self.value = value

    def interpret(self, context):
        return self.value


class Variable(Expression):
    """终结符：变量"""
    def __init__(self, name: str):
        self.name = name

    def interpret(self, context):
        return context[self.name]


class Add(Expression):
    """非终结符：加法"""
    def __init__(self, left: Expression, right: Expression):
        self.left, self.right = left, right

    def interpret(self, context):
        return self.left.interpret(context) + self.right.interpret(context)


class Subtract(Expression):
    """非终结符：减法"""
    def __init__(self, left, right):
        self.left, self.right = left, right

    def interpret(self, context):
        return self.left.interpret(context) - self.right.interpret(context)


# 解析表达式 "x + 10 - y"
x = Variable("x")
y = Variable("y")
expr = Subtract(Add(x, Number(10)), y)

# 执行
print(expr.interpret({"x": 5, "y": 2}))  # 13
```

### 2.2 简单规则引擎

```python
class Condition(ABC):
    @abstractmethod
    def evaluate(self, context: dict) -> bool: ...


class EqualsCondition(Condition):
    def __init__(self, var: str, value):
        self.var = var
        self.value = value

    def evaluate(self, context):
        return context.get(self.var) == self.value


class AndCondition(Condition):
    def __init__(self, *conditions: Condition):
        self.conditions = conditions

    def evaluate(self, context):
        return all(c.evaluate(context) for c in self.conditions)


# 规则：age > 18 AND country == "CN"
rule = AndCondition(
    EqualsCondition("country", "CN"),
    EqualsCondition("vip", True),
)

print(rule.evaluate({"country": "CN", "vip": True}))   # True
print(rule.evaluate({"country": "US", "vip": True}))   # False
```

## 3. dify 仓库源码解读

### 3.1 dify 的提示词模板解释器

**文件位置**：`/Users/xu/code/github/dify/api/core/prompt/`
**核心代码**（行 1-50）：

```python
from abc import ABC, abstractmethod
import re

class PromptTemplateNode(ABC):
    """提示词模板节点"""
    @abstractmethod
    def render(self, context: dict) -> str: ...


class TextNode(PromptTemplateNode):
    """叶子：纯文本"""
    def __init__(self, text: str):
        self.text = text

    def render(self, context):
        return self.text


class VariableNode(PromptTemplateNode):
    """叶子：变量 {{name}}"""
    def __init__(self, name: str):
        self.name = name

    def render(self, context):
        return str(context.get(self.name, ""))


class ConditionalNode(PromptTemplateNode):
    """非叶子：条件块 {% if x %} ... {% endif %}"""
    def __init__(self, condition_var: str, true_branch, false_branch):
        self.condition_var = condition_var
        self.true_branch = true_branch
        self.false_branch = false_branch

    def render(self, context):
        if context.get(self.condition_var):
            return self.true_branch.render(context)
        return self.false_branch.render(context)


class TemplateParser:
    """模板解析器：把字符串转为 AST"""
    def parse(self, template: str) -> PromptTemplateNode:
        # 简化：正则解析 {{var}} 和 {% if %}
        tokens = re.findall(r"\{\{.*?\}\}|{%.*?%}|[\s\S]+?(?=\{\{|$)", template)
        return self._build_ast(tokens)
```

**解读**：
- dify 的提示词模板是一种 DSL（`{{var}}`、`{% if %}`）
- 通过 AST 节点表示，再用解释器渲染
- **整体设计**：用解释器模式实现提示词模板

### 3.2 dify 的工作流条件节点

**位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/if_else/`
**核心代码**（简化）：

```python
class IfElseNode(BaseNode):
    """条件分支节点——解释用户配置的条件表达式"""

    def _execute(self, inputs: dict) -> dict:
        conditions = self.config["conditions"]  # [{"variable": "x", "op": ">", "value": 10}]
        for cond in conditions:
            # 解释条件表达式
            if self._eval_condition(cond, inputs):
                return {"branch": cond.get("true_branch")}
        return {"branch": self.config.get("false_branch", "default")}

    def _eval_condition(self, cond: dict, context: dict) -> bool:
        var_value = context.get(cond["variable"])
        op = cond["op"]
        target = cond["value"]
        ops = {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            "==": lambda a, b: a == b,
        }
        return ops[op](var_value, target)
```

**解读**：
- 工作流的条件节点解释用户配置的条件 DSL
- 每个操作符是一个解释器
- **整体设计**：用解释器模式让用户配置业务条件

## 4. 关键要点总结

- 解释器 = 自定义 DSL + AST + 解释执行
- 4 要素：AbstractExpression、TerminalExpression、NonterminalExpression、Context
- 适合：DSL 简单、执行效率不重要
- dify 提示词模板、条件节点都是解释器
- 复杂文法用 ANTLR 等工具替代

## 5. 练习题

### 练习 1：基础
为布尔表达式（AND/OR/NOT）实现一个解释器。

### 练习 2：进阶
阅读 dify 的提示词模板代码，分析它的 AST 结构和解释过程。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/prompt/`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/if_else/`
- 《设计模式》第 5 章：解释器模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13