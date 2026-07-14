# 3.2 模板方法模式（Template Method）

> 模板方法定义算法的骨架，把一些步骤延迟到子类。Spring 的 JdbcTemplate、Python 的 contextmanager 都是典型应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解模板方法模式的核心（算法骨架 + 步骤延迟）
- 识别 dify/ruoyi 中的模板方法
- 区分模板方法与策略模式
- 知道好莱坞原则（Don't call us, we'll call you）

## 📚 前置知识

- 继承/多态
- 13-strategy.md

## 1. 核心概念

### 1.1 模板方法的核心思想

父类定义**算法骨架**，子类实现**具体步骤**——通过继承实现代码复用。

### 1.2 好莱坞原则

"Don' t call us, we'll call you"——父类调用子类，而非相反。

### 1.3 模板方法 vs 策略

| 维度 | 模板方法 | 策略 |
|------|---------|------|
| 实现方式 | 继承 | 组合 |
| 关系 | 子类受父类约束 | 策略之间独立 |
| 灵活性 | 较低 | 较高 |

## 2. 代码示例

### 2.1 经典模板方法

```python
from abc import ABC, abstractmethod

class DataProcessor(ABC):
    """数据处理模板——定义算法骨架"""

    def process(self, data: str) -> dict:
        """模板方法：算法骨架（final）"""
        parsed = self.parse(data)       # 步骤 1
        validated = self.validate(parsed)  # 步骤 2
        transformed = self.transform(validated)  # 步骤 3
        result = self.save(transformed)  # 步骤 4
        return result

    @abstractmethod
    def parse(self, data: str) -> dict:
        """子类必须实现"""
        ...

    @abstractmethod
    def validate(self, data: dict) -> dict:
        """子类必须实现"""
        ...


class JSONProcessor(DataProcessor):
    def parse(self, data: str) -> dict:
        import json
        return json.loads(data)

    def validate(self, data: dict) -> dict:
        if "name" not in data:
            raise ValueError("Missing name")
        return data


# 使用
processor = JSONProcessor()
result = processor.process('{"name": "Alice"}')
```

### 2.2 Python contextmanager

```python
from contextlib import contextmanager

@contextmanager
def managed_file(path: str):
    """模板：打开 → yield → 关闭"""
    f = open(path)  # 步骤 1
    try:
        yield f       # 调用方使用
    finally:
        f.close()     # 步骤 2

# 使用
with managed_file("data.txt") as f:
    content = f.read()
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的工作流节点执行模板

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/base/node.py`
**核心代码**（行 1-50）：

```python
from abc import ABC, abstractmethod

class BaseNode(ABC):
    """节点基类——定义执行算法骨架"""

    def _run(self) -> dict:
        """模板方法：定义节点执行流程"""
        # 1. 准备输入
        inputs = self._prepare_inputs()

        # 2. 执行节点逻辑（子类实现）
        result = self._execute(inputs)

        # 3. 处理输出
        processed = self._process_output(result)

        # 4. 记录日志/状态
        self._record_state(processed)
        return processed

    @abstractmethod
    def _execute(self, inputs: dict) -> dict:
        """子类实现：节点核心逻辑"""
        ...


class LLMNode(BaseNode):
    def _execute(self, inputs: dict) -> dict:
        # LLM 节点的具体逻辑：调用模型
        return self.llm.invoke(inputs["prompt"])
```

**解读**：
- `BaseNode._run()` 定义节点执行流程（模板）
- 子类只需实现 `_execute()`（具体步骤）
- **整体设计**：用模板方法复用节点执行的公共流程

### 3.2 ruoyi 的 BaseDO 基类

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/`
**核心代码**：

```java
@Data
public abstract class BaseDO implements Serializable {
    /** 创建时间——公共字段 */
    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /** 更新时间——公共字段 */
    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}

// 所有 DO 继承 BaseDO
@Data
@TableName("system_users")
public class AdminUserDO extends BaseDO {
    private Long id;
    private String username;
    // ... 自动继承 createTime / updateTime
}
```

**解读**：
- `BaseDO` 定义公共字段（创建时间、更新时间、删除标记等）
- 子类 DO 继承即可拥有这些字段——模板方法
- **整体设计**：用基类实现公共字段复用

## 4. 关键要点总结

- 模板方法 = 算法骨架在父类，步骤在子类
- 通过继承实现代码复用
- 好莱坞原则：父类调用子类
- Python `contextmanager` 是函数式模板方法
- dify 工作流节点、ruoyi BaseDO 都是模板方法

## 5. 练习题

### 练习 1：基础
为不同格式的导出（CSV / Excel / PDF）实现模板方法。

### 练习 2：进阶
阅读 dify 的 `BaseNode`，画出 `_run()` 的完整执行流程图。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/base/node.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`
- 《设计模式》第 5 章：模板方法

---

**文档版本**：v1.0
**最后更新**：2026-07-13