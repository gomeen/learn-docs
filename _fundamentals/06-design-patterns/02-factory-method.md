# 1.2 工厂方法模式（Factory Method）

> 工厂方法把"对象的创建"延迟到子类。Spring 的 BeanFactory、MyBatis 的 SqlSessionFactory 都是典型应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解工厂方法 vs 简单工厂的区别
- 掌握 Python/Java 的工厂方法实现
- 识别 dify/ruoyi 中的工厂方法
- 知道何时该用工厂方法

## 📚 前置知识

- 01-singleton.md
- 继承/多态基础

## 1. 核心概念

### 1.1 简单工厂 vs 工厂方法

| 维度 | 简单工厂 | 工厂方法 |
|------|---------|---------|
| 创建逻辑 | 在一个方法中用 if/else | 在子类中重写方法 |
| 扩展性 | ❌ 违反开闭原则 | ✅ 符合开闭原则 |
| 类数量 | 1 个工厂类 | 1 个抽象工厂 + N 个子类 |

### 1.2 工厂方法四要素

1. **抽象产品（Product）**：定义产品接口
2. **具体产品（ConcreteProduct）**：实现产品
3. **抽象工厂（Creator）**：声明工厂方法
4. **具体工厂（ConcreteCreator）**：实现工厂方法

### 1.3 适用场景

- 创建对象需要复杂逻辑（不只是 `new`）
- 需要根据配置决定创建哪个对象
- 客户端不需要知道具体类名

## 2. 代码示例

### 2.1 Python 工厂方法实现

```python
from abc import ABC, abstractmethod

# 抽象产品
class LLM(ABC):
    @abstractmethod
    def invoke(self, prompt: str) -> str:
        pass

# 具体产品
class OpenAILLM(LLM):
    def invoke(self, prompt: str) -> str:
        return f"OpenAI response to: {prompt}"

class AnthropicLLM(LLM):
    def invoke(self, prompt: str) -> str:
        return f"Anthropic response to: {prompt}"

# 抽象工厂
class LLMFactory(ABC):
    @abstractmethod
    def create_llm(self) -> LLM:
        pass

# 具体工厂
class OpenAIFactory(LLMFactory):
    def create_llm(self) -> LLM:
        return OpenAILLM()

class AnthropicFactory(LLMFactory):
    def create_llm(self) -> LLM:
        return AnthropicLLM()


# 使用：根据配置选择工厂
def get_factory(provider: str) -> LLMFactory:
    factories = {
        "openai": OpenAIFactory(),
        "anthropic": AnthropicFactory(),
    }
    return factories[provider]

factory = get_factory("openai")
llm = factory.create_llm()
print(llm.invoke("Hello"))  # OpenAI response to: Hello
```

### 2.2 Java 工厂方法

```java
// 抽象产品
public interface LLM {
    String invoke(String prompt);
}

// 抽象工厂
public abstract class LLMFactory {
    public abstract LLM createLLM();

    // 模板方法 + 工厂方法
    public String generate(String prompt) {
        LLM llm = createLLM();
        return llm.invoke(prompt);
    }
}

// 具体工厂
public class OpenAIFactory extends LLMFactory {
    @Override
    public LLM createLLM() {
        return new OpenAILLM();
    }
}
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的工具工厂（ToolManager）

**文件位置**：`/Users/xu/code/github/dify/api/core/tools/tool_manager.py`
**核心代码**（行 1-30）：

```python
from typing import Type

from core.tools.__base.tool import Tool
from core.tools.builtin_tool.provider import BuiltinToolProvider

class ToolManager:
    """工具管理器——根据类型创建工具（工厂方法）"""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def get_tool(self, provider: str, tool_name: str) -> Tool:
        """根据 provider 名称返回具体工具——工厂方法"""
        if provider == "builtin":
            return BuiltinToolProvider(self.tenant_id).get_tool(tool_name)
        elif provider == "custom":
            return CustomToolProvider(self.tenant_id).get_tool(tool_name)
        elif provider == "workflow":
            return WorkflowToolProvider(self.tenant_id).get_tool(tool_name)
        raise ValueError(f"Unknown provider: {provider}")
```

**解读**：
- `get_tool()` 就是工厂方法——根据 provider 类型返回不同工具实例
- 第 19-22 行：扩展时需要修改 `get_tool()`（违反开闭原则，可以改进为更优雅的注册式工厂）
- **整体设计**：dify 用工厂方法管理 3 种工具源（builtin / custom / workflow）

### 3.2 ruoyi 的 MyBatis SqlSessionFactory

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
**核心代码**：

```java
@Bean
public SqlSessionFactory sqlSessionFactory(DataSource dataSource) throws Exception {
    SqlSessionFactoryBean factoryBean = new SqlSessionFactoryBean();
    factoryBean.setDataSource(dataSource);
    factoryBean.setMapperLocations(
        new PathMatchingResourcePatternResolver()
            .getResources("classpath*:mapper/**/*Mapper.xml")
    );
    return factoryBean.getObject();
}
```

**解读**：
- `SqlSessionFactory` 是 MyBatis 的核心工厂——创建 SqlSession
- 通过工厂方法动态创建 MyBatis 会话
- **整体设计**：MyBatis 用工厂方法统一管理数据库会话

## 4. 关键要点总结

- 工厂方法 = 把对象的创建延迟到子类
- 简单工厂 vs 工厂方法：后者更符合开闭原则
- Python 用 ABC + 类继承实现
- Java 用抽象类 + 重写方法实现
- dify 的 ToolManager、ruoyi 的 SqlSessionFactory 都是工厂方法

## 5. 练习题

### 练习 1：基础
为不同类型的邮件通知（SendGrid、Mailgun、SES）实现工厂方法模式。

### 练习 2：进阶
阅读 `dify/api/core/tools/tool_manager.py`，把它改造成注册式工厂（用字典 + 类引用）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/tools/tool_manager.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`
- 《设计模式：可复用面向对象软件的基础》第 3 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13