# 17 安全测试：OWASP ZAP / Bandit

> 理解安全测试的目标和工具栈，能用 Bandit 检测 Python 代码安全问题，用 OWASP ZAP 做 Web 渗透测试。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 OWASP Top 10 等安全测试框架
- 掌握 Bandit 静态安全扫描的用法
- 知道 OWASP ZAP 渗透测试的基本流程
- 应用：能在 dify 中运行 Bandit 并修复发现的安全问题

## 📚 前置知识

- Web 安全基础（OWASP 概览详见 [OWASP Top 10](../../_common/05-web-security/01-owasp-top10.md)；SQL 注入 / XSS / CSRF 详见同目录专题）
- Python 类型提示与代码分析

## 1. 核心概念

### 1.1 安全测试的两大类

**静态应用安全测试（SAST, Static AST）**：
- 不运行代码，直接扫描源码
- 速度快，能发现常见漏洞
- 工具：Bandit（Python）、Semgrep、SonarQube

**动态应用安全测试（DAST, Dynamic AST）**：
- 运行真实应用，模拟攻击
- 发现运行时漏洞（如 XSS、注入）
- 工具：OWASP ZAP、Burp Suite

### 1.2 OWASP Top 10（2021 版）

dify 防御的主要威胁类别：

| 编号 | 威胁 | dify 关注点 |
|------|------|------------|
| A01 | Broken Access Control | RBAC（详见 [RBAC](../../_common/08-authorization/01-rbac.md)）、API 鉴权 |
| A02 | Cryptographic Failures | SECRET_KEY、密码哈希 |
| A03 | Injection | SQLAlchemy 防注入（详见 [SQL 注入](../../_common/05-web-security/03-sql-injection.md)）、Prompt 注入 |
| A04 | Insecure Design | SSRF 防护（dify 的 `SSRFProxy`，详见 [SSRF](../../_common/05-web-security/06-ssrf.md)） |
| A05 | Security Misconfiguration | CORS（详见 [CORS](../../_common/05-web-security/05-cors.md)）、debug 模式 |
| A06 | Vulnerable Components | 依赖扫描 |
| A07 | Authentication Failures | JWT（详见 [JWT](../../_common/07-authentication/03-jwt.md)）、登录流程 |
| A08 | Data Integrity Failures | Workflow 持久化 |
| A09 | Logging Failures | 审计日志 |
| A10 | SSRF | **dify 重点**（LLM 调用外部 API） |

### 1.3 dify 的安全工具

| 工具 | 用途 | 在 dify 中的位置 |
|------|------|------------------|
| **Bandit** | Python 静态扫描 | 可作为 pre-commit hook（详见 [Pre-commit Hook](./21-pre-commit.md)） |
| **Ruff S 规则** | 内置安全 lint | `api/.ruff.toml` |
| **Trivy** | 容器镜像扫描 | CI 阶段（详见 [CI/CD 概念](../../_common/11-cicd/01-concepts.md)） |
| **Safety** | Python 依赖漏洞 | 未来可集成 |

## 2. 代码示例

### 2.1 Bandit 基础扫描

```bash
# 安装 Bandit
$ pip install bandit

# 扫描整个目录
$ bandit -r api/

# 输出示例
Run started: 2026-07-13 12:00:00

Test results:
>> Issue: [B105:blacklist] Use of hardcoded password
   Severity: High   Confidence: Medium
   Location: api/services/auth.py:42
   More Info: https://bandit.readthedocs.io/en/latest/blacklists/blacklist_calls.html
42    password = "admin123"

--------------------------------------------------
>> Issue: [B602:subprocess_popen_with_shell_equals_true] subprocess call with shell=True
   Severity: High   Confidence: High
   Location: api/utils/cmd.py:15
15    subprocess.Popen(cmd, shell=True)
```

### 2.2 Bandit 配置

```yaml
# 文件：.bandit
skips:
  - B101  # assert_used（测试代码中常用）
  - B601  # paramiko_calls（dify 不直接用 paramiko）

exclude_dirs:
  - api/tests
  - api/migrations
```

```bash
# 使用配置文件扫描
$ bandit -r api/ -c .bandit
```

### 2.3 OWASP ZAP 基础扫描

```bash
# 启动 ZAP daemon
$ docker run -u zap -p 8080:8080 owasp/zap2docker-stable zap.sh -daemon -port 8080

# 用 Python 客户端扫描
$ python -c "
from zapv2 import ZAPv2
zap = ZAPv2(apikey='', proxies={'http': 'http://localhost:8080', 'https': 'http://localhost:8080'})

# 1. spider 爬取
zap.spider.scan('http://localhost:3000')

# 2. 主动扫描
zap.ascan.scan('http://localhost:3000')

# 3. 获取报告
print(zap.core.alerts())
"
```

### 2.4 dify ruff.toml 中的安全规则

dify 的 `api/.ruff.toml` 启用了 Ruff 内置的安全规则：

