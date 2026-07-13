# 10.1.3 结构化日志：JSON 格式

> 把日志从"人类可读字符串"升级为"机器可解析的 JSON 字段"，让日志能被 ELK / Loki 等系统高效处理。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解结构化日志相对于文本日志的优势
- 掌握 JSON 日志的常见字段约定
- 能在 Python 中实现自定义 JSON Formatter
- 能看懂 dify `core/logging/structured_formatter.py` 的设计

## 📚 前置知识

- 10.1.2 Python logging 模块（`02-python-logging.md`）
- JSON 语法
- 04-cache-and-queue：序列化基础

## 1. 核心概念

### 1.1 为什么需要结构化日志？

**文本日志**（默认）：
```
2026-07-13 10:30:15.123 INFO [worker-1] [app.py:42] abc123 - User logged in, user_id=42
```

**结构化日志（JSON）**：
```json
{
  "ts": "2026-07-13T10:30:15.123Z",
  "severity": "INFO",
  "service": "dify-api",
  "caller": "app.py:42",
  "trace_id": "abc123",
  "message": "User logged in",
  "attributes": {"user_id": 42}
}
```

**核心差异**：

| 维度 | 文本日志 | JSON 日志 |
|------|----------|-----------|
| 解析速度 | 需要正则 | 直接 `jq` / `json.loads` |
| 字段提取 | 脆弱（格式变了就坏） | 稳定（字段名固定） |
| 嵌套结构 | 难以表达 | 原生支持 |
| 索引效率 | 全文扫描 | 按字段建索引 |
| 适合人类 | ✅ | ❌（需要工具） |

### 1.2 常见 JSON 日志字段

参考 OpenTelemetry、ECS（Elastic Common Schema）等规范：

| 字段 | 类型 | 说明 |
|------|------|------|
| `ts` | ISO 8601 string | 时间戳（UTC） |
| `severity` | string | 日志级别（INFO / WARN / ERROR） |
| `service` | string | 服务名（如 `dify-api`） |
| `caller` | string | 代码位置（`file.py:line`） |
| `message` | string | 主要消息 |
| `trace_id` | hex string | 链路追踪 ID（32 字符） |
| `span_id` | hex string | 当前 span ID（16 字符） |
| `attributes` | object | 自定义键值对 |
| `stack_trace` | string | 异常堆栈（ERROR 时） |

### 1.3 实现 JSON Formatter

继承 `logging.Formatter`，重写 `format()` 方法：

```python
import logging
import json
from datetime import datetime, UTC

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "ts": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "message": record.getMessage(),
            "caller": f"{record.filename}:{record.lineno}",
        }
        if record.exc_info:
            log_obj["stack_trace"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)
```

## 2. 代码示例

### 2.1 完整示例：自定义 JSON Formatter

```python
import logging
import json
import orjson  # 更快的 JSON 库
from datetime import UTC, datetime


class StructuredJSONFormatter(logging.Formatter):
    """输出符合 OpenTelemetry 风格的 JSON 日志。"""

    SEVERITY_MAP = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARN",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "ERROR",
    }

    def __init__(self, service_name: str = "my-service"):
        super().__init__()
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_dict = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "severity": self.SEVERITY_MAP.get(record.levelno, "INFO"),
            "service": self._service_name,
            "caller": f"{record.filename}:{record.lineno}",
            "message": record.getMessage(),
        }
        if record.exc_info:
            import traceback
            log_dict["stack_trace"] = "".join(
                traceback.format_exception(*record.exc_info)
            )
        return orjson.dumps(log_dict).decode("utf-8")


# 使用
handler = logging.StreamHandler()
handler.setFormatter(StructuredJSONFormatter("dify-test"))
logger = logging.getLogger("demo")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

logger.info("User logged in", extra={"attributes": {"user_id": 42}})
# 输出：{"ts":"2026-07-13T...","severity":"INFO","service":"dify-test","caller":"demo.py:34","message":"User logged in"}
```

### 2.2 常见错误：未序列化的对象

```python
import logging
import json

logger = logging.getLogger("demo")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ❌ 错误：datetime 对象无法直接 JSON 序列化
logger.info({"user_id": 42, "created_at": datetime.now()})
# json.dumps 会抛 TypeError

# ✅ 正确：用 default=str 兜底，或在记录前序列化
class SafeFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {"message": record.getMessage(), "time": datetime.now()},
            default=str,  # 不可序列化的对象转 str
        )

handler.setFormatter(SafeFormatter())
logger.info("test")
```

### 2.3 通过 `extra` 注入动态字段

```python
import logging

logger = logging.getLogger("demo")

# extra 参数会把字段添加到 LogRecord
logger.info(
    "User logged in",
    extra={"attributes": {"user_id": 42, "ip": "1.2.3.4"}}
)
# 在 Formatter 中可通过 getattr(record, "attributes", {}) 获取
```

