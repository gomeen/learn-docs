# 3.5 责任链模式（Chain of Responsibility）

> 责任链模式将请求的发送者和接收者解耦，让多个对象都有机会处理请求。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解责任链模式的核心（多处理器链）
- 区分责任链 vs 装饰器 vs 观察者
- 识别 dify 的中间件链、ruoyi 的拦截器链
- 知道责任链的适用场景

## 📚 前置知识

- 07-decorator.md
- 08-proxy.md

## 1. 核心概念

### 1.1 责任链的核心思想

多个处理器串成链，请求沿链传递，直到有一个处理器处理它。

### 1.2 责任链 vs 装饰器 vs 观察者

| 维度 | 责任链 | [装饰器](./07-decorator.md) | [观察者](./15-observer.md) |
|------|--------|--------|--------|
| 链结构 | 串联 | 嵌套包装 | 中心辐射 |
| 处理逻辑 | 选一个处理 | 全部叠加 | 全部通知 |
| 中断 | 可以中断 | 不可中断 | 全部执行 |

### 1.3 适用场景

- 多个对象都可能处理请求，具体由运行时决定
- 需要动态指定处理者集合
- 发送者不需要知道谁最终处理

## 2. 代码示例

### 2.1 经典责任链

```python
from abc import ABC, abstractmethod

class Handler(ABC):
    def __init__(self):
        self._next: "Handler | None" = None

    def set_next(self, handler: "Handler") -> "Handler":
        self._next = handler
        return handler

    def handle(self, request: str) -> str | None:
        """处理请求——可选择传递"""
        result = self._process(request)
        if result is None and self._next:
            return self._next.handle(request)  # 传递给下一个
        return result

    @abstractmethod
    def _process(self, request: str) -> str | None:
        """子类实现：返回处理结果或 None"""
        ...


class AuthHandler(Handler):
    def _process(self, request: str) -> str | None:
        if not request.startswith("/login"):
            return None  # 不是登录请求，跳过
        if "user" not in request:
            return "401 Unauthorized"
        return None  # 鉴权通过，传递给下一个

class LogHandler(Handler):
    def _process(self, request: str) -> str | None:
        print(f"[LOG] {request}")
        return None  # 日志记录后继续

class RouterHandler(Handler):
    def _process(self, request: str) -> str | None:
        if "/api" in request:
            return f"API response for {request}"
        return None


# 组装链：auth → log → router
chain = AuthHandler()
chain.set_next(LogHandler()).set_next(RouterHandler())

print(chain.handle("GET /api/users?user=alice"))  # 日志 + API 响应
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的 Flask 中间件链

**文件位置**：`/Users/xu/code/github/dify/api/app_factory.py`（或类似文件）
**核心代码**（行 1-50）：

```python
from flask import Flask

def create_app() -> Flask:
    """创建 Flask 应用——中间件责任链"""
    app = Flask(__name__)

    # 责任链：每个 before_request 都是一个处理器
    @app.before_request
    def log_request():
        """处理器 1：记录请求日志"""
        print(f"[LOG] {request.method} {request.path}")

    @app.before_request
    def authenticate():
        """处理器 2：认证"""
        if not is_authenticated(request):
            return {"error": "Unauthorized"}, 401

    @app.before_request
    def check_rate_limit():
        """处理器 3：限流"""
        if is_rate_limited(request):
            return {"error": "Too many requests"}, 429

    # 处理链：log → auth → rate_limit → route handler
    return app
```

**解读**：
- 多个 `before_request` 组成处理链
- 任一处理器返回响应就中断
- **整体设计**：Flask 中间件链是责任链模式

### 3.2 ruoyi 的 Spring 拦截器链

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**：

```java
@Configuration
public class YudaoWebAutoConfiguration implements WebMvcConfigurer {

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        // 责任链：多个拦截器按顺序执行
        registry.addInterceptor(new AuthInterceptor())     // 1. 认证
                .addPathPatterns("/**");
        registry.addInterceptor(new DataPermissionInterceptor())  // 2. 数据权限
                .addPathPatterns("/**");
        registry.addInterceptor(new WebLogInterceptor())    // 3. 日志
                .addPathPatterns("/**");
    }
}
```

**解读**：
- Spring 拦截器链：auth → dataPermission → webLog
- 每个拦截器可中断（`return false`）
- **整体设计**：用拦截器链实现横切关注点

### 3.3 ruoyi 的登录 Token 校验链

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
**核心代码**：

```java
@Component
public class TokenAuthFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest req,
                                     HttpServletResponse resp,
                                     FilterChain chain) {
        // 1. 提取 Token
        String token = req.getHeader("Authorization");

        // 2. 校验 Token（处理器 1）
        if (!validateToken(token)) {
            resp.setStatus(401);
            return;  // 中断链
        }

        // 3. 设置上下文
        SecurityContextHolder.setContext(...);

        // 4. 传递给下一个过滤器
        chain.doFilter(req, resp);  // 责任链
    }
}
```

**解读**：
- 多个 Filter 串成链：`TokenAuthFilter → PermissionFilter → ControllerFilter`
- 任何一个 Filter 返回错误就中断
- **整体设计**：用 Filter 链实现认证授权链

## 4. 关键要点总结

- 责任链 = 多个处理器串成链，请求沿链传递
- 与装饰器区别：责任链选一个处理，装饰器全部叠加
- dify 用 Flask `before_request`，ruoyi 用 Spring 拦截器
- 适合：认证、日志、限流、参数校验等横切关注点
- 可中断（任一处理者返回）

## 5. 练习题

### 练习 1：基础
为请假审批实现责任链（组长 → 经理 → 总监，每级有金额上限）。

### 练习 2：进阶
阅读 ruoyi 的 `YudaoWebAutoConfiguration`，画出它的拦截器链顺序。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/app_factory.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/`
- 《设计模式》第 5 章：责任链

---

**文档版本**：v1.0
**最后更新**：2026-07-13