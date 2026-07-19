# 2.1.5 依赖注入：构造函数注入与控制反转

> 理解依赖注入（DI）和控制反转（IoC），掌握 dify 中通过构造函数注入依赖的方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解控制反转（IoC）和依赖注入（DI）的关系
- 掌握三种注入方式：构造函数注入、属性注入、方法注入
- 在 dify 仓库中找到构造函数注入的具体用法
- 用依赖注入编写可测试的代码

## 📚 前置知识

- [分层架构](./02-layered-architecture.md)
- [Repository 模式](./03-repository-pattern.md)
- Python 类与构造函数基础

## 1. 核心概念

### 1.1 控制反转（IoC）

传统代码：对象自己创建依赖（**主动控制**）：

```python
# ❌ 没有 IoC：对象自己创建依赖
class OrderService:
    def __init__(self):
        self.db = MySQLConnection()  # 自己 new
        self.repo = SqlOrderRepository(self.db)
```

IoC 代码：**容器/调用方**负责注入依赖（**控制权反转**）：

```python
# ✅ IoC：依赖从外部传入
class OrderService:
    def __init__(self, db, repo):
        self.db = db
        self.repo = repo  # 由调用方决定传什么

# 由调用方注入
service = OrderService(db=MySQLConnection(), repo=SqlOrderRepository())
```

**IoC 的好处**：
- 解耦：对象不依赖具体实现
- 可测试：测试时传入 Mock 对象
- 灵活：运行时切换实现

### 1.2 三种注入方式

| 方式 | 语法 | 优点 | 缺点 |
|------|------|------|------|
| 构造函数注入 | `__init__(self, dep)` | 不可变、强制依赖 | 参数过多时构造复杂 |
| 属性注入 | `self.dep = dep` | 灵活、可选依赖 | 状态可变、难追踪 |
| 方法注入 | `do_work(self, dep)` | 每次调用灵活 | 调用方负担重 |

**最佳实践**：**优先使用构造函数注入**，只在可选依赖或测试场景使用属性注入。

### 1.3 dify 的依赖注入方式

dify 仓库中常见的注入方式：

1. **构造函数注入（最常用）**：Service 类、Repository 实现
   ```python
   class WorkflowService:
       def __init__(self, session_factory):
           self._session_factory = session_factory
   ```

2. **装饰器注入（Controller 层）**：通过 `@with_current_user`、`@get_app_model` 装饰器注入参数（装饰器原理详见 [装饰器](../01-fundamentals/10-decorator.md)）
   ```python
   @with_current_user
   def get(self, current_user: Account):
       ...
   ```

3. **全局单例（少量场景）**：`db.session`、`redis_client` 通过 `extensions/ext_*.py` 初始化为全局对象（单例模式详见 [单例](../../_fundamentals/06-design-patterns/01-singleton.md)）

### 1.4 DI 容器 vs 手动注入

大型框架（Spring、Django）有 DI 容器。dify 没有显式 DI 容器，依赖通过：
- 构造函数参数显式传递
- 装饰器自动注入（针对 Flask request context）
- `extensions/ext_*.py` 模块级单例

## 2. 代码示例

### 2.1 构造函数注入（推荐）

```python
from abc import ABC, abstractmethod

# 定义接口（ABC 详见 [抽象基类 ABC](../01-fundamentals/19-abc.md)）
class UserRepository(ABC):
    @abstractmethod
    def find_by_id(self, user_id: str): ...

class EmailService(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str): ...

# Service 通过构造函数接收依赖
class UserApplicationService:
    def __init__(
        self,
        user_repo: UserRepository,
        email_service: EmailService,
    ):
        self._user_repo = user_repo
        self._email_service = email_service

    def register(self, email: str):
        user = self._user_repo.find_by_id(email)
        if user:
            raise ValueError("用户已存在")
        # ... 创建用户
        self._email_service.send(email, "欢迎", "欢迎注册")


# 生产环境：传入真实实现
service = UserApplicationService(
    user_repo=SqlUserRepository(session),
    email_service=SmtpEmailService(),
)

# 测试环境：传入 Mock
service = UserApplicationService(
    user_repo=InMemoryUserRepository(),
    email_service=MockEmailService(),
)
```

