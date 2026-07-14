# 5.1 OWASP Top 10 漏洞概览

> 了解 Web 应用最常见的十大安全风险，建立安全防护的整体框架。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 OWASP Top 10 (2021) 十大安全风险的分类与含义
- 掌握每类漏洞的核心攻击原理与典型场景
- 能在 dify/ruoyi 等真实项目中识别这些风险的防护位置
- 形成"威胁建模"的基本思路，写代码时主动规避常见漏洞

## 📚 前置知识

- HTTP 协议基础（请求/响应/方法/状态码）
- Web 三层架构（前端 / 后端 / 数据库）
- 任意一门后端语言（Python 或 Java）

## 1. 核心概念

### 1.1 什么是 OWASP？

OWASP（Open Worldwide Application Security Project）是全球性的非营利组织，定期发布 **OWASP Top 10** —— Web 应用最常见、最危险的十大安全风险清单。

| 版本 | 年份 | 主要变化 |
|------|------|---------|
| 2017 | — | 引入 XXE、SSRF |
| **2021** | 当前主流 | 重组为 10 类，新增 Insecure Design 等 |
| 2025 (草案) | — | 关注供应链、API 安全 |

### 1.2 OWASP Top 10 (2021) 完整列表

| # | 类别 | 中文名 | 一句话概括 |
|---|------|--------|-----------|
| A01 | Broken Access Control | 权限控制失效 | 用户能访问/操作本不该访问的资源 |
| A02 | Cryptographic Failures | 加密失效 | 明文存密码、弱加密、不安全的传输 |
| A03 | Injection | 注入攻击 | SQL / NoSQL / OS / LDAP 注入 |
| A04 | Insecure Design | 不安全设计 | 设计阶段缺乏威胁建模 |
| A05 | Security Misconfiguration | 安全配置错误 | 默认密码、调试模式开启 |
| A06 | Vulnerable Components | 易受攻击组件 | 使用了有 CVE 的第三方库 |
| A07 | Authentication Failures | 认证失效 | 弱密码、会话固定、凭证填充 |
| A08 | Software & Data Integrity | 软件与数据完整性 | 不安全的反序列化、CI/CD 投毒 |
| A09 | Logging & Monitoring Failures | 日志与监控失效 | 无法检测攻击、无法溯源 |
| A10 | SSRF | 服务端请求伪造 | 服务端被迫访问内网资源 |

### 1.3 真实案例

- **Equifax 数据泄露 (2017)**：A06，使用了未打补丁的 Apache Struts，导致 1.47 亿用户信息泄露
- **SolarWinds 供应链攻击 (2020)**：A08，攻击者污染了 CI/CD 流水线
- **Capital One 数据泄露 (2019)**：A10，SSRF 攻击访问 AWS 元数据接口，窃取 1 亿条记录

### 1.4 dify 和 ruoyi 的安全设计对比

| OWASP 类别 | dify 防护位置 | ruoyi 防护位置 |
|----------|--------------|----------------|
| A01 权限失效 | `controllers/common/wraps.py` RBAC 装饰器 | `@PreAuthorize` + 数据权限拦截器 |
| A02 加密失效 | `libs/password.py` PBKDF2 | BCrypt + 自定义 Encrypt 注解 |
| A03 注入 | SQLAlchemy ORM + 参数化查询 | MyBatis `#{}` 占位符 + XSS 过滤 |
| A04 不安全设计 | 中间件架构 + Celery 任务隔离 | Spring Security Filter Chain |
| A05 配置错误 | 环境变量 + Secrets 管理 | 配置中心 + Nacos |
| A07 认证失效 | Flask-Login + CSRF Token | TokenAuthenticationFilter |
| A10 SSRF | `core/helper/ssrf_proxy.py` | 自定义 Squid 代理 + 黑名单 |

## 2. 代码示例

### 2.1 一个"百毒俱全"的反面教材

```python
# 文件：vulnerable_app.py
# ⚠️ 这是一个**故意写错**的示例，用于展示 OWASP Top 10 的常见问题
from flask import Flask, request

app = Flask(__name__)

# A05 默认配置：debug=True 会泄露栈跟踪
app.config["DEBUG"] = True  # ❌ 生产环境绝对不能开

# A07 弱认证：硬编码管理员密码
ADMIN_PASSWORD = "admin123"  # ❌ 字典攻击 1 秒破解

@app.route("/login")
def login():
    username = request.args.get("username")
    password = request.args.get("password")

    # A03 SQL 注入：直接拼接 SQL
    query = f"SELECT * FROM users WHERE name='{username}' AND pwd='{password}'"  # ❌
    # 攻击：username=admin'--   →  绕过密码验证

    # A02 明文密码：未哈希比较
    if password == ADMIN_PASSWORD:
        return "logged in"

    # A09 日志缺失：登录失败不记录
    return "failed", 401

@app.route("/file")
def read_file():
    # A03 OS 命令注入：用户控制文件名
    filename = request.args.get("name")
    return open(f"/var/data/{filename}").read()  # ❌ 路径遍历：?name=../../etc/passwd
```

### 2.2 修正后的版本

