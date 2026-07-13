# 4.3.5 定时任务：Celery Beat 调度

> Celery Beat 是 Celery 的定时任务调度器，可以定时执行清理、备份、统计等任务。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 Celery Beat 配置定时任务
- 掌握 crontab / timedelta / solar 调度
- 部署 Beat 时的注意事项（单实例、高可用）
- 理解 dify 的定时任务清单

## 📚 前置知识

- Celery 基础
- Cron 表达式
- 14-celery-architecture.md

## 1. 核心概念

### 1.1 Celery Beat 是什么？

Celery Beat 是**独立的调度进程**，按 schedule 触发任务，把任务扔到 Broker 让 Worker 执行。

```
Beat 进程 → 调度表 → 触发时间到 → 提交任务 → Redis → Worker 执行
```

**注意**：Beat 只触发，**不执行**任务。执行靠 Worker。

### 1.2 调度方式

```python
# 固定间隔
app.conf.beat_schedule = {
    "task-every-hour": {
        "task": "tasks.cleanup",
        "schedule": 3600.0,  # 每 3600 秒
    },
}

# timedelta（更直观）
from datetime import timedelta
app.conf.beat_schedule = {
    "task-every-30min": {
        "task": "tasks.report",
        "schedule": timedelta(minutes=30),
    },
}

# crontab（Unix 风格）
from celery.schedules import crontab
app.conf.beat_schedule = {
    "task-at-midnight": {
        "task": "tasks.cleanup",
        "schedule": crontab(hour=0, minute=0),  # 每天 0 点
    },
}
```

### 1.3 crontab 语法

```python
crontab()                          # 每分钟
crontab(minute=0)                  # 每小时
crontab(hour=0, minute=0)          # 每天 0 点
crontab(hour=2, minute=30)         # 每天 2:30
crontab(day_of_week=1)             # 每周一
crontab(day_of_month=1)            # 每月 1 号
crontab(minute="*/15")             # 每 15 分钟
crontab(minute=0, hour="*/2")      # 每 2 小时
```

### 1.4 Beat 高可用问题

**Beat 必须是单实例**！多个 Beat 会重复触发任务。

**解决方案**：
1. **只部署一个 Beat 实例**
2. 用分布式锁（`celery-beat-mongo` / `celery-redbeat` / `django-celery-beat`）

### 1.5 Beat 持久化

默认 Beat 把调度表存内存，重启会丢失某些调度。可以用 `beat_schedule_filename` 存文件，或用 `django-celery-beat` 存数据库。

## 2. 代码示例

### 2.1 完整定时任务配置

```python
# celery_app.py
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

app = Celery("tasks", broker="redis://localhost:6379/0")

app.conf.beat_schedule = {
    # 每小时清理缓存
    "cleanup-every-hour": {
        "task": "tasks.cleanup_cache",
        "schedule": crontab(minute=0),  # 每小时 0 分
    },
    # 每天凌晨备份数据库
    "backup-daily": {
        "task": "tasks.backup_db",
        "schedule": crontab(hour=3, minute=0),
    },
    # 每 5 分钟检查订单
    "check-orders": {
        "task": "tasks.check_pending_orders",
        "schedule": timedelta(minutes=5),
    },
    # 工作日早上 9 点发送日报
    "daily-report": {
        "task": "tasks.send_daily_report",
        "schedule": crontab(hour=9, minute=0, day_of_week="1-5"),
    },
}
```

### 2.2 启动 Beat

```bash
# 启动 Beat（前台）
celery -A celery_app beat

# 后台启动
celery -A celery_app beat --loglevel=info &

# 启动 Worker（必须独立启动）
celery -A celery_app worker --loglevel=info
```

### 2.3 定时任务本身

```python
@shared_task
def cleanup_cache():
    """每小时清理过期缓存"""
    deleted = redis_client.eval(
        "for _, k in ipairs(redis.call('KEYS', 'cache:*')) do "
        "  redis.call('DEL', k) "
        "end",
        0,
    )
    return {"deleted": deleted}
```

### 2.4 常见错误：Beat 部署多个

```bash
# ❌ 错误：两台机器都启动 Beat
# 机器 A: celery beat
# 机器 B: celery beat
# 结果：每个定时任务被触发两次！

# ✅ 正确：只在一台机器启动 Beat，或用 redbeat
pip install celery-redbeat
celery -A app beat -S redbeat.RedBeatScheduler
```

## 3. dify 仓库源码解读

### 3.1 Beat 调度表

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
**核心代码**（行 163-225）：

```python
beat_schedule: dict[str, CeleryBeatScheduleEntry] = {}
if dify_config.ENABLE_CLEAN_EMBEDDING_CACHE_TASK:
    imports.append("schedule.clean_embedding_cache_task")
    beat_schedule["clean_embedding_cache_task"] = {
        "task": "schedule.clean_embedding_cache_task.clean_embedding_cache_task",
        "schedule": crontab(minute="0", hour="2", day_of_month=f"*/{day}"),
    }
if dify_config.ENABLE_CLEAN_UNUSED_DATASETS_TASK:
    imports.append("schedule.clean_unused_datasets_task")
    beat_schedule["clean_unused_datasets_task"] = {
        "task": "schedule.clean_unused_datasets_task.clean_unused_datasets_task",
        "schedule": crontab(minute="0", hour="3", day_of_month=f"*/{day}"),
    }
if dify_config.ENABLE_CREATE_TIDB_SERVERLESS_TASK:
    imports.append("schedule.create_tidb_serverless_task")
    beat_schedule["create_tidb_serverless_task"] = {
        "task": "schedule.create_tidb_serverless_task.create_tidb_serverless_task",
        "schedule": crontab(minute="0", hour="*"),
    }
```

