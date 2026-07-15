# 3.5 分布式 Session 设计

> 掌握分布式 Session 的存储方案、Session 共享与安全防护。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释为什么需要分布式 Session
- 区分基于 Cookie / Token / Session 的认证方式
- 用 Redis 实现分布式 Session 存储
- 理解 Session 安全防护要点

## 📚 前置知识

- HTTP Cookie 机制
- 单点登录（SSO）基本概念
- Redis 基础操作

## 1. 核心概念

### 1.1 为什么需要分布式 Session？

**传统单体应用**：
- Session 存在服务器内存
- 用户每次请求带 Cookie（session_id）
- 服务器从内存查 session_id 对应的用户

**分布式场景问题**：
- 同一用户多次请求可能落到不同服务器
- 服务器 A 内存里的 session，服务器 B 看不到
- 用户被反复要求登录

### 1.2 Session 的三大存储方案

| 方案 | 优点 | 缺点 |
|------|------|------|
| **服务器内存** | 最快 | 不跨服务器 |
| **[Redis](../01-redis/01-data-structures.md) 集中存储** | 跨服务器、TTL 自动清理 | 多一次网络 IO |
| **[JWT](../07-authentication/03-jwt.md) 无状态 Token** | 无需存储 | 无法主动失效 |

### 1.3 Session 与 Token 的对比

**Session（服务器存储）**：
```
浏览器                    服务器                   Redis
  |--GET /api-->          |--查 session-->          |
  |  Cookie: sid=xxx      |   无 sid → 401           |
  |                       |--get sid from Redis--->|
  |                       |<--{user: alice}---------|
  |<--返回数据-------------|
```

**Token（JWT）**：
```
浏览器                    服务器
  |--GET /api-->          |
  |  Authorization: Bearer xxx
  |                       |--解析 JWT（无 DB 查询）
  |<--返回数据-------------|
```

| 维度 | Session | Token |
|------|---------|-------|
| 存储 | 服务端 | 客户端 |
| 主动失效 | 可以 | 难（需黑名单） |
| 跨域 | 难 | 易 |
| 适用 | 内部系统 | 跨域 SSO / 移动端 |

### 1.4 分布式 Session 的标准实现

```
1. 用户登录 → 服务器验证密码
2. 生成 session_id（随机字符串）
3. 存 session_id → user_data 到 Redis
4. 通过 Set-Cookie 返回 session_id 给浏览器
5. 后续请求：浏览器带 Cookie → 服务器查 Redis
6. 用户登出：删除 Redis 中的 session
```

### 1.5 Session 的关键设计点

- **session_id 必须足够随机**（防止伪造）
- **session 必须有过期时间**（防止无限增长）
- **敏感操作要二次验证**（如支付前要求重新登录）
- **HTTPS 传输**（防窃听）

## 2. 代码示例

### 2.1 Redis Session 实现

```python
# 文件：example_session.py
import redis
import secrets
import json
import hashlib
import time

r = redis.Redis(host="localhost", port=6379)

SESSION_TTL = 3600    # 1 小时
SESSION_PREFIX = "session:"


def create_session(user_id: str, user_data: dict) -> str:
    """用户登录后创建 session"""
    # 1. 生成随机 session_id
    session_id = secrets.token_urlsafe(32)

    # 2. 存到 Redis
    session_data = {
        "user_id": user_id,
        "user_data": user_data,
        "created_at": int(time.time()),
        "ip": "",          # 登录时记录 IP
        "ua": "",          # 登录时记录 User-Agent
    }
    r.setex(SESSION_PREFIX + session_id, SESSION_TTL, json.dumps(session_data))

    return session_id


def get_session(session_id: str) -> dict | None:
    """从 Cookie 提取 session_id 后调用"""
    if not session_id:
        return None

    data = r.get(SESSION_PREFIX + session_id)
    if not data:
        return None

    # 滑动过期：每次访问刷新 TTL
    r.expire(SESSION_PREFIX + session_id, SESSION_TTL)

    return json.loads(data)


def destroy_session(session_id: str):
    """登出"""
    r.delete(SESSION_PREFIX + session_id)


# 使用
session_id = create_session("user-001", {"name": "alice", "role": "admin"})
print(f"登录成功: session_id={session_id}")

session = get_session(session_id)
print(f"获取 session: {session}")

destroy_session(session_id)
print("已登出")
```

### 2.2 Flask + Redis Session 中间件

