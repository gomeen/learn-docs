# 10.1.1 日志级别：DEBUG / INFO / WARNING / ERROR

> 理解日志级别的语义、选择标准和 dify 中的实际使用规范。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Python logging 模块的 5 个标准级别
- 掌握不同级别的适用场景
- 能在 dify 中选择合适的日志级别记录事件
- 能看懂 `api/configs/feature/__init__.py` 中的 `LOG_LEVEL` 配置

## 📚 前置知识

- Python 基础语法
- `../../dify/01-fundamentals/06-modules-and-imports.md`（了解 import 机制）

## 1. 核心概念

### 1.1 日志级别的语义

日志级别（Log Level）是一种**过滤机制**：当 logger 设置为某个级别后，低于该级别的日志会被丢弃。

Python `logging` 模块定义了 5 个标准级别，按严重程度递增：

| 级别 | 数值 | 语义 | 典型场景 |
|------|------|------|----------|
| `DEBUG` | 10 | 调试信息，开发者专用 | 变量值、循环计数器、内部状态 |
| `INFO` | 20 | 正常运行信息 | 服务启动、请求完成、配置加载 |
| `WARNING` | 30 | 警告，不影响主流程 | 重试、降级、过期 API 调用 |
| `ERROR` | 40 | 错误，部分功能失败 | 异常捕获、关键操作失败 |
| `CRITICAL` | 50 | 致命错误，应用崩溃 | 数据库不可用、磁盘满 |

### 1.2 级别选择的判断准则

回答三个问题：

1. **如果不打这条日志，排查问题时是否缺少关键信息？**
   - 是 → DEBUG（开发环境）/ INFO（生产环境）
   - 否 → 删掉

2. **这条日志是否表示"非预期但可恢复"的状态？**
   - 是 → WARNING
   - 否（属于预期行为） → DEBUG 或 INFO

3. **看到这条日志，是否需要立即人工介入？**
   - 是 → ERROR 或 CRITICAL
   - 否 → WARNING

### 1.3 级别继承

`logging` 是层级结构：root logger 是顶层，子 logger 继承父级配置。

```python
# root logger
logging.basicConfig(level=logging.INFO)

# 子 logger 自动继承 INFO 级别
logger = logging.getLogger("dify.core.workflow")
logger.debug("不会打印")  # 因为级别 < INFO
logger.info("会打印")
```

## 2. 代码示例

### 2.1 基础用法

```python
import logging

# 创建一个 logger（通常以模块名命名）
logger = logging.getLogger(__name__)

def divide(a: float, b: float) -> float:
    logger.debug(f"divide called: a={a}, b={b}")  # 调试细节

    if b == 0:
        logger.error(f"Division by zero: a={a}")  # 错误
        raise ValueError("b must not be zero")

    result = a / b
    logger.info(f"divide result: {result}")  # 正常结果
    return result


def fetch_url(url: str, retries: int = 3):
    for i in range(retries):
        try:
            return requests.get(url)
        except requests.RequestException:
            # 重试是"可恢复"，所以是 WARNING
            logger.warning(f"Retry {i+1}/{retries} for {url}")
    logger.error(f"Failed to fetch {url} after {retries} retries")
```

### 2.2 常见错误：ERROR vs WARNING

```python
# ❌ 错误：用户没登录是"可预期的业务状态"，不该用 ERROR
def view_profile(user):
    if not user:
        logger.error("User not logged in")  # 触发告警，会刷屏
        return None

# ✅ 正确：用 DEBUG 或 INFO
def view_profile(user):
    if not user:
        logger.debug("Anonymous user, redirect to login")  # 日常情况
        return None
```

### 2.3 常见错误：CRITICAL 滥用

```python
# ❌ 错误：单个消息发送失败不是"致命"
def send_notification(user_id, msg):
    try:
        push_service.send(user_id, msg)
    except Exception:
        logger.critical("Push failed")  # 会触发紧急告警，淹没真实问题

# ✅ 正确：用 ERROR，并附带上下文
def send_notification(user_id, msg):
    try:
        push_service.send(user_id, msg)
    except Exception:
        logger.exception("Push failed for user_id=%s", user_id)  # ERROR + stack trace
```

## 3. dify 仓库源码解读

### 3.1 日志级别的配置定义

**文件位置**：`/Users/xu/code/github/dify/api/configs/feature/__init__.py`
**核心代码**（行 679-687）：

```python
class LoggingConfig(BaseSettings):
    """
    Configuration for application logging
    """

    LOG_LEVEL: str = Field(
        description="Logging level, default to INFO. Set to ERROR for production environments.",
        default="INFO",
    )

    LOG_OUTPUT_FORMAT: Literal["text", "json"] = Field(
        description="Log output format: 'text' for human-readable, 'json' for structured JSON logs.",
        default="text",
    )
```

**解读**：
- 第 5 行：默认 `INFO`——开发友好，生产可通过环境变量调到 `ERROR`
- 第 9 行：`LOG_OUTPUT_FORMAT` 用 `Literal` 限制只能取 `text` 或 `json`，避免拼写错误
- **关键设计**：级别可由 `LOG_LEVEL` 环境变量覆盖，方便生产环境按需调整

### 3.2 日志级别在 dify 中的实际使用

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 192-199）：

```python
# Credential might have been deleted between lookups (async timing)
# Return ID but empty name rather than failing
logger.warning(
    "Failed to lookup credential name for credential_id=%s (provider=%s, model=%s): %s",
    credential_id,
    provider,
    model,
    str(e),
    exc_info=True,
)
```

**解读**：
- 第 4-9 行：`logger.warning` + `exc_info=True`——记录异常但不让请求失败
- **判断准则**：这里"凭据被异步删除"是非预期但可恢复的，符合 WARNING 定义
- **位置参数优于 f-string**：dify 用 `logger.warning("...%s...", arg)` 而不是 f-string，避免在日志被过滤时仍做字符串拼接

## 4. 关键要点总结

- 5 个级别按严重度递增：`DEBUG < INFO < WARNING < ERROR < CRITICAL`
- 选择准则：是否需要排查信息？是否非预期？是否需要立即介入？
- **WARNING 用于"可恢复的非预期"**，**ERROR 用于"需要关注的功能失败"**
- dify 风格：用 `%s` 占位符而非 f-string，性能更好
- dify 默认 `LOG_LEVEL=INFO`，生产可调为 `ERROR`

## 5. 练习题

### 练习 1：基础（必做）

为以下场景选择合适的日志级别，并写一段伪代码：
1. 用户登录成功
2. 数据库连接失败
3. 第三方 API 返回 429（限流，详见 [限流](../../_common/03-cache-patterns/04-rate-limiting.md)），开始重试
4. Redis 缓存未命中（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)），触发数据库查询
5. 配置文件加载完成

### 练习 2：进阶

阅读 `api/extensions/ext_logging.py`，画出 dify 日志系统的初始化流程图（从 `init_app` 到 `logging.basicConfig`）。

### 练习 3：挑战（选做）

修改 `api/configs/feature/__init__.py` 的 `LoggingConfig`，新增 `LOG_LEVEL_OVERRIDES: dict[str, str]` 字段，允许对特定 logger（如 `sqlalchemy.engine`）单独设置级别，并实现一个 `apply_level_overrides()` 函数。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/configs/feature/__init__.py`
- `/Users/xu/code/github/dify/api/extensions/ext_logging.py`
- `/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
- Python logging 官方文档：https://docs.python.org/3/library/logging.html#logging-levels

---

**文档版本**：v1.0
**最后更新**：2026-07-13