### 2.2 属性注入（可选依赖）

```python
class ImageProcessor:
    def __init__(self):
        self._cache: Cache | None = None  # 可选依赖
        self._storage: Storage | None = None

    def set_cache(self, cache: Cache):
        """可选依赖，通过 setter 注入"""
        self._cache = cache

    def process(self, image: bytes) -> bytes:
        if self._cache:
            cached = self._cache.get(image)
            if cached:
                return cached
        result = self._do_process(image)
        if self._cache:
            self._cache.set(image, result)
        return result


# 基础用法
proc = ImageProcessor()
proc.process(image)  # 没有缓存

# 高级用法
proc.set_cache(RedisCache())
proc.process(image)  # 有缓存
```

### 2.3 常见错误：服务定位器反模式

```python
# ❌ 错误：Service Locator（隐藏依赖）
class BadOrderService:
    def create_order(self, items):
        # 直接访问全局容器——依赖关系不透明
        repo = ServiceLocator.get("OrderRepository")
        email = ServiceLocator.get("EmailService")
        repo.save(items)
        email.send(...)

# ✅ 正确：构造函数注入（依赖关系明确）
class GoodOrderService:
    def __init__(self, order_repo, email_service):
        self._order_repo = order_repo
        self._email_service = email_service

    def create_order(self, items):
        self._order_repo.save(items)
        self._email_service.send(...)
```

### 2.4 常见错误：循环依赖

```python
# ❌ 循环依赖：A 依赖 B，B 依赖 A
class A:
    def __init__(self, b: "B"):
        self._b = b

class B:
    def __init__(self, a: "A"):
        self._a = a

# 解决：抽取第三个对象 C，或者延迟注入（方法参数注入）
class BetterA:
    def __init__(self):
        self._b: B | None = None

    def set_b(self, b: B):
        self._b = b
```

## 3. dify 仓库源码解读

### 3.1 构造函数注入：`SQLAlchemyWorkflowExecutionRepository`

**文件位置**：`/Users/xu/code/github/dify/api/core/repositories/sqlalchemy_workflow_execution_repository.py`
**核心代码**（行 40-60）：

```python
def __init__(
    self,
    session_factory: sessionmaker | Engine,
    user: Account | EndUser,
    app_id: str | None,
    triggered_from: WorkflowRunTriggeredFrom | None,
):
    """Initialize the repository with a SQLAlchemy sessionmaker or engine and context information.

    Args:
        session_factory: SQLAlchemy sessionmaker or engine（依赖注入）
        user: Account or EndUser object（上下文对象）
        app_id: Application ID（多租户隔离）
        triggered_from: Source of the execution trigger（触发来源）
    """
    self._session_factory = session_factory
    self._user = user
    self._app_id = app_id
    self._triggered_from = triggered_from
```

**解读**：
- 第 2-7 行：4 个参数全部通过构造函数注入
- 第 3 行：`sessionmaker | Engine` 是 Union 类型——支持两种注入方式（sessionmaker 是工厂，Engine 是连接池）
- 第 4 行：`Account | EndUser` 也是 Union 类型——不同调用场景注入不同用户类型
- `app_id` 等上下文用于多租户隔离（详见 [多租户架构](./20-multi-tenancy.md)）
- **优点**：测试时可以传入 `MockEngine`、`FakeUser`，无需修改任何业务代码

### 3.2 装饰器注入：`@with_current_user`

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/wraps.py`
**核心代码**（行 603-622）：

```python
def with_current_user[T, **P, R](
    view: Callable[Concatenate[T, Account, P], R],
) -> Callable[Concatenate[T, P], R]:
    """Inject the current authenticated Account into the handler as the first argument after self.

    Usage::

        class MyResource(Resource):
            @login_required
            @with_current_user
            def get(self, current_user: Account):
                ...
    """

    @wraps(view)
    def decorated(self: T, *args: P.args, **kwargs: P.kwargs) -> R:
        current_user, _ = current_account_with_tenant()
        return view(self, current_user, *args, **kwargs)

    return decorated
