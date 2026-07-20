# 4.3.5 定时任务：Celery Beat 调度

> Celery Beat 是 Celery 的定时任务调度器，可以定时执行清理、备份、统计等任务。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 Celery Beat 配置定时任务
- 掌握 crontab / timedelta / solar 调度
- 部署 Beat 时的注意事项（单实例、高可用）
- 理解 dify 的定时任务清单

## 📚 前置知识

- Celery 基础（详见 [Celery 架构](./05-celery-architecture.md)）
- Cron 表达式

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

## 3. 关键要点总结

- Beat 是**独立调度进程**，不执行任务
- 调度方式：`float` / `timedelta` / `crontab`
- **Beat 必须单实例**，否则重复触发
- 调度表可配置化（按 `ENABLE_*` 开关启用）
- dify 有 10+ 个定时任务，覆盖清理、监控、刷新

---

**文档版本**：v1.0
**最后更新**：2026-07-13