```python
# 文件：secure_app.py
# ✅ 修复版：体现 OWASP Top 10 的基本防护原则
import hashlib
import hmac
import logging
import os
import secrets
from functools import wraps

from flask import Flask, request, abort
from sqlalchemy import text
from sqlalchemy.orm import Session

app = Flask(__name__)

# ✅ A05：debug 由环境变量控制
app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "0") == "1"

# ✅ A02：密码使用 PBKDF2 哈希存储
def hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)

logger = logging.getLogger("secure-app")

def require_api_key(f):
    """✅ A07：API Key 校验，避免硬编码密码"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(key, os.environ["API_KEY"]):
            abort(401)
        return f(*args, **kwargs)
    return wrapper

@app.route("/login")
def login():
    username = request.args.get("username", "")
    password = request.args.get("password", "")

    # ✅ A03：使用 SQLAlchemy 参数化查询
    with Session(engine) as session:
        row = session.execute(
            text("SELECT pwd_hash, salt FROM users WHERE name = :name"),
            {"name": username}
        ).first()
        if row and hash_password(password, row.salt) == row.pwd_hash:
            return "logged in"

    # ✅ A09：登录失败必须记录日志
    logger.warning("login failed for user=%s ip=%s", username, request.remote_addr)
    return "failed", 401

# ✅ A01：权限装饰器
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.headers.get("X-Admin-Token"):
            abort(403)
        return f(*args, **kwargs)
    return wrapper

@app.route("/admin/users")
@require_api_key
@admin_required
def list_users():
    return "user list"
```

**说明**：
- A02：密码用 PBKDF2 加盐哈希存储
- A03：所有 SQL 用参数化查询，禁止字符串拼接
- A05：debug 模式由环境变量控制，生产永远关闭
- A07：API Key 用 `hmac.compare_digest` 常数时间比较
- A09：登录失败必须记录日志
- A01：敏感接口用装饰器做权限校验

## 3. dify 仓库源码解读

### 3.1 dify 的认证与权限中间层

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/wraps.py`
**核心代码**（行 113-125）：

```python
def account_initialization_required[R](view: Callable[..., R]) -> Callable[..., R]:
    @wraps(view)
    def decorated(*args: Any, **kwargs: Any) -> R:
        # The overloads keep Resource methods method-aware for pyrefly while
        # preserving support for plain functions used in tests and utilities.
        # check account initialization
        current_user, _ = current_account_with_tenant()
        if current_user.status == AccountStatus.UNINITIALIZED:
            raise AccountNotInitializedError()

        return view(*args, **kwargs)

    return decorated
```

**解读**：
- 第 119 行：调用 `current_account_with_tenant()` 获取当前登录用户与租户（封装了 Flask-Login 与 CSRF 校验）
- 第 120 行：**A01 防护**——检查用户状态，未初始化的账户拒绝访问
- 第 121 行：抛自定义异常，由全局异常处理器返回 401/403
- **整体设计意图**：所有 console 接口通过装饰器链统一做"认证 + 初始化 + 租户 + RBAC"四层校验

### 3.2 ruoyi 的 Token 过滤器（认证失效 A07 的标准答案）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 42-69）：

```java
@Override
@SuppressWarnings("NullableProblems")
protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
        throws ServletException, IOException {
    String token = SecurityFrameworkUtils.obtainAuthorization(request,
            securityProperties.getTokenHeader(), securityProperties.getTokenParameter());
    if (StrUtil.isNotEmpty(token)) {
        Integer userType = WebFrameworkUtils.getLoginUserType(request);
        try {
            // 1.1 基于 token 构建登录用户
            LoginUser loginUser = buildLoginUserByToken(token, userType);
            // 1.2 模拟 Login 功能，方便日常开发调试
            if (loginUser == null) {
                loginUser = mockLoginUser(request, token, userType);
            }

            // 2. 设置当前用户
            if (loginUser != null) {
                SecurityFrameworkUtils.setLoginUser(loginUser, request);
            }
        } catch (Throwable ex) {
            CommonResult<?> result = globalExceptionHandler.allExceptionHandler(request, ex);
            ServletUtils.writeJSON(response, result);
            return;
        }
    }

    // 继续过滤链
    chain.doFilter(request, response);
}
```

**解读**：
- 第 44 行：从 Header 或 Query 参数中获取 Token（**A07 防护**——Token 不放 URL 中）
- 第 50 行：调用 OAuth2 服务校验 Token 有效性
- 第 52-54 行：mock 登录仅在开发环境开启（**A05 防护**——避免线上留后门）
- 第 60-63 行：异常被全局处理器转成 JSON 返回，避免栈跟踪泄露
- **整体设计意图**：用 Filter 统一处理 Token 校验，把"会话有效性"和"业务逻辑"解耦

## 4. 关键要点总结

- OWASP Top 10 是 Web 安全的"行业地图"，但它不是清单——它是思考框架
- A01（权限失效）和 A03（注入）历年稳居前两名，必须重点防护
- dify 用装饰器链 + SQLAlchemy ORM 防护 A01/A03
- ruoyi 用 Spring Security Filter Chain + MyBatis `#{}` 防护 A01/A03
- **安全是设计出来的，不是补丁堆出来的** —— 写代码时多问一句"如果用户输入是恶意的，会怎样？"

## 5. 练习题

### 练习 1：基础（必做）

列出你最近写的一个接口，对照 OWASP Top 10 (2021) 逐项检查，指出至少 3 个潜在风险点。

**参考答案**：见 `solutions/01-owasp-checklist.md`

### 练习 2：进阶

阅读 dify 的 `controllers/console/wraps.py`，画出 `login_required` → `account_initialization_required` → `rbac_permission_required` 装饰器链的执行流程。

### 练习 3：挑战（选做）

对比 dify 的 `controllers/console/wraps.py` 和 ruoyi 的 `YudaoWebSecurityConfigurerAdapter.java`，写一份两者的安全机制对比表（按 OWASP Top 10 分类）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/wraps.py`
- `/Users/xu/code/github/dify/api/controllers/common/wraps.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
- OWASP Top 10 官网：https://owasp.org/Top10/

---

**文档版本**：v1.0
**最后更新**：2026-07-13