## 3. dify 仓库源码解读

### 3.1 dify 的 StructuredJSONFormatter

**文件位置**：`/Users/xu/code/github/dify/api/core/logging/structured_formatter.py`
**核心代码**（行 49-71）：

```python
class StructuredJSONFormatter(logging.Formatter):
    """
    JSON log formatter following the specified schema:
    {
      "ts": "ISO 8601 UTC",
      "severity": "INFO|ERROR|WARN|DEBUG",
      "service": "service name",
      "caller": "file:line",
      "trace_id": "hex 32",
      "span_id": "hex 16",
      "identity": { "tenant_id", "user_id", "user_type" },
      "message": "log message",
      "attributes": { ... },
      "stack_trace": "..."
    }
    """

    SEVERITY_MAP: dict[int, str] = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARN",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "ERROR",
    }

    def __init__(self, service_name: str | None = None):
        super().__init__()
        self._service_name = service_name or dify_config.APPLICATION_NAME
```

**解读**：
- 第 16-21 行：用 docstring 显式定义 schema，方便团队对齐
- 第 23-28 行：`SEVERITY_MAP` 把 Python 数字级别映射为字符串，并合并 `CRITICAL → ERROR`
- 第 30-32 行：服务名从 `dify_config.APPLICATION_NAME` 自动读取
- **关键设计**：schemafirst——字段定义写在 docstring，比代码更稳定

### 3.2 字段组装逻辑

**文件位置**：`/Users/xu/code/github/dify/api/core/logging/structured_formatter.py`
**核心代码**（行 72-105）：

```python
def _build_log_dict(self, record: logging.LogRecord) -> LogDict:
    # Core fields
    log_dict: LogDict = {
        "ts": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "severity": self.SEVERITY_MAP.get(record.levelno, "INFO"),
        "service": self._service_name,
        "caller": f"{record.filename}:{record.lineno}",
        "message": record.getMessage(),
    }

    # Trace context (from TraceContextFilter)
    trace_id = getattr(record, "trace_id", "")
    span_id = getattr(record, "span_id", "")

    if trace_id:
        log_dict["trace_id"] = trace_id
    if span_id:
        log_dict["span_id"] = span_id

    # Identity context (from IdentityContextFilter)
    identity = self._extract_identity(record)
    if identity:
        log_dict["identity"] = identity

    # Dynamic attributes
    attributes = getattr(record, "attributes", None)
    if attributes:
        log_dict["attributes"] = attributes

    # Stack trace for errors with exceptions
    if record.exc_info and record.levelno >= logging.ERROR:
        log_dict["stack_trace"] = self._format_exception(record.exc_info)

    return log_dict
```

**解读**：
- 第 3-9 行：核心字段固定 5 个（ts/severity/service/caller/message）
- 第 12-17 行：`getattr(record, ..., "")` 兜底——filter 没运行时也不会 KeyError
- 第 25-26 行：`attributes` 由 logger 的 `extra` 参数提供
- 第 29-30 行：**只在 ERROR 级别才加 stack_trace**，避免日志膨胀
- **关键设计**：用 `TypedDict` 约束字段类型，避免字段拼写错误

## 4. 关键要点总结

- 结构化日志 = 机器可解析的 JSON 字段，便于检索和分析
- 关键字段：`ts`、`severity`、`service`、`message`、`trace_id`、`attributes`
- 用 `extra={"attributes": {...}}` 注入动态字段
- dify 用 `orjson`（性能优于标准库 `json`）
- ERROR 级别才加 stack_trace，控制日志体积

## 5. 练习题

### 练习 1：基础（必做）

写一个 `JSONFormatter`，输出包含 `ts`（ISO 8601）、`level`、`message`、`module` 四个字段的 JSON 日志。

### 练习 2：进阶

阅读 `api/core/logging/structured_formatter.py` 的 `_extract_identity` 方法，画出字段提取流程图：从 `LogRecord` 到最终 JSON 中的 `identity` 字典。

### 练习 3：挑战（选做）

扩展 `StructuredJSONFormatter`，新增一个 `mask_sensitive` 功能：自动检测 `attributes` 中的字段名（如 `password`、`api_key`），把值替换为 `***`。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/logging/structured_formatter.py`
- `/Users/xu/code/github/dify/api/core/logging/filters.py`
- Elastic Common Schema：https://www.elastic.co/guide/en/ecs/current/ecs-reference.html
- OpenTelemetry Logs Data Model：https://opentelemetry.io/docs/specs/logs/data-model/

---

**文档版本**：v1.0
**最后更新**：2026-07-13