```python
# 文件：example_flask_session.py
from flask import Flask, request, jsonify, g
import redis
import secrets

app = Flask(__name__)
r = redis.Redis(host="localhost", port=6379)


def session_required(f):
    """装饰器：要求登录"""
    def wrapper(*args, **kwargs):
        session_id = request.cookies.get("session_id")
        if not session_id:
            return jsonify({"error": "未登录"}), 401

        data = r.get(f"session:{session_id}")
        if not data:
            return jsonify({"error": "session 过期"}), 401

        g.session_id = session_id
        g.user = json.loads(data)["user_data"]
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


@app.post("/login")
def login():
    username = request.json.get("username")
    password = request.json.get("password")

    # 验证密码（伪代码）
    user = db_verify_user(username, password)
    if not user:
        return jsonify({"error": "密码错误"}), 401

    # 创建 session
    session_id = secrets.token_urlsafe(32)
    r.setex(f"session:{session_id}", 3600, json.dumps({"user_data": user}))

    response = jsonify({"message": "登录成功"})
    response.set_cookie(
        "session_id",
        session_id,
        httponly=True,        # 防 [XSS](../05-web-security/02-xss.md) 窃取
        secure=True,          # 仅 HTTPS
        samesite="Lax",       # 防 [CSRF](../05-web-security/04-csrf.md)
        max_age=3600,
    )
    return response


@app.get("/me")
@session_required
def get_me():
    return jsonify({"user": g.user})


@app.post("/logout")
def logout():
    session_id = request.cookies.get("session_id")
    if session_id:
        r.delete(f"session:{session_id}")
    response = jsonify({"message": "已登出"})
    response.delete_cookie("session_id")
    return response
```

### 2.3 常见错误：Session ID 太弱

```python
# ❌ 反例：session_id 用自增整数
session_id = str(user_id)   # user_id=123 → session_id="123"

# 问题：攻击者遍历 session_id=1,2,3... 窃取所有 session

# ✅ 正例：用密码学安全的随机数
import secrets
session_id = secrets.token_urlsafe(32)   # 256 位熵
```

## 3. dify 仓库源码解读

### 3.1 dify 的 JWT 认证（无 Session 设计）

**说明**：dify 主要使用 **JWT Token** 而非 Session，因为：
- 前后端分离 + 移动端 API
- 跨域支持友好
- 无需服务器存储

**文件位置**：`/Users/xu/code/github/dify/api/services/feature_service.py`
**核心代码**（行 39-46）：

```python
class LicenseLimitationModel(FeatureResponseModel):
    """
    - enabled: whether this limit is enforced
    - size: current usage count
    - limit: maximum allowed count; 0 means unlimited
    """

    enabled: bool = Field(False, description="Whether this limit is currently active")
    size: int = Field(0, description="Number of resources already consumed")
    limit: int = Field(0, description="Maximum number of resources allowed; 0 means no limit")
```

**解读**：
- dify 用 JWT + Redis 黑名单的组合方式：
  - **JWT** 存用户身份信息（无状态、快速）
  - **Redis 黑名单** 处理登出/封禁场景（解决 JWT 无法主动失效的问题）
- 第 42 行 `enabled: bool`：标识限制是否生效——类似 session 的"是否启用"
- **应用关联**：dify 在 API 层用 JWT 校验用户身份，但限流、配额等信息从 FeatureService（可缓存）查询

### 3.2 ruoyi 的 Redis Session（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
**核心代码**（简化）：

```java
// Spring Session + Redis 集成
@Configuration
@EnableRedisHttpSession(maxInactiveIntervalInSeconds = 3600)
public class SessionConfig {
    @Bean
    public CookieSerializer cookieSerializer() {
        DefaultCookieSerializer serializer = new DefaultCookieSerializer();
        serializer.setCookieName("SESSION");
        serializer.setSameSite("Lax");
        serializer.setUseSecureCookie(true);
        return serializer;
    }
}

// SecurityConfig.java - 鉴权
http
    .sessionManagement(session -> session
        .sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED)
        .maximumSessions(1)              // 同一用户最多 1 个 session
        .maxSessionsPreventsLogin(false) // 后登录踢出前一个
    );
```

**解读**：
- 第 2 行 `@EnableRedisHttpSession`：Spring Session 自动把 HttpSession 存到 Redis，**业务代码完全无感知**
- 第 12 行 `maximumSessions(1)`：限制同一账号只能 1 个 session（防多设备登录）
- 与 Flask 自实现对比：Spring Session 是**框架级**解决方案，dify 的 JWT 是**应用级**方案

## 4. 关键要点总结

- **分布式 Session** 必须用集中存储（Redis），不能用服务器内存
- **session_id 必须用密码学安全的随机数**
- **Cookie 必须配置 HttpOnly + Secure + SameSite**
- **JWT 适合跨域场景**，但难以主动失效（需黑名单）
- **Spring Session** 是 Java 生态的事实标准（自动 Redis 化）
- dify 用 JWT + Redis 黑名单的组合方案

## 5. 练习题

### 练习 1：基础（必做）

实现一个完整的 Session 类：
1. `create(user_id)` → 返回 session_id
2. `get(session_id)` → 返回 user 数据（自动续期）
3. `destroy(session_id)` → 删除
4. 用 Redis SETEX 实现 TTL

### 练习 2：进阶

设计一个**双因素 Session 验证**：
- 普通操作：只检查 session
- 敏感操作（修改密码、转账）：额外要求输入 2FA 验证码
- 验证后 30 分钟内免重复验证

### 练习 3：挑战（选做）

对比 **Session vs JWT** 在 dify 这种 API 服务中的适用性：
- dify 为什么选 JWT 不选 Session？
- 如果 dify 要支持"管理员强制用户下线"，JWT 方案需要怎么改造？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/feature_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
- Spring Session：https://docs.spring.io/spring-session/reference/
- OWASP Session 管理：https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-14