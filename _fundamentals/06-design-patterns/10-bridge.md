# 2.5 桥接模式（Bridge）

> 桥接模式将抽象部分与实现部分分离，使它们可以独立变化。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解桥接模式的核心（抽象与实现分离）
- 区分桥接 vs 适配器 vs 装饰器
- 在 dify/ruoyi 中识别桥接应用
- 知道何时该用桥接

## 📚 前置知识

- 06-adapter.md
- 07-decorator.md

## 1. 核心概念

### 1.1 桥接的核心思想

把"抽象"和"实现"两个维度**解耦**，让它们各自独立变化，避免类爆炸。

### 1.2 类爆炸问题

```
形状（圆形、矩形、三角形）
  + 颜色（红、蓝、绿）
    = 3 × 3 = 9 个类
```

桥接后：3 个形状 + 3 个颜色 = 6 个类，且各自独立扩展。

### 1.3 桥接 vs 适配器

| 维度 | 桥接 | 适配器 |
|------|------|--------|
| 目的 | 抽象与实现解耦 | 接口兼容 |
| 时机 | 设计时就分离 | 已有类不兼容时补救 |
| 关系 | 双向 | 通常单向 |

## 2. 代码示例

### 2.1 经典桥接：形状 + 颜色

```python
from abc import ABC, abstractmethod

# 实现部分：颜色
class Color(ABC):
    @abstractmethod
    def fill(self) -> str: ...

class RedColor(Color):
    def fill(self) -> str:
        return "red"

class BlueColor(Color):
    def fill(self) -> str:
        return "blue"

# 抽象部分：形状（持有颜色引用——桥接）
class Shape(ABC):
    def __init__(self, color: Color):
        self.color = color   # 桥接！

    @abstractmethod
    def draw(self) -> str: ...

class Circle(Shape):
    def draw(self) -> str:
        return f"Circle filled with {self.color.fill()}"

class Rectangle(Shape):
    def draw(self) -> str:
        return f"Rectangle filled with {self.color.fill()}"


# 使用：自由组合
red_circle = Circle(RedColor())
print(red_circle.draw())  # "Circle filled with red"

blue_rect = Rectangle(BlueColor())
print(blue_rect.draw())  # "Rectangle filled with blue"
```

### 2.2 JDBC 是经典的桥接模式

```
JDBC API（抽象）
   ↓
DriverManager（桥）
   ↓
MySQL Driver / Oracle Driver / PostgreSQL Driver（实现）
```

JDBC API 不依赖任何数据库，但通过 Driver 桥接可以连接任何数据库。

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的模型类型 + 提供商桥接

**文件位置**：`/Users/xu/code/github/dify/api/core/provider_manager.py`
**核心代码**（行 30-60）：

```python
class ProviderModelBundle:
    """模型 bundle——桥接模型类型和提供商"""
    def __init__(self, configuration: ProviderConfiguration, model_type_instance):
        self.configuration = configuration           # 抽象：提供商配置
        self.model_type_instance = model_type_instance  # 实现：模型类型实例


class ModelInstance:
    """模型实例——桥接 ProviderModelBundle 和具体调用"""

    def __init__(self, provider_model_bundle: ProviderModelBundle, model: str):
        self.provider_model_bundle = provider_model_bundle
        self.model_name = model

    def invoke(self, prompt: str) -> dict:
        """调用模型——通过 bundle 桥接"""
        model = self.provider_model_bundle.model_type_instance.get_model(...)
        return model.invoke(prompt)
```

**解读**：
- 模型类型（LLM/Embedding/Rerank）和提供商（OpenAI/Anthropic）独立变化
- `ProviderModelBundle` 把两者桥接起来
- **整体设计**：用桥接解耦模型类型和提供商

### 3.2 ruoyi 的数据库 + 业务桥接

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`
**核心代码**：

```java
// MyBatis 通过 SqlSessionFactory 桥接应用代码和数据库驱动
public class SqlSessionFactoryBean {
    private DataSource dataSource;       // 抽象：数据源
    private Resource[] mapperLocations;  // 实现：SQL 映射

    public SqlSessionFactory getObject() throws Exception {
        // 用 DataSource + Mapper 桥接应用代码和数据库
        SqlSessionFactory factory = new SqlSessionFactoryBuilder().build(configuration);
        return factory;
    }
}
```

**解读**：
- 应用代码不直接用 JDBC，而是用 SqlSession（抽象）
- SqlSessionFactory 桥接 DataSource（MySQL/PG/Oracle）
- **整体设计**：MyBatis 用桥接屏蔽数据库差异

## 4. 关键要点总结

- 桥接 = 抽象与实现分离
- 解决多维度变化的类爆炸问题
- JDBC 是经典桥接
- dify 的 ProviderModelBundle、ruoyi 的 SqlSessionFactory 都是桥接
- 与适配器区别：桥接是设计时解耦，适配器是已有类兼容

## 5. 练习题

### 练习 1：基础
设计 `Logger`（FileLogger / ConsoleLogger / NetworkLogger）+ `LogFormatter`（JSON / PlainText）的桥接模式。

### 练习 2：进阶
阅读 dify 的 `ProviderModelBundle`，分析它如何桥接模型类型和提供商。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/provider_manager.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`
- 《设计模式》第 4 章：桥接模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13