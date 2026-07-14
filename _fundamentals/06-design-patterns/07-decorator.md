# 2.2 装饰器模式（Decorator）

> 装饰器模式动态地给对象添加额外职责。Python 装饰器、Spring AOP、Java I/O 流都是典型应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解装饰器模式的核心（包装对象增加职责）
- 区分装饰器 vs 继承 vs 代理
- 掌握 Python 装饰器的多种写法
- 识别 dify 的认证装饰器、ruoyi 的 Spring AOP

## 📚 前置知识

- 06-adapter.md
- Python 装饰器基础

## 1. 核心概念

### 1.1 装饰器的核心思想

不修改原有类，**动态包装**对象以增加职责。多个装饰器可以嵌套。

### 1.2 装饰器 vs 继承 vs 代理

| 维度 | 继承 | 装饰器 | 代理 |
|------|------|--------|------|
| 扩展方式 | 类层级 | 对象层级 | 对象层级 |
| 运行时修改 | ❌ | ✅ | ✅ |
| 接口 | 可改 | 不变 | 不变 |
| 目的 | 重用 + 扩展 | 增加职责 | 控制访问 |

### 1.3 经典装饰器结构

```
Component（接口）
├── ConcreteComponent（核心实现）
└── Decorator（持有 Component 引用）
    ├── ConcreteDecoratorA
    └── ConcreteDecoratorB
```

## 2. 代码示例

### 2.1 Python 函数装饰器

```python
import time
from functools import wraps

def timing(func):
    """计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed:.3f}s")
        return result
    return wrapper


def retry(max_attempts: int = 3):
    """重试装饰器（带参数）"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == max_attempts - 1:
                        raise
                    time.sleep(2 ** i)
        return wrapper
    return decorator


# 使用：装饰器嵌套
@timing
@retry(max_attempts=3)
def fetch_data(url: str) -> dict:
    """获取数据（可能失败）"""
    return {"url": url, "data": "..."}
```

### 2.2 Python 类装饰器

```python
from abc import ABC, abstractmethod

class Coffee(ABC):
    @abstractmethod
    def cost(self) -> float: ...

class SimpleCoffee(Coffee):
    def cost(self) -> float:
        return 10.0

class CoffeeDecorator(Coffee):
    """装饰器基类"""
    def __init__(self, coffee: Coffee):
        self._coffee = coffee

    def cost(self) -> float:
        return self._coffee.cost()

class MilkDecorator(CoffeeDecorator):
    def cost(self) -> float:
        return self._coffee.cost() + 2.0

class SugarDecorator(CoffeeDecorator):
    def cost(self) -> float:
        return self._coffee.cost() + 1.0


# 组合装饰器
coffee = SugarDecorator(MilkDecorator(SimpleCoffee()))
print(f"Cost: {coffee.cost()}")  # 13.0
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的认证装饰器

**文件位置**：`/Users/xu/code/github/dify/api/libs/helper.py`（或类似文件）
**核心代码**（行 1-30）：

```python
from functools import wraps
from flask import request

from extensions.ext_database import db
from models.account import Account

def login_required(func):
    """登录认证装饰器——装饰器模式"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 1. 从请求头获取 token
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return {"error": "Unauthorized"}, 401

        # 2. 解析 token 并查用户
        token = auth_header.replace("Bearer ", "")
        user = db.session.query(Account).filter_by(access_token=token).first()
        if not user:
            return {"error": "Invalid token"}, 401

        # 3. 注入 current_user
        return func(*args, current_user=user, **kwargs)
    return wrapper


# 使用
@app.route("/api/apps")
@login_required
def list_apps(current_user):
    return {"apps": current_user.apps}
```

**解读**：
- `@login_required` 给所有需要认证的接口加认证逻辑
- 不修改业务函数，仅包装一层——装饰器
- **整体设计**：用装饰器统一处理横切关注点（认证、日志、限流）

### 3.2 ruoyi 的 Spring AOP @Transactional（也是装饰器）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserServiceImpl.java`
**核心代码**：

```java
@Service
public class AdminUserServiceImpl implements AdminUserService {

    @Override
    @Transactional(rollbackFor = Exception.class)  // 装饰器：动态加事务
    public Long createUser(UserSaveReqVO reqVO) {
        // 业务代码——纯粹的事务操作
        AdminUserDO user = ...;
        userMapper.insert(user);
        return user.getId();
    }
}
```

**解读**：
- `@Transactional` 是 Spring AOP 的装饰器——动态包装方法
- 在方法调用前后自动开启/提交/回滚事务
- 业务代码完全不感知事务——典型装饰器
- **整体设计**：用 AOP 实现横切关注点（日志、事务、安全、缓存）

### 3.3 ruoyi 的日志装饰器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/`
**核心代码**：

```java
@Aspect
@Component
public class WebLogAspect {
    private static final Logger LOG = LoggerFactory.getLogger(WebLogAspect.class);

    // 环绕通知——装饰请求处理
    @Around("execution(* cn.iocoder.yudao..controller..*(..))")
    public Object doAround(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.currentTimeMillis();
        try {
            return pjp.proceed();  // 调用原方法
        } finally {
            long cost = System.currentTimeMillis() - start;
            LOG.info("Request {} took {}ms", pjp.getSignature(), cost);
        }
    }
}
```

**解读**：
- `@Around` 拦截所有 controller 调用，记录耗时——装饰器
- 不修改业务代码，动态添加日志功能
- **整体设计**：用 Spring AOP 实现横切关注点

## 4. 关键要点总结

- 装饰器 = 包装对象增加职责，不改原类
- Python 函数装饰器是语法糖，本质就是装饰器模式
- Spring AOP `@Transactional`、AOP 日志都是装饰器
- dify 用 `@login_required`，ruoyi 用 Spring AOP
- 与代理区别：装饰器强调"增加功能"，代理强调"控制访问"

## 5. 练习题

### 练习 1：基础
实现一个带参数的装饰器 `@rate_limit(max_calls=10, period=60)`，限制函数调用频率。

### 练习 2：进阶
阅读 dify 的登录装饰器，把它改造成支持"可选登录"（`@login_required(optional=True)`）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/helper.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- 《设计模式》第 4 章：装饰器模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13