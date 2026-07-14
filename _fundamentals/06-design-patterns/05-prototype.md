# 1.5 原型模式（Prototype）

> 原型模式通过"克隆"已有对象来创建新对象，避免重复初始化。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解原型模式的核心思想（克隆代替 new）
- 掌握浅拷贝 vs 深拷贝的区别
- 在 dify/ruoyi 中识别原型应用
- 知道原型模式的局限

## 📚 前置知识

- Python 类与对象
- 引用 vs 拷贝

## 1. 核心概念

### 1.1 原型模式的核心

不是通过 `new` 创建新对象，而是**克隆**已有对象。

### 1.2 浅拷贝 vs 深拷贝

| 维度 | 浅拷贝 | 深拷贝 |
|------|--------|--------|
| 拷贝层级 | 只拷贝顶层 | 递归拷贝所有层 |
| 引用对象 | 共享原对象引用 | 复制一份 |
| Python | `copy.copy()` | `copy.deepcopy()` |

### 1.3 适用场景

- 对象初始化成本高（如数据库连接、复杂配置）
- 需要保留对象状态做快照
- 创建对象需要的数据不方便直接获得

## 2. 代码示例

### 2.1 Python 深浅拷贝

```python
import copy

class Config:
    def __init__(self, db: dict, features: list[str]):
        self.db = db
        self.features = features

original = Config({"host": "localhost", "port": 5432}, ["auth", "rag"])

# 浅拷贝
shallow = copy.copy(original)
shallow.db["host"] = "remote"  # 影响原对象！

# 深拷贝
deep = copy.deepcopy(original)
deep.db["host"] = "remote"     # 不影响原对象

print(original.db["host"])  # remote（浅拷贝修改了原对象）
```

### 2.2 Python 原型模式实现

```python
import copy
from abc import ABC, abstractmethod

class Prototype(ABC):
    @abstractmethod
    def clone(self):
        pass

class MessageTemplate(Prototype):
    def __init__(self, role: str, content: str, metadata: dict | None = None):
        self.role = role
        self.content = content
        self.metadata = metadata or {}

    def clone(self) -> "MessageTemplate":
        """深拷贝创建新对象——原型模式"""
        return copy.deepcopy(self)


# 使用：克隆模板
system_template = MessageTemplate("system", "You are a helpful assistant.")
user_msg = system_template.clone()
user_msg.role = "user"
user_msg.content = "Hello!"

print(user_msg.role)  # user（不影响 system_template）
```

### 2.3 Java Cloneable

```java
public class Message implements Cloneable {
    private String role;
    private String content;

    @Override
    public Message clone() {
        try {
            return (Message) super.clone();
        } catch (CloneNotSupportedException e) {
            throw new RuntimeException(e);
        }
    }
}
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的工作流节点克隆

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/base/node.py`
**核心代码**（行 1-40）：

```python
from typing import Any

class Node:
    """工作流节点基类——支持克隆"""

    def __init__(self, id: str, config: dict):
        self.id = id
        self.config = config
        self.state: dict = {}

    def clone(self, new_id: str) -> "Node":
        """克隆节点——用于工作流复制/复用"""
        from copy import deepcopy
        new_node = self.__class__.__new__(self.__class__)
        new_node.id = new_id
        new_node.config = deepcopy(self.config)
        new_node.state = {}
        return new_node
```

**解读**：
- 工作流节点经常需要复用（如模板）
- `clone()` 用 `deepcopy` 避免共享引用
- **整体设计**：dify 用原型模式支持工作流节点复用

### 3.2 ruoyi 的 BeanUtils.copyProperties

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/object/BeanUtils.java`
**核心代码**：

```java
public class BeanUtils {
    /**
     * 拷贝属性——浅拷贝对象（基于反射）
     */
    public static <T> T copyProperties(Object source, Class<T> targetClass) {
        try {
            T target = targetClass.getDeclaredConstructor().newInstance();
            org.springframework.beans.BeanUtils.copyProperties(source, target);
            return target;
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
```

**解读**：
- `BeanUtils.copyProperties` 是 Spring 的属性拷贝工具——浅拷贝
- 用法：把 DO（持久化对象）转为 VO（视图对象）
- **整体设计**：ruoyi 用浅拷贝做对象转换（DTO/VO/DO 之间）

## 4. 关键要点总结

- 原型模式 = 克隆代替 new
- 浅拷贝只拷贝顶层，深拷贝递归拷贝
- Python：`copy.copy()` / `copy.deepcopy()`
- Java：实现 `Cloneable` 接口
- dify 工作流节点用 `deepcopy` 克隆，ruoyi 用 `BeanUtils.copyProperties` 浅拷贝

## 5. 练习题

### 练习 1：基础
演示浅拷贝和深拷贝的区别（修改深拷贝对象不影响原对象）。

### 练习 2：进阶
阅读 `dify/api/core/workflow/nodes/base/node.py`，分析节点克隆的具体逻辑。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/base/node.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`
- 《设计模式》第 3 章：原型模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13