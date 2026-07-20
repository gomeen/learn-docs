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

## 3. 关键要点总结

- dify 日志系统：`ext_logging.init_app` → Handler + Filter + Formatter
- 双格式输出：`LOG_OUTPUT_FORMAT=text|json`
- 三大组件协作：`ContextVar` → `Filter` → `Formatter`
- Filter 必须用 try/except 兜底，不能影响业务
- `force=True` 重置 root logger，避免重复初始化
- 禁用 SQLAlchemy 等"噪音 logger"的 propagation

---

**文档版本**：v1.0
**最后更新**：2026-07-13
