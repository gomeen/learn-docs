# 10.1.2 Python `logging` 模块与 Logger 层级

> 掌握 Python 标准库 `logging` 的四大组件与层级模型，能配置复杂项目的日志。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Logger / Handler / Filter / Formatter 四大组件的关系
- 掌握 Logger 的层级结构和命名规范
- 能在 Flask 应用中配置日志系统
- 能看懂 dify `extensions/ext_logging.py` 的初始化流程

## 📚 前置知识

- 10.1.1 日志级别（`01-log-levels.md`）
- Python 基础语法（模块、装饰器）

## 1. 核心概念

### 1.1 四大组件

Python `logging` 由四类对象协作：

```
Logger          →  入口，调用者用 logger.info(...) 产生 LogRecord
  │  (log() 调用)
  ▼
Filter          →  过滤，决定 LogRecord 是否通过
  │
  ▼
Handler         →  输出，把 LogRecord 写到文件 / 控制台 / 网络
  │
  ▼
Formatter       →  格式化，把 LogRecord 转换为字符串
```

**完整流程**：
1. 用户调用 `logger.info("msg")`
2. Logger 检查自己的级别，过滤低级别日志
3. LogRecord 经过所有 Filter
4. Logger 把 LogRecord 传给所有 Handler
5. 每个 Handler 用自己的 Filter 过滤，再交给 Formatter
6. Formatter 输出最终字符串

### 1.2 Logger 层级

Logger 用 `.` 分隔的字符串命名，形成树状结构：

```
root
├── dify
│   ├── dify.core
│   │   ├── dify.core.workflow
│   │   └── dify.core.llm
│   └── dify.api
└── sqlalchemy
```

**继承规则**：子 logger 默认继承父 logger 的 Handler 和级别。

```python
# 配置根 logger，影响所有子 logger
logging.basicConfig(level=logging.INFO)

# 子 logger 自动继承
logger = logging.getLogger("dify.core.workflow")
logger.info("...")  # 会输出（继承 INFO 级别）
```

**推荐命名**：用 `__name__`（即模块的完整路径），自动形成有意义的层级。

```python
# 在 services/auth.py 中
logger = logging.getLogger(__name__)
# logger.name == "services.auth" 或 "api.services.auth"
```

### 1.3 常用 Handler

| Handler | 用途 |
|---------|------|
| `StreamHandler` | 输出到 stdout/stderr |
| `RotatingFileHandler` | 按大小切割日志文件 |
| `TimedRotatingFileHandler` | 按时间切割日志文件 |
| `SMTPHandler` | 通过邮件发送 ERROR 日志 |
| `SysLogHandler` | 发送到系统日志服务 |

## 2. 代码示例

### 2.1 基础：四大组件协作

```python
import logging
import sys

# 1. 创建 logger
logger = logging.getLogger("myapp")
logger.setLevel(logging.DEBUG)

# 2. 创建 handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)  # handler 也有自己的级别

# 3. 创建 formatter
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
console_handler.setFormatter(formatter)

# 4. 绑定到 logger
logger.addHandler(console_handler)

# 测试
logger.debug("这条不会显示")  # logger=DEBUG, handler=INFO → 被 handler 过滤
logger.info("应用启动")
```

### 2.2 自定义 Filter：注入请求上下文

```python
import logging
import uuid

_request_id: str = ""

class RequestContextFilter(logging.Filter):
    """给每条日志自动加上 request_id 字段。"""
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id
        return True

# 设置
handler = logging.StreamHandler()
handler.addFilter(RequestContextFilter())
handler.setFormatter(logging.Formatter(
    "[%(request_id)s] %(levelname)s - %(message)s"
))
logger = logging.getLogger("myapp")
logger.addHandler(handler)

# 模拟请求处理
def handle_request():
    global _request_id
    _request_id = uuid.uuid4().hex[:8]
    logger.info("处理请求")  # 自动带上 request_id
```

### 2.3 常见错误：重复添加 Handler

```python
import logging

logger = logging.getLogger("myapp")

def configure():
    # ❌ 错误：每次调用都会新增 handler，导致日志重复输出
    handler = logging.StreamHandler()
    logger.addHandler(handler)

# ✅ 正确：先清空再加
def configure():
    logger.handlers.clear()
    handler = logging.StreamHandler()
    logger.addHandler(handler)
```

## 3. dify 仓库源码解读

### 3.1 dify 的日志初始化

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
```

**解读**：
- 第 6-14 行：可选的 `RotatingFileHandler`，按大小切割日志（默认 20MB × 5 份）
- 第 17-18 行：始终添加 stdout handler，方便容器化环境（Docker/K8s）收集
- 第 24-25 行：用 `addFilter` 给所有 handler 注入 trace_id 和 user identity
- 第 37-39 行：`force=True` 会重置已有配置，避免重复
- 第 42 行：禁用 `sqlalchemy.engine` 的日志传播，避免 SQL 查询刷屏

### 3.2 文本格式化器：保证字段永远存在

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_logging.py`
**核心代码**（行 93-104）：

```python
class _TextFormatter(logging.Formatter):
    """Text formatter that ensures trace_id and req_id are always present."""

    @override
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "req_id"):
            record.req_id = ""
        if not hasattr(record, "trace_id"):
            record.trace_id = ""
        if not hasattr(record, "span_id"):
            record.span_id = ""
        return super().format(record)
```

**解读**：
- 第 7-11 行：兜底逻辑——如果 filter 没运行（比如 Celery worker 没有 Flask 上下文），字段可能缺失
- 第 12 行：用空字符串兜底，避免日志格式错乱（`KeyError: 'trace_id'`）
- **关键设计**：让 `LOG_FORMAT` 模板可以放心引用 `%(trace_id)s`，不用每次判断

## 4. 关键要点总结

- 四大组件：**Logger**（入口）→ **Filter**（过滤）→ **Handler**（输出）→ **Formatter**（格式化）
- Logger 用 `.` 形成层级，子继承父的配置
- 推荐命名 `__name__`，自动对应模块路径
- dify 用 `force=True` 重置 logging 配置，避免初始化冲突
- dify 给所有 handler 注入 `TraceContextFilter` 和 `IdentityContextFilter`

## 5. 练习题

### 练习 1：基础（必做）

手写一个 `RotatingFileHandler` 配置，要求：
- 日志文件路径 `/tmp/app.log`
- 单文件最大 5MB
- 保留最近 3 个备份
- 同时输出到控制台

### 练习 2：进阶

阅读 `api/core/logging/filters.py`，解释为什么 `IdentityContextFilter` 要放在 `TraceContextFilter` 之后？两个 filter 的职责如何划分？

### 练习 3：挑战（选做）

实现一个 `AsyncSafeContextFilter`：在 asyncio 环境下，把当前的 `task_id` 和 `coroutine_name` 注入到 LogRecord。需要处理 `Task` 切换时上下文丢失的问题。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_logging.py`
- `/Users/xu/code/github/dify/api/core/logging/filters.py`
- `/Users/xu/code/github/dify/api/core/logging/__init__.py`
- Python logging 官方文档：https://docs.python.org/3/library/logging.html
- Python logging cookbook：https://docs.python.org/3/howto/logging-cookbook.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13