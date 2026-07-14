# 1.3 抽象工厂模式（Abstract Factory）

> 抽象工厂是工厂方法的"升级版"——创建**一族**相关对象，而不是单个对象。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分抽象工厂 vs 工厂方法
- 掌握抽象工厂的实现结构
- 在 dify/ruoyi 中识别抽象工厂
- 知道抽象工厂的适用场景

## 📚 前置知识

- 02-factory-method.md
- 继承/接口

## 1. 核心概念

### 1.1 工厂方法 vs 抽象工厂

| 维度 | 工厂方法 | 抽象工厂 |
|------|---------|---------|
| 创建数量 | 1 种产品 | **一族**产品 |
| 抽象层级 | 1 个抽象方法 | **多个**抽象方法 |
| 复杂度 | 较低 | 较高 |
| 适用 | 单产品变体 | 多产品族配套 |

### 1.2 抽象工厂的组成

```
抽象工厂（AbstractFactory）
├── create_product_a() → AbstractProductA
├── create_product_b() → AbstractProductB
└── create_product_c() → AbstractProductC

具体工厂 1（Factory1）：创建 A1, B1, C1
具体工厂 2（Factory2）：创建 A2, B2, C2
```

### 1.3 经典案例：跨平台 UI

```
WindowsFactory → WindowsButton + WindowsMenu + WindowsDialog
MacFactory     → MacButton + MacMenu + MacDialog
LinuxFactory   → LinuxButton + LinuxMenu + LinuxDialog
```

**约束**：同一族产品必须一起使用（如所有 UI 都是 Windows 风格）。

## 2. 代码示例

### 2.1 Python 抽象工厂

```python
from abc import ABC, abstractmethod

# 抽象产品族
class Button(ABC):
    @abstractmethod
    def render(self) -> str:
        pass

class Menu(ABC):
    @abstractmethod
    def render(self) -> str:
        pass

# 具体产品
class WindowsButton(Button):
    def render(self) -> str:
        return "[Windows Button]"

class MacButton(Button):
    def render(self) -> str:
        return "(Mac Button)"

class WindowsMenu(Menu):
    def render(self) -> str:
        return "[Windows Menu]"

class MacMenu(Menu):
    def render(self) -> str:
        return "(Mac Menu)"

# 抽象工厂
class UIFactory(ABC):
    @abstractmethod
    def create_button(self) -> Button:
        pass

    @abstractmethod
    def create_menu(self) -> Menu:
        pass

# 具体工厂
class WindowsFactory(UIFactory):
    def create_button(self) -> Button:
        return WindowsButton()

    def create_menu(self) -> Menu:
        return WindowsMenu()

class MacFactory(UIFactory):
    def create_button(self) -> Button:
        return MacButton()

    def create_menu(self) -> Menu:
        return MacMenu()


# 客户端
def create_ui(factory: UIFactory) -> None:
    button = factory.create_button()
    menu = factory.create_menu()
    print(button.render(), "+", menu.render())

create_ui(WindowsFactory())  # [Windows Button] + [Windows Menu]
create_ui(MacFactory())      # (Mac Button) + (Mac Menu)
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的模型提供商工厂

**文件位置**：`/Users/xu/code/github/dify/api/core/provider_manager.py`
**核心代码**（行 1-50）：

```python
from typing import Type

from core.entities.provider_entities import ModelType

class ProviderManager:
    """模型提供商管理器——多种模型类型的统一创建"""

    def get_provider_model_bundle(
        self, provider: str, model_type: str
    ) -> "ProviderModelBundle":
        """创建模型 bundle——抽象工厂的一种实现"""
        if model_type == ModelType.LLM:
            return self._create_llm_bundle(provider)
        elif model_type == ModelType.TEXT_EMBEDDING:
            return self._create_embedding_bundle(provider)
        elif model_type == ModelType.RERANK:
            return self._create_rerank_bundle(provider)
        raise ValueError(f"Unknown model type: {model_type}")
```

**解读**：
- 不同 model_type（LLM/Embedding/Rerank）需要不同的模型实现
- `ProviderManager` 协调创建多种模型——抽象工厂
- **整体设计**：dify 把 OpenAI、Anthropic 等多家模型提供商的多种模型类型统一封装

### 3.2 ruoyi 的多数据库适配

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/`
**核心代码**：

```java
public abstract class BaseDO {
    // 抽象基类，MyBatis Plus 自动适配 MySQL/PostgreSQL/Oracle 等数据库
    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}

// 通过方言（Dialect）适配不同数据库——抽象工厂的核心思想
// MySQLDialect, PostgreSQLDialect, OracleDialect 都是 DialectFactory 的具体实现
```

**解读**：
- ruoyi 通过 MyBatis Plus 方言（Dialect）适配多种数据库
- 不同数据库有不同的 SQL 方言实现——典型的抽象工厂

## 4. 关键要点总结

- 抽象工厂 = 工厂方法的"产品族"版本
- 一族产品必须配套使用（如 UI 风格统一）
- 优点：保证产品族一致性
- 缺点：扩展产品族需要修改所有工厂（违反开闭原则）
- dify/ruoyi 中识别：管理多种类型的统一创建

## 5. 练习题

### 练习 1：基础
为不同操作系统（Windows/Mac/Linux）的"按钮 + 菜单 + 复选框"实现抽象工厂。

### 练习 2：进阶
阅读 dify 的 `ProviderManager`，分析它如何管理多个模型提供商的多种模型类型。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/provider_manager.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`
- 《设计模式》第 3 章：创建型模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13