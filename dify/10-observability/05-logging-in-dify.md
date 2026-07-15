# 10.1.5 dify 的日志体系分析

> 系统性梳理 dify 的日志架构：从配置、初始化、过滤器、格式化器到与 Sentry/OTEL 的集成。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 dify 日志系统的整体架构
- 理解 Logger / Filter / Formatter / Handler 在 dify 中的协作
- 能根据环境灵活切换 text 和 JSON 输出
- 能扩展 dify 的日志系统（如新增字段、集成第三方服务）

## 📚 前置知识

- 10.1.1 ~ 10.1.4 日志相关文档
- Flask 应用结构（`dify_app.py`）
- OpenTelemetry 基础（10.3.2）

## 1. 核心概念

### 1.1 dify 日志系统的分层架构

```
┌─────────────────────────────────────────────────────┐
│                 dify_app.py                          │
│  Flask app.extensions['logging'] ← init_app()       │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┴─────────────┐
        ▼                          ▼
   ┌─────────┐               ┌──────────┐
   │ Config  │               │ Runtime  │
   │ LOG_*   │               │ Logger   │
   └─────────┘               └──────────┘
        │                          │
        ▼                          ▼
   LoggingConfig           Application Code
   (Pydantic)              logger.info(...)
        │                          │
        └──────────┬───────────────┘
                   ▼
         ┌──────────────────┐
         │   ext_logging    │
         │   init_app()     │
         └────────┬─────────┘
                  │
   ┌──────────────┼──────────────┐
   ▼              ▼              ▼
┌────────┐  ┌──────────┐  ┌──────────────┐
│Handler │  │  Filter  │  │  Formatter   │
│Stdout  │  │ Trace    │  │  Text/JSON   │
│RotFile │  │ Identity │  │              │
└────────┘  └──────────┘  └──────────────┘
```

### 1.2 双格式输出：text vs json

dify 通过 `LOG_OUTPUT_FORMAT` 配置项支持两种格式：

| 格式 | 适用场景 | 字段来源 |
|------|----------|----------|
| `text` | 本地开发、tail -f | LOG_FORMAT 模板 |
| `json` | 生产环境、K8s + Loki/ELK | StructuredJSONFormatter |

### 1.3 日志系统的扩展点

dify 在 `core/logging/` 目录提供了模块化组件：

| 文件 | 职责 |
|------|------|
| `__init__.py` | 统一导出（filter/formatter/context） |
| `context.py` | ContextVar 定义（request_id / trace_id） |
| `filters.py` | Filter 实现（trace / identity） |
| `structured_formatter.py` | JSON 格式化器 |

新增日志字段只需要在三个地方加：
1. `context.py` 定义 ContextVar（可选）
2. `filters.py` 实现 filter，注入到 `LogRecord`
3. `structured_formatter.py` 在 `_build_log_dict` 中输出

## 2. 代码示例

### 2.1 启动 dify 时的日志初始化

```python
# api/dify_app.py 中的核心逻辑
from configs import dify_config
from extensions import ext_logging

def create_app() -> Flask:
    app = Flask(__name__)
    # ... 其他扩展 ...
    ext_logging.init_app(app)  # 初始化日志
    return app
```

**说明**：
- `ext_logging.init_app` 由 Flask 扩展机制调用
- 所有配置从 `dify_config.LOG_*` 读取
- 通过环境变量切换行为，无需改代码

### 2.2 在业务代码中使用 logger

```python
import logging

logger = logging.getLogger(__name__)  # 推荐命名约定

def process_message(user_id: str, content: str):
    logger.info("开始处理消息")  # 自动带上 trace_id + identity
    try:
        result = llm_call(content)
        logger.info(
            "LLM 调用完成",
            extra={"attributes": {
                "user_id": user_id,
                "tokens": result.tokens,
                "latency_ms": result.latency,
            }}
        )
    except Exception as e:
        logger.exception("LLM 调用失败")  # 自动加 stack_trace
        raise
```

### 2.3 切换为 JSON 格式

```bash
# .env 或环境变量
LOG_OUTPUT_FORMAT=json
LOG_LEVEL=INFO
LOG_FILE=/var/log/dify/app.log
LOG_FILE_MAX_SIZE=50
LOG_FILE_BACKUP_COUNT=10
```

启动后，所有日志输出为 JSON，便于 Loki / Elasticsearch 解析。

## 3. dify 仓库源码解读

