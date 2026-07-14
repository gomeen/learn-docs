# 4.3 反模式：常见错误用法

> 反模式（Anti-Pattern）是看似合理但实际有害的设计。学习反模式能帮你避开常见陷阱。

## 🎯 学习目标

完成本文档后，你将能够：
- 识别常见的反模式
- 知道每个反模式的危害
- 学会如何重构
- 在 dify/ruoyi 中识别反模式

## 📚 前置知识

- 01-25 所有内容
- 实际项目经验

## 1. 核心反模式清单

| 反模式 | 表现 | 危害 |
|--------|------|------|
| 上帝对象（God Object） | 一个类做所有事 | 难以维护、测试 |
| 贫血模型（Anemic Domain Model） | 只有 getter/setter | 业务逻辑分散 |
| 大泥球（Big Ball of Mud） | 无架构 | 难以理解 |
| 过度设计 | 简单问题用复杂模式 | 增加复杂度 |
| 重复造轮子 | 自己实现已有功能 | 浪费时间 |
| 硬编码 | 魔法值散落代码 | 难以修改 |
| 回调地狱 | 嵌套回调 | 难以阅读 |
| 循环依赖 | A 依赖 B，B 依赖 A | 难以重构 |
| 数据库作为集成点 | 多个服务共享同一数据库 | 紧耦合 |

## 2. 代码示例

### 2.1 上帝对象

```python
# ❌ 反例：1 个类做 100 件事
class OrderManager:
    def create_order(self): ...
    def send_email(self): ...
    def process_payment(self): ...
    def update_inventory(self): ...
    def generate_invoice(self): ...
    def send_sms(self): ...
    def log_audit(self): ...

# ✅ 重构：单一职责
class OrderCreator: ...
class PaymentProcessor: ...
class InventoryUpdater: ...
class InvoiceGenerator: ...
class NotificationService: ...
```

### 2.2 贫血模型

```python
# ❌ 反例：只有 getter/setter，业务逻辑在 Service
class User:
    def __init__(self, name):
        self.name = name

class UserService:
    def is_adult(self, user):
        return user.age >= 18  # 业务逻辑不在 User

# ✅ 重构：模型有行为
class User:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def is_adult(self) -> bool:
        return self.age >= 18  # 行为在模型
```

### 2.3 回调地狱

```python
# ❌ 反例：嵌套回调
def get_user_posts(user_id, callback):
    db.get_user(user_id, lambda user:
        db.get_posts(user.id, lambda posts:
            callback(posts)))

# ✅ 重构：async/await
async def get_user_posts(user_id):
    user = await db.get_user(user_id)
    posts = await db.get_posts(user.id)
    return posts
```

### 2.4 硬编码

```python
# ❌ 反例：魔法值
if user.role == 3:  # 3 是什么意思？
    grant_admin()

# ✅ 重构：枚举或常量
class UserRole:
    ADMIN = 1
    USER = 2
    GUEST = 3

if user.role == UserRole.ADMIN:
    grant_admin()
```

### 2.5 循环依赖

```python
# ❌ 反例：A 依赖 B，B 依赖 A
class A:
    def __init__(self):
        self.b = B()  # A 依赖 B

class B:
    def __init__(self):
        self.a = A()  # B 又依赖 A

# ✅ 重构：引入中介或反转
class C:  # 中介
    def __init__(self):
        self.a = A()
        self.b = B()
        self.a.partner = self.b
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 避免的反模式

**示例**：避免上帝对象

**位置**：`/Users/xu/code/github/dify/api/services/`
**核心代码**：

```python
# dify 的 Service 层每个类职责单一
class WorkflowService:
    """只管工作流"""
    def run_workflow(self): ...

class AccountService:
    """只管账户"""
    def create_account(self): ...

class DatasetService:
    """只管数据集"""
    def create_dataset(self): ...
```

**解读**：
- dify 的 Service 按业务拆分，每个只管一个领域
- 避免上帝对象反模式
- **整体设计**：清晰的职责划分

### 3.2 ruoyi 的常见反模式

**示例**：MyBatis Plus 的 IService 容易导致贫血模型

```java
// ❌ 反模式：业务全在 Service
public class OrderServiceImpl extends ServiceImpl<OrderMapper, OrderDO> {
    public void cancelOrder(Long id) {
        OrderDO order = getById(id);
        if (order.getStatus() == 1) {  // 状态判断硬编码
            order.setStatus(2);
            updateById(order);
        }
    }
}

// ✅ 重构：状态机 + 模型行为
public class OrderDO {
    public void cancel() {  // 行为在模型
        if (this.status != OrderStatus.PAID) {
            throw new IllegalStateException("...");
        }
        this.status = OrderStatus.CANCELLED;
    }
}
```

**解读**：
- ruoyi 的 MyBatis Plus 容易导致贫血模型（Service 接管所有业务）
- 改进方向：状态机 + 模型自带行为
- **整体设计**：ruoyi 的 Service 层较厚，需要重构

### 3.3 数据库作为集成点反模式

```python
# ❌ 反例：两个服务共享同一张表
# order_service 直接读 user_service 的 users 表
def get_user_for_order(user_id):
    return db.query("SELECT * FROM users WHERE id = ?", user_id)
    # 直接访问其他服务的表

# ✅ 重构：通过 API 调用
def get_user_for_order(user_id):
    return user_service_client.get_user(user_id)  # API 调用
```

**解读**：
- dify/ruoyi 早期都有这个反模式
- 微服务化后必须通过 API 通信

## 4. 关键要点总结

- 反模式 = 看似合理但实际有害的设计
- 常见：上帝对象、贫血模型、大泥球、过度设计、硬编码
- 重构方向：单一职责、行为上移、依赖反转
- dify Service 层职责清晰，ruoyi Service 较厚需改进
- 简单优于复杂，不要为了模式而模式

## 5. 练习题

### 练习 1：基础
在你的代码中找出一个反模式，重构它。

### 练习 2：进阶
阅读 ruoyi 的 `AdminUserServiceImpl.java`，分析它是否贫血模型。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- 《重构：改善既有代码的设计》第 3 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13