**解读**：
- 所有定时任务**按配置开关**注册（`ENABLE_*` 环境变量）
- 用 `day_of_month=f"*/{day}"` 控制每月第几天执行
- 不同任务在不同时间段（错峰执行）：
  - `clean_embedding_cache_task`：2 点
  - `clean_unused_datasets_task`：3 点
  - `clean_messages`：4 点
  - `mail_clean_document_notify_task`：周 1 10 点

### 3.2 清理任务列表

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
**核心代码**（行 170-220）：

```python
if dify_config.ENABLE_CLEAN_MESSAGES:
    imports.append("schedule.clean_messages")
    beat_schedule["clean_messages"] = {
        "task": "schedule.clean_messages.clean_messages",
        "schedule": crontab(minute="0", hour="4", day_of_month=f"*/{day}"),
    }
if dify_config.ENABLE_MAIL_CLEAN_DOCUMENT_NOTIFY_TASK:
    imports.append("schedule.mail_clean_document_notify_task")
    beat_schedule["mail_clean_document_notify_task"] = {
        "task": "schedule.mail_clean_document_notify_task.mail_clean_document_notify_task",
        "schedule": crontab(minute="0", hour="10", day_of_week="1"),
    }
if dify_config.ENABLE_DATASETS_QUEUE_MONITOR:
    imports.append("schedule.queue_monitor_task")
    beat_schedule["datasets-queue-monitor"] = {
        "task": "schedule.queue_monitor_task.queue_monitor_task",
        "schedule": timedelta(minutes=dify_config.QUEUE_MONITOR_INTERVAL or 30),
    }
```

**解读**：
- **dify 的定时任务全景**：
  | 任务 | 时间 | 用途 |
  |------|------|------|
  | `clean_embedding_cache_task` | 2 点 | 清理 embedding 缓存 |
  | `clean_unused_datasets_task` | 3 点 | 清理未使用数据集 |
  | `create_tidb_serverless_task` | 每小时 | 创建 TiDB Serverless |
  | `clean_messages` | 4 点 | 清理消息 |
  | `mail_clean_document_notify_task` | 周一 10 点 | 邮件通知文档清理 |
  | `queue_monitor_task` | 每 30 分钟 | 队列监控 |
  | `check_upgradable_plugin_task` | 每 15 分钟 | 检查插件升级 |

### 3.3 动态间隔任务

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
**核心代码**（行 239-257）：

```python
if dify_config.ENABLE_WORKFLOW_SCHEDULE_POLLER_TASK:
    imports.append("schedule.workflow_schedule_task")
    beat_schedule["workflow_schedule_task"] = {
        "task": "schedule.workflow_schedule_task.poll_workflow_schedules",
        "schedule": timedelta(minutes=dify_config.WORKFLOW_SCHEDULE_POLLER_INTERVAL),
    }
if dify_config.ENABLE_TRIGGER_PROVIDER_REFRESH_TASK:
    imports.append("schedule.trigger_provider_refresh_task")
    beat_schedule["trigger_provider_refresh"] = {
        "task": "schedule.trigger_provider_refresh_task.trigger_provider_refresh",
        "schedule": timedelta(minutes=dify_config.TRIGGER_PROVIDER_REFRESH_INTERVAL),
    }

if dify_config.ENABLE_API_TOKEN_LAST_USED_UPDATE_TASK:
    imports.append("schedule.update_api_token_last_used_task")
    beat_schedule["batch_update_api_token_last_used"] = {
        "task": "schedule.update_api_token_last_used_task.batch_update_api_token_last_used",
        "schedule": timedelta(minutes=dify_config.API_TOKEN_LAST_USED_UPDATE_INTERVAL),
    }
```

**解读**：
- 部分任务用 `timedelta` 而不是 `crontab`，因为间隔是**配置驱动**（用户可调）
- **`schedule.workflow_schedule_task`**：轮询用户配置的工作流定时（用户自己设的 cron）
- **`trigger_provider_refresh`**：刷新触发器提供商
- **`batch_update_api_token_last_used`**：批量更新 API token 最后使用时间

### 3.4 导入列表

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
**核心代码**（行 153-159）：

```python
imports = [
    "tasks.async_workflow_tasks",  # trigger workers
    "tasks.trigger_processing_tasks",  # async trigger processing
    "tasks.generate_summary_index_task",  # summary index generation
    "tasks.regenerate_summary_index_task",  # summary index regeneration
    "tasks.app_generate.resume_agent_app_task",  # ENG-635: Agent v2 chat ask_human resume
]
```

**解读**：
- Celery 必须显式 import 任务模块才能注册
- 定时任务的导入和正常任务的导入**共用**一个列表
- 新加任务需要同时加到 `imports` 列表和 `beat_schedule`

## 4. 关键要点总结

- Beat 是**独立调度进程**，不执行任务
- 调度方式：`float` / `timedelta` / `crontab`
- **Beat 必须单实例**，否则重复触发
- 调度表可配置化（按 `ENABLE_*` 开关启用）
- dify 有 10+ 个定时任务，覆盖清理、监控、刷新

## 5. 练习题

### 练习 1：基础（必做）

配置 3 个定时任务：每小时清理缓存、每天凌晨备份、每 5 分钟检查订单。

### 练习 2：进阶

写一个监控脚本，列出当前 Beat 触发的所有任务和下次执行时间。

### 练习 3：挑战（选做）

阅读 `extensions/ext_celery.py` 完整 Beat schedule，理解为什么 dify 把清理任务安排在凌晨 2-4 点而不是白天。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_celery.py`（第 153-260 行）
- Celery Beat 文档：https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
- crontab 语法：https://crontab.guru/

---

**文档版本**：v1.0
**最后更新**：2026-07-13