### 3.1 ext_logging.py 的初始化流程

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_logging.py`
**核心代码**（行 13-58）：

```python
def init_app(app: DifyApp):
    """Initialize logging with support for text or JSON format."""
    log_handlers: list[logging.Handler] = []

    # File handler
    log_file = dify_config.LOG_FILE
    if log_file:
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)
        log_handlers.append(
            RotatingFileHandler(
                filename=log_file,
                maxBytes=dify_config.LOG_FILE_MAX_SIZE * 1024 * 1024,
                backupCount=dify_config.LOG_FILE_BACKUP_COUNT,
            )
        )

    # Console handler
    sh = logging.StreamHandler(sys.stdout)
    log_handlers.append(sh)

    # Apply filters to all handlers
    from core.logging.filters import IdentityContextFilter, TraceContextFilter

    for handler in log_handlers:
        handler.addFilter(TraceContextFilter())
        handler.addFilter(IdentityContextFilter())

    # Configure formatter based on format type
    formatter = _create_formatter()
    for handler in log_handlers:
        handler.setFormatter(formatter)

    # Configure root logger
    logging.basicConfig(
        level=dify_config.LOG_LEVEL,
        handlers=log_handlers,
        force=True,
    )

    # Disable propagation for noisy loggers to avoid duplicate logs
    logging.getLogger("sqlalchemy.engine").propagate = False

    # Apply timezone if specified (only for text format)
    if dify_config.LOG_OUTPUT_FORMAT == "text":
        _apply_timezone(log_handlers)
```

**解读**：
- 第 5-13 行：可选的文件 handler，按大小切割
- 第 16-17 行：始终有 stdout handler（Docker / K8s 友好，详见 [Docker 核心概念](../../_common/09-containerization/01-concepts.md)）
- 第 20-24 行：**所有 handler 都加两个 filter**——确保 trace_id 和 identity 始终注入
- 第 27-31 行：每个 handler 设置统一的 formatter
- 第 34-38 行：`basicConfig(level=..., handlers=..., force=True)` 重置 root logger
- 第 41 行：禁用 SQLAlchemy 日志传播，避免 SQL 刷屏
- 第 44-45 行：只有 text 格式才应用时区（JSON 已经是 UTC ISO 8601）

### 3.2 格式化器选择逻辑

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_logging.py`
**核心代码**（行 61-72）：

```python
def _create_formatter() -> logging.Formatter:
    """Create appropriate formatter based on configuration."""
    if dify_config.LOG_OUTPUT_FORMAT == "json":
        from core.logging.structured_formatter import StructuredJSONFormatter

        return StructuredJSONFormatter()
    else:
        # Text format - use existing pattern with backward compatible formatter
        return _TextFormatter(
            fmt=dify_config.LOG_FORMAT,
            datefmt=dify_config.LOG_DATEFORMAT,
        )
```

**解读**：
- 第 4-6 行：JSON 模式延迟导入 `StructuredJSONFormatter`（避免启动开销）
- 第 8-11 行：text 模式用 `_TextFormatter`（保证 `req_id/trace_id/span_id` 字段一定存在）
- **关键设计**：根据环境变量动态选择 formatter，无需重启应用代码

### 3.3 统一导出层

**文件位置**：`/Users/xu/code/github/dify/api/core/logging/__init__.py`
**核心代码**（行 1-21）：

```python
"""Structured logging components for Dify."""

from core.logging.context import (
    clear_request_context,
    get_request_id,
    get_trace_id,
    init_request_context,
)
from core.logging.filters import IdentityContextFilter, TraceContextFilter
from core.logging.structured_formatter import StructuredJSONFormatter

__all__ = [
    "IdentityContextFilter",
    "StructuredJSONFormatter",
    "TraceContextFilter",
    "clear_request_context",
    "get_request_id",
    "get_trace_id",
    "init_request_context",
]
```

**解读**：
- 第 3-15 行：集中 re-export，让外部代码只用 `from core.logging import ...`
- 第 17-20 行：`__all__` 明确公共 API
- **好处**：内部重构不影响调用方（如把 filters.py 拆成多个文件）

## 4. 关键要点总结

- dify 日志系统：`ext_logging.init_app` → Handler + Filter + Formatter
- 双格式输出：`LOG_OUTPUT_FORMAT=text|json`
- 三大组件协作：`ContextVar` → `Filter` → `Formatter`
- Filter 必须用 try/except 兜底，不能影响业务
- `force=True` 重置 root logger，避免重复初始化
- 禁用 SQLAlchemy 等"噪音 logger"的 propagation

## 5. 练习题

### 练习 1：基础（必做）

在本地启动 dify，把 `LOG_OUTPUT_FORMAT` 改为 `json`，然后在任意 endpoint 触发一次请求，观察 stdout 的日志输出格式。

### 练习 2：进阶

阅读 `api/extensions/ext_logging.py` 的全部代码，画出 `init_app` 的完整调用流程图（包含所有 filter 和 formatter 的注册顺序）。

### 练习 3：挑战（选做）

扩展 dify 的日志系统，新增一个 `RequestDurationFilter`：自动计算当前请求的处理时长，并把 `request_duration_ms` 字段注入 JSON 日志。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_logging.py`
- `/Users/xu/code/github/dify/api/core/logging/__init__.py`
- `/Users/xu/code/github/dify/api/core/logging/context.py`
- `/Users/xu/code/github/dify/api/core/logging/filters.py`
- `/Users/xu/code/github/dify/api/core/logging/structured_formatter.py`
- `/Users/xu/code/github/dify/api/configs/feature/__init__.py`（LoggingConfig）

---

**文档版本**：v1.0
**最后更新**：2026-07-13