```

**解读**：
- 第 1-3 行：装饰器签名使用泛型 `T, **P, R`，保证类型安全（详见 [Protocol 与 Generic](../01-fundamentals/09-protocol-generic.md)）
- 第 13 行：装饰器从 Flask context（`current_account_with_tenant()`）取出当前用户（上下文详见 [Flask 上下文](./09-flask-context.md)）
- 第 14 行：把 `current_user` 注入到视图函数的参数列表中
- **本质是方法参数注入**：每个请求都会被注入一个 `current_user` 参数

### 3.3 单例注入：`ext_database`

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**（行 50-65）：

```python
def init_app(app: DifyApp):
    db.init_app(app)
    _setup_gevent_compatibility()

    # Eagerly build the engine so pool_size/max_overflow/etc. come from config
    try:
        with app.app_context():
            _ = db.engine  # triggers engine creation with the configured options
    except Exception:
        logger.exception("Failed to initialize SQLAlchemy engine during app startup")
```

**解读**：
- 第 2 行：`db.init_app(app)` 把 Flask app 绑定到 SQLAlchemy
- 第 8 行：在应用启动时立即构建 engine（预先创建连接池）
- 这是一种**全局单例 + Flask app context** 的注入模式：
  - 通过 `from extensions.ext_database import db` 在任何地方访问
  - 但底层根据当前 Flask request 自动绑定 session

## 4. 关键要点总结

- **构造函数注入**是最推荐的 DI 方式：依赖关系明确、不可变、便于测试
- dify 三种注入方式并存：
  - 构造函数注入：Repository、Service 层
  - 装饰器注入：Controller 层（`@with_current_user`、`@get_app_model`）
  - 单例注入：`db`、`redis_client`、`storage` 等基础设施
- 避免**服务定位器反模式**：不要在类内部调用全局工厂获取依赖
- 循环依赖通过**延迟注入**（setter）或**抽取第三个对象**解决

## 5. 练习题

### 练习 1：基础（必做）

为一个 `EmailService` 设计构造函数注入：
- 依赖：`smtp_host: str`、`smtp_port: int`、`username: str`、`password: str`
- 实现 `send(to, subject, body)` 方法
- 编写单元测试：传入 MockSMTP，验证 `send` 被调用

### 练习 2：进阶

阅读 `api/services/workflow_service.py`：
1. 找出 `WorkflowService.__init__` 接收哪些参数
2. 这些参数是如何被注入的？（构造函数 / 全局单例 / 装饰器）
3. 哪些参数可以在测试时替换为 Mock？

### 练习 3：挑战（选做）

设计一个简单的 DI 容器：

```python
class DIContainer:
    def register(self, interface, implementation): ...
    def resolve(self, interface): ...

# 使用
container = DIContainer()
container.register(UserRepository, SqlUserRepository)
container.register(EmailService, SmtpEmailService)
service = SomeService(
    user_repo=container.resolve(UserRepository),
    email_service=container.resolve(EmailService),
)
```

要求支持：
- 单例模式（同一接口只创建一个实例）
- 构造函数自动注入（通过类型注解自动找依赖）

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/repositories/sqlalchemy_workflow_execution_repository.py` — 构造函数注入
- `/Users/xu/code/github/dify/api/controllers/console/wraps.py` — 装饰器注入
- `/Users/xu/code/github/dify/api/extensions/ext_database.py` — 单例 + Flask context
- Martin Fowler《控制反转容器与依赖注入模式》
- `/Users/xu/code/github/dify/api/services/workflow_service.py` — 应用服务依赖管理

---

**文档版本**：v1.0
**最后更新**：2026-07-13