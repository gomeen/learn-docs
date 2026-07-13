# 10.4.1 Sentry 错误追踪集成

> 用 Sentry 集中收集 dify 前后端异常、定位代码错误、监控应用健康度。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Sentry 的工作原理和价值
- 掌握 Sentry 与 Flask / Celery 的集成方法
- 能看懂 dify `extensions/ext_sentry.py` 的配置
- 知道 Sentry 在 dify 中的位置和作用

## 📚 前置知识

- 10.1.5 dify 日志体系（`05-logging-in-dify.md`）
- 04-cache-and-queue Celery 任务队列
- Python 异常处理

## 1. 核心概念

### 1.1 Sentry 是什么？

**Sentry** 是应用错误追踪平台，专注三件事：
1. **捕获异常**：自动收集前后端的运行时错误
2. **上下文聚合**：把同一异常的多次发生合并，附带完整堆栈和环境信息
3. **告警与分配**：异常发生时通知相关人员

### 1.2 Sentry vs 日志系统

| 维度 | 日志系统（ELK / Loki） | Sentry |
|------|------------------------|--------|
| 数据量 | 大（全量日志） | 小（只关注异常） |
| 聚合 | 按时间/级别聚合 | 按异常类型聚合（自动去重） |
| 上下文 | 自由格式 | 标准化（user / browser / OS） |
| 告警 | 需要自己配置 | 内置告警规则 |
| 用途 | 全链路分析 | 错误定位与修复追踪 |

**最佳实践**：两者并存——日志用于排查流程，Sentry 用于追踪 bug。

### 1.3 Sentry 的核心概念

| 概念 | 含义 |
|------|------|
| **Event** | 一次异常发生 |
| **Issue** | 同类型异常的聚合（自动去重） |
| **Stack Trace** | 异常堆栈，含源码位置 |
| **Breadcrumb** | 异常前的操作轨迹（如日志） |
| **Release** | 代码版本关联，识别新引入的 bug |
| **Environment** | 环境（dev / staging / prod） |

### 1.4 Sentry 的 Python SDK

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn="https://...@sentry.io/123",
    integrations=[FlaskIntegration(), CeleryIntegration()],
    traces_sample_rate=0.1,         # 10% 性能追踪采样
    profiles_sample_rate=0.1,       # 10% profiling
    environment="production",
    release="myapp@1.0.0",
)
```

**关键参数**：
- `dsn`：Sentry 项目地址
- `integrations`：自动捕获特定框架的异常
- `traces_sample_rate`：性能追踪采样率（性能 vs 成本）
- `before_send`：钩子函数，过滤不想上报的异常

## 2. 代码示例

### 2.1 最小 Sentry 集成

```python
import sentry_sdk

sentry_sdk.init(dsn="https://...@sentry.io/123")

# 自动捕获异常
def divide(a, b):
    return a / b  # ZeroDivisionError 自动上报

divide(1, 0)
```

### 2.2 自定义 before_send 过滤

```python
import sentry_sdk

def before_send(event, hint):
    # 过滤某些异常类型
    if "exc_info" in hint:
        exc_type, exc_value, _ = hint["exc_info"]
        # 不上报 ValueError
        if exc_type is ValueError:
            return None
    return event

sentry_sdk.init(
    dsn="...",
    before_send=before_send,
)
```

### 2.3 手动捕获异常 + 用户上下文

```python
import sentry_sdk

sentry_sdk.init(dsn="...")

def handle_request(user_id):
    # 设置用户上下文
    with sentry_sdk.configure_scope() as scope:
        scope.user = {"id": user_id, "email": "user@example.com"}

    try:
        risky_operation()
    except Exception as e:
        # 手动捕获，附带额外信息
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("operation", "checkout")
            scope.set_extra("cart_size", 5)
            sentry_sdk.capture_exception(e)
```

### 2.4 常见错误：DSN 泄露

```python
# ❌ 错误：DSN 硬编码
sentry_sdk.init(dsn="https://abc123@sentry.io/456")

# ✅ 正确：从环境变量读取
sentry_sdk.init(dsn=os.environ["SENTRY_DSN"])
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Sentry 集成

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_sentry.py`
**核心代码**（行 1-47）：

```python
from configs import dify_config
from dify_app import DifyApp


