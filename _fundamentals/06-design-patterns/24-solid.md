# 4.1 SOLID 原则

> SOLID 是面向对象设计的 5 大原则，是写出可维护代码的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 SOLID 五大原则
- 在代码中识别违反 SOLID 的反模式
- 在 dify/ruoyi 中应用 SOLID 原则
- 用 SOLID 评估现有设计

## 📚 前置知识

- 前面所有设计模式（01-23）
- 面向对象基础

## 1. 核心概念

### 1.1 SOLID 五大原则

| 缩写 | 原则 | 核心思想 |
|------|------|---------|
| S | 单一职责（Single Responsibility） | 一个类只做一件事 |
| O | 开闭（Open/Closed） | 对扩展开放，对修改关闭 |
| L | 里氏替换（Liskov Substitution） | 子类可替换父类 |
| I | 接口隔离（Interface Segregation） | 接口要小而专 |
| D | 依赖倒置（Dependency Inversion） | 依赖抽象，不依赖具体 |

## 2. 代码示例

### 2.1 S - 单一职责

```python
# ❌ 反例：一个类做太多事
class User:
    def save_to_db(self, user): ...
    def send_email(self, user, content): ...
    def generate_report(self, users): ...

# ✅ 正例：拆分职责
class UserRepository:
    def save(self, user): ...

class EmailService:
    def send(self, user, content): ...

class UserReportGenerator:
    def generate(self, users): ...
```

### 2.2 O - 开闭原则

```python
# ❌ 反例：每加一种支付都要改
class PaymentProcessor:
    def process(self, type, amount):
        if type == "stripe":
            ...
        elif type == "paypal":  # 每加一种都要改这里
            ...

# ✅ 正例：对扩展开放（新增支付方式），对修改关闭
class PaymentProcessor:
    def __init__(self, strategies: dict):
        self.strategies = strategies  # 注册式

    def process(self, type, amount):
        return self.strategies[type].pay(amount)
```

### 2.3 L - 里氏替换

```python
# ❌ 反例：子类违反父类契约
class Rectangle:
    def set_width(self, w): self.width = w
    def set_height(self, h): self.height = h

class Square(Rectangle):  # ❌ Square 不是 Rectangle
    def set_width(self, w):
        self.width = self.height = w   # 违反预期！
```

### 2.4 I - 接口隔离

```python
# ❌ 反例：胖接口
class Worker(ABC):
    @abstractmethod
    def work(self): ...
    @abstractmethod
    def eat(self): ...
    @abstractmethod
    def sleep(self): ...

# 机器人不需要 eat/sleep
class Robot(Worker):
    def eat(self): raise NotImplementedError   # ❌

# ✅ 正例：拆分接口
class Workable(ABC):
    @abstractmethod
    def work(self): ...

class Eatable(ABC):
    @abstractmethod
    def eat(self): ...

class Robot(Workable):  # 只实现需要的
    def work(self): ...
```

### 2.5 D - 依赖倒置

```python
# ❌ 反例：高层依赖底层
class OrderService:
    def __init__(self):
        self.mysql = MySQLClient()  # 依赖具体实现

# ✅ 正例：依赖抽象
class OrderService:
    def __init__(self, db: Database):  # 依赖抽象接口
        self.db = db
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的 SOLID 应用

**文件位置**：`/Users/xu/code/github/dify/api/core/provider_manager.py`
**核心代码**（行 1-30）：

```python
from abc import ABC, abstractmethod

class LLM(ABC):
    """抽象接口（DIP）"""
    @abstractmethod
    def invoke(self, prompt: str) -> dict: ...

# 具体实现（OCP）
class OpenAILLM(LLM):
    def invoke(self, prompt: str) -> dict: ...

class AnthropicLLM(LLM):
    def invoke(self, prompt: str) -> dict: ...

# 客户端只依赖抽象
class WorkflowRunner:
    def __init__(self, llm: LLM):  # 依赖抽象
        self.llm = llm

    def run(self, prompt):
        return self.llm.invoke(prompt)  # 多态
```

**解读**：
- `LLM` 抽象接口 → DIP（依赖倒置）
- 具体实现独立扩展 → OCP（开闭原则）
- `WorkflowRunner` 只依赖 `LLM` 接口 → 可测试

### 3.2 ruoyi 的 SOLID 应用

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserService.java`
**核心代码**：

```java
public interface AdminUserService {
    // ISP：接口隔离——只暴露用户管理相关方法
    Long createUser(UserSaveReqVO reqVO);
    void updateUser(UserSaveReqVO reqVO);
    void deleteUser(Long id);
    AdminUserDO getUser(Long id);
}

// Service 实现类只做用户管理（SRP）
@Service
public class AdminUserServiceImpl implements AdminUserService {
    @Resource
    private AdminUserMapper userMapper;  // DIP：依赖抽象接口
    // ... 单一职责：只管用户
}
```

**解读**：
- `AdminUserService` 接口小而专（ISP）
- `AdminUserServiceImpl` 单一职责（SRP）：只管用户
- 依赖 `AdminUserMapper` 抽象接口（DIP）
- **整体设计**：ruoyi 严格遵守 SOLID

## 4. 关键要点总结

- SOLID 是 OOP 设计的 5 大原则
- S：单一职责（一个类一个职责）
- O：开闭原则（对扩展开放、对修改关闭）
- L：里氏替换（子类可替换父类）
- I：接口隔离（小接口，不强迫实现不需要的方法）
- D：依赖倒置（依赖抽象，不依赖具体）
- dify/ruoyi 都遵循 SOLID 设计

## 5. 练习题

### 练习 1：基础
评估你的项目代码，找出违反 SOLID 原则的 3 个地方。

### 练习 2：进阶
阅读 dify 的 `provider_manager.py`，分析它如何同时满足 OCP 和 DIP。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/provider_manager.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- 《敏捷软件开发：原则、模式与实践》（Robert C. Martin）

---

**文档版本**：v1.0
**最后更新**：2026-07-13