```toml
[lint]
select = [
    ...
    "S102",  # exec-builtin, disallow use of `exec`
    "S307",  # suspicious-eval-usage, disallow use of `eval` and `ast.literal_eval`
    "S301",  # suspicious-pickle-usage, disallow use of `pickle` and its wrappers.
    "S302",  # suspicious-marshal-usage, disallow use of `marshal` module
    "S311",  # suspicious-non-cryptographic-random-usage,
    "TID",   # flake8-tidy-imports
]
```

**解读**：
- `S102`/`S307`/`S301`/`S302`/`S311` 是 Ruff 内置的 Bandit 兼容规则
- dify 选择用 Ruff 代替独立 Bandit（统一工具链）
- 通过 ruff.toml 集中配置安全规则

## 3. dify 仓库源码解读

### 3.1 dify 的 Ruff 安全规则配置

**文件位置**：`/Users/xu/code/github/dify/api/.ruff.toml`
**核心代码**（行 49-58）：

```toml
    # security related linting rules
    # RCE proctection (sort of)
    "S102", # exec-builtin, disallow use of `exec`
    "S307", # suspicious-eval-usage, disallow use of `eval` and `ast.literal_eval`
    "S301", # suspicious-pickle-usage, disallow use of `pickle` and its wrappers.
    "S302", # suspicious-marshal-usage, disallow use of `marshal` module
    "S311", # suspicious-non-cryptographic-random-usage,
    "TID",   # flake8-tidy-imports

```

**解读**：
- 第 51 行：`S102 exec-builtin` —— 禁止使用 `exec()`（避免代码执行漏洞）
- 第 52 行：`S307 eval-usage` —— 禁止使用 `eval()`（避免代码注入）
- 第 53 行：`S301 pickle-usage` —— 禁止 `pickle.loads`（反序列化攻击）
- 第 54 行：`S302 marshal-usage` —— 禁止 `marshal`（不安全的序列化）
- 第 55 行：`S311 random` —— 禁止非密码学 random（避免用 `random` 生成 token）
- **设计意图**：dify 通过 Ruff 内置规则强制安全编码，等同于一个轻量级 Bandit

### 3.2 dify 的 SSRF 防护（OWASP A10）

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（async 用法详见 [async/await 与 asyncio](../01-fundamentals/12-async-asyncio.md)）：

```python
class SSRFProxy:
    """SSRF 安全的异步 HTTP 客户端。

    通过代理转发外部请求，避免服务端请求伪造攻击。
    """

    async def get(self, url: str, **kwargs) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, **kwargs) as response:
                response.raise_for_status()
                return await response.text()
```

**解读**：
- dify 把所有外部 HTTP 请求通过 `SSRFProxy` 转发
- SSRF（Server-Side Request Forgery）是 LLM 应用的**典型风险**：用户输入 URL，服务器请求它，可能访问内网
- `SSRFProxy` 通过白名单/黑名单 IP 段，阻止对 `127.0.0.1`、`169.254.169.254`（AWS metadata）等敏感地址的访问

### 3.3 dify 的 `try-except-pass` 禁止

**文件位置**：`/Users/xu/code/github/dify/api/.ruff.toml`
**核心代码**（行 47-48）：

```toml
    "S110",    # disallow the try-except-pass pattern.

    # security related linting rules
    # RCE proctection (sort of)
```

**解读**：
- `S110 try-except-pass` —— 禁止"捕获异常后什么都不做"
- 这种模式会**吞掉错误信息**，导致安全事件无法被日志发现
- dify 在测试代码中**允许**（通过 per-file-ignores），但生产代码强制开启

## 4. 关键要点总结

- 安全测试分 SAST（静态）和 DAST（动态），互相补充
- OWASP Top 10 是 Web 安全的事实标准
- Bandit 是 Python 静态安全扫描的主流工具
- dify 通过 **Ruff 内置安全规则**（S102、S307、S301 等）替代独立 Bandit
- dify 的 SSRFProxy 是 LLM 应用防护 SSRF 的关键基础设施
- `try-except-pass` 被显式禁止，避免吞错

## 5. 练习题

### 练习 1：基础（必做）

在 `api/` 目录下运行 `uv run --project api --dev ruff check --select S api/`，查看 S 系列安全规则的命中情况，找出所有 `S110`（try-except-pass）的位置。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`（如果存在），理解 dify 如何实现 SSRF 防护，写一段总结：SSRF 攻击是什么、dify 如何防御。

### 练习 3：挑战（选做）

为 dify 增加一个 pre-commit hook，运行 `ruff check --select S api/`（安全规则扫描），并把扫描结果写入 `pre-commit-config.yaml`。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/.ruff.toml`（Ruff 安全规则）
- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`（SSRF 防护）
- OWASP Top 10：https://owasp.org/Top10/
- Bandit 文档：https://bandit.readthedocs.io/
- OWASP ZAP 文档：https://www.zaproxy.org/

---

**文档版本**：v1.0
**最后更新**：2026-07-13