def init_app(app: DifyApp):
    if dify_config.SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.flask import FlaskIntegration
        from werkzeug.exceptions import HTTPException

        from graphon.model_runtime.errors.invoke import InvokeRateLimitError

        try:
            from langfuse._utils import parse_error

            _langfuse_error_response = parse_error.defaultErrorResponse
        except (ImportError, AttributeError):
            _langfuse_error_response = (
                "Unexpected error occurred. Please check your request"
                " and contact support: https://langfuse.com/support."
            )

        def before_send(event, hint):
            if "exc_info" in hint:
                _, exc_value, _ = hint["exc_info"]
                if _langfuse_error_response in str(exc_value):
                    return None

            return event

        sentry_sdk.init(
            dsn=dify_config.SENTRY_DSN,
            integrations=[FlaskIntegration(), CeleryIntegration()],
            ignore_errors=[
                HTTPException,
                ValueError,
                FileNotFoundError,
                InvokeRateLimitError,
                _langfuse_error_response,
            ],
            traces_sample_rate=dify_config.SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=dify_config.SENTRY_PROFILES_SAMPLE_RATE,
            environment=dify_config.DEPLOY_ENV,
            release=f"dify-{dify_config.project.version}-{dify_config.COMMIT_SHA}",
            before_send=before_send,
        )
```

**解读**：
- 第 5 行：**DSN 为空时跳过整个初始化**——本地开发无需 Sentry
- 第 6-9 行：延迟导入——只在配置 Sentry 时才加载 sentry_sdk（节省启动开销）
- 第 11 行：导入 `InvokeRateLimitError`（dify 限流错误），准备忽略
- 第 13-22 行：尝试导入 Langfuse 默认错误响应字符串
  - 第 14 行：用 `try/except` 兜底，避免 langfuse 未安装时崩溃
  - 第 21-22 行：Langfuse 未安装时使用 fallback 字符串
- 第 24-30 行：`before_send` 钩子——过滤 Langfuse 错误（避免和 Langfuse 内部错误重复上报）
- 第 32-47 行：初始化 Sentry
  - 第 34-35 行：同时集成 Flask 和 Celery
  - 第 36-42 行：`ignore_errors` 列表——HTTP 异常、ValueError、限流等不需要上报
  - 第 43-44 行：可配置的采样率
  - 第 45 行：环境标识（development / production）
  - 第 46 行：`release` 字段标识代码版本，便于 Sentry 识别"新引入的 bug"
  - 第 47 行：`before_send` 钩子
- **关键设计**：
  - DSN 可选（不影响本地开发）
  - 多层错误过滤（Langfuse + ValueError + HTTPException）
  - `release` 包含 git commit，便于关联代码版本

### 3.2 关键设计决策分析

**为什么 ignore_errors 包含 HTTPException？**

```python
ignore_errors=[
    HTTPException,           # 4xx 客户端错误
    ValueError,              # 参数错误
    FileNotFoundError,       # 资源缺失
    InvokeRateLimitError,    # LLM 限流
    _langfuse_error_response, # Langfuse 内部错误
]
```

**原因**：
1. **HTTPException**：4xx 是用户错误，不是 bug
2. **ValueError**：通常是参数校验失败，业务逻辑
3. **FileNotFoundError**：文件丢失，但可能是临时 IO 问题
4. **InvokeRateLimitError**：限流是预期行为，不是 bug
5. **Langfuse 错误**：避免和 Langfuse 自身告警重复

### 3.3 dify 中 Sentry 与 OTEL 的协同

**Sentry 和 OTEL 不冲突，而是互补**：
- **Sentry**：关注异常事件，用于 bug 定位
- **OTEL**：关注完整 trace，用于性能分析

两者可以共存于同一个应用：
- Sentry 自动捕获 Flask / Celery 异常
- OTEL 自动埋点所有 HTTP / DB / Redis 调用
- 当 Sentry 报异常时，可通过 trace_id 跳转到 OTEL 后端看完整链路

## 4. 关键要点总结

- **Sentry** 专注异常追踪，与日志系统互补
- dify 用 **DSN 环境变量**配置，本地开发默认关闭
- 集成 **Flask + Celery** 两大框架
- 通过 `ignore_errors` + `before_send` 过滤噪音异常
- `release` 字段标识代码版本（`dify-{version}-{commit}`）
- Sentry 和 OTEL 互补：异常 → Sentry，链路 → OTEL

## 5. 练习题

### 练习 1：基础（必做）

注册一个 Sentry 账号（免费版），获取 DSN，配置 dify 的 `SENTRY_DSN` 环境变量，触发一个未捕获异常，在 Sentry UI 中查看。

### 练习 2：进阶

阅读 `api/extensions/ext_sentry.py`，解释 dify 为什么要 ignore `InvokeRateLimitError` 和 `HTTPException`？如果不忽略会有什么后果？

### 练习 3：挑战（选做）

扩展 dify 的 `ext_sentry.py`，新增一个 `before_send_transaction` 钩子：过滤掉所有 `traces_sample_rate=0` 的 transaction，并附带 `tenant_id` 标签。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_sentry.py`
- Sentry Python SDK：https://docs.sentry.io/platforms/python/
- Sentry Flask 集成：https://docs.sentry.io/platforms/python/guides/flask/
- Sentry Celery 集成：https://docs.sentry.io/platforms/python/guides/celery/
- Sentry vs 日志系统：https://docs.sentry.io/product/issues/

---

**文档版本**：v1.0
**最后更新**：2026-07-13