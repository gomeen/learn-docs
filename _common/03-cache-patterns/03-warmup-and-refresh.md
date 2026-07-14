# 3.3 缓存预热与更新

> 掌握缓存预热、异步刷新和数据同步的工程实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 设计合理的缓存预热策略
- 实现异步刷新避免缓存击穿
- 区分主动刷新与被动失效
- 在 dify 中找到类似的实现

## 📚 前置知识

- 缓存策略（`03-cache-patterns/01-strategies.md`）
- 缓存三大问题（`03-cache-patterns/02-three-problems.md`）
- 消息队列基础（`02-mq/01-concepts.md`）

## 1. 核心概念

### 1.1 为什么需要预热？

**冷启动问题**：服务启动时缓存为空，第一个用户请求必然查 DB。
- 高并发场景：DB 瞬间被打爆
- 大数据量场景：首次查询慢（数秒）

**预热**：服务启动前把热数据加载到缓存。

### 1.2 预热的三大场景

| 场景 | 做法 |
|------|------|
| **服务启动预热** | 启动时异步加载热数据到缓存 |
| **定时预热** | 每隔 N 分钟刷新热点数据 |
| **主动加载** | 业务触发时按需加载 |

### 1.3 缓存刷新的三种模式

**被动失效（Lazy Refresh）**：
- 写 DB 时删缓存
- 下次读时按需加载
- **优点**：实现简单
- **缺点**：每次失效后第一个请求较慢

**主动刷新（Active Refresh）**：
- 后台任务定期刷新缓存
- 业务读到的总是新鲜数据
- **优点**：读性能稳定
- **缺点**：可能刷新过期数据（并发写时）

**双写一致性（Dual Write）**：
- 写 DB 同时更新缓存
- 用 MQ 异步同步保证最终一致

### 1.4 服务启动预热的设计

```
启动流程：
1. 应用启动
2. 注册健康检查（/health 返回 503）
3. 加载配置 → 启动 HTTP 监听
4. 异步预热缓存（不阻塞健康检查）
5. 预热完成后 /health 返回 200
6. 接受流量
```

**关键原则**：**预热不影响启动速度**——异步 + 优先级队列。

### 1.5 异步刷新的常见实现

**方式 1：定时任务（Celery Beat）**
- 每 5 分钟触发一次刷新任务
- 适合刷新频率固定的场景

**方式 2：发布订阅（Redis Pub/Sub）**
- 写 DB 时发"数据变更"消息
- 消费者收到后刷新缓存

**方式 3：基于消息队列的事件驱动**
- dify 用 Celery 任务异步刷新（mail-inner-task 等）

## 2. 代码示例

### 2.1 启动预热

```python
# 文件：example_warmup.py
import asyncio
import redis
from concurrent.futures import ThreadPoolExecutor

r = redis.Redis(host="localhost", port=6379)

def warm_up_hot_users():
    """启动时预热：把访问 TOP 1000 用户加载到缓存"""
    hot_user_ids = db_get_top_n_user_ids(n=1000)   # 从 DB 或分析系统获取

    with ThreadPoolExecutor(max_workers=10) as executor:
        for user_id in hot_user_ids:
            executor.submit(_load_user_cache, user_id)

    print(f"预热完成: {len(hot_user_ids)} 个用户")


def _load_user_cache(user_id: str):
    user = db_query_user(user_id)
    if user:
        r.setex(f"user:{user_id}", 3600, str(user))


# 应用启动时调用
async def on_startup():
    """启动钩子"""
    # Step 1: 标记为未就绪
    set_health_status("warming")

    # Step 2: 启动 HTTP 监听（但不接流量）
    start_http_server()

    # Step 3: 异步预热
    asyncio.create_task(asyncio.to_thread(warm_up_hot_users))

    # Step 4: 等待预热完成
    await asyncio.sleep(5)   # 或等待信号

    # Step 5: 标记就绪
    set_health_status("ready")
```

### 2.2 主动刷新（后台定时任务）

```python
# 文件：example_active_refresh.py
from celery import shared_task
from celery.schedules import crontab
import redis

r = redis.Redis(host="localhost", port=6379)


@shared_task
def refresh_hot_items_cache():
    """定时刷新：每 5 分钟执行一次"""
    hot_item_ids = db_get_hot_item_ids()    # 从分析表获取热点

    for item_id in hot_item_ids:
        item = db_query_item(item_id)
        if item:
            # 用逻辑过期：缓存值包含 expire_at
            r.setex(
                f"item:{item_id}",
                3600,
                f"{item.expire_at}#{str(item)}",   # 业务字段 + expire_at
            )

    print(f"刷新完成: {len(hot_item_ids)} 个商品")


# Celery Beat 配置
app.conf.beat_schedule = {
    "refresh-hot-items": {
        "task": "refresh_hot_items_cache",
        "schedule": crontab(minute="*/5"),   # 每 5 分钟
    },
}
```

### 2.3 基于消息队列的失效广播

```python
# 文件：example_invalidation_mq.py
from celery import shared_task
import redis

r = redis.Redis(host="localhost", port=6379)


@shared_task(queue="cache-invalidation")
def invalidate_cache(item_id: str):
    """消费失效消息，删除对应缓存"""
    r.delete(f"item:{item_id}")
    print(f"失效缓存: item:{item_id}")


# 写 DB 后发失效消息
def update_item(item_id: str, data: dict):
    """Cache-Aside：写 DB 后发 MQ 消息失效缓存"""
    db_update_item(item_id, data)
    invalidate_cache.delay(item_id)   # 异步失效
```

### 2.4 常见错误：启动时同步预热阻塞启动

```python
# ❌ 反例：启动时同步预热
def on_startup_bad():
    warm_up_hot_users()   # 同步等待预热完成（10 秒）
    start_http_server()   # 10 秒后才有流量进来

# 问题：
# 1. 启动慢（10 秒不可用）
# 2. 预热失败 → 整个服务起不来

# ✅ 正例：异步预热 + 健康检查
async def on_startup_good():
    start_http_server()
    asyncio.create_task(warm_up_async())   # 异步预热
    # 立即接受流量（缓存慢慢填）
```

## 3. dify 仓库源码解读

### 3.1 dify 的异步邮件任务（典型预热/刷新模式）

**文件位置**：`/Users/xu/code/github/dify/api/tasks/mail_inner_task.py`
**核心代码**（行 45-50）：

```python
@shared_task(queue="mail")
def send_inner_email_task(to: list[str], subject: str, body: str, substitutions: Mapping[str, str]):
    if not mail.is_inited():
        return

    logger.info(click.style(f"Start enterprise mail to {to} with subject {subject}", fg="green"))
```

**解读**：
- **异步刷新思路**：dify 把"发送邮件"这个**耗时且非关键路径**的操作放到 Celery 异步任务
- **为什么不阻塞 HTTP 请求**：用户在 API 层只关心"邮件已加入发送队列"，实际发送在后台
- **预热关联**：Celery Worker 启动时不需要预热——它是**无状态的消费者**，从 MQ 拉任务即可

### 3.2 dify 的 FeatureService 多级预热

**文件位置**：`/Users/xu/code/github/dify/api/services/feature_service.py`
**核心代码**（行 304-309）：

```python
@classmethod
def _fulfill_params_from_env(cls, features: FeatureModel):
    features.can_replace_logo = dify_config.CAN_REPLACE_LOGO
    features.model_load_balancing_enabled = dify_config.MODEL_LB_ENABLED
    features.dataset_operator_enabled = dify_config.DATASET_OPERATOR_ENABLED
    features.education.enabled = dify_config.EDUCATION_ENABLED
```

**解读**：
- 第 2-5 行：从环境变量读取 feature flag——**这是"零延迟预热"**（进程启动时 Python 加载 env）
- **多级缓存策略**：env（最快）→ billing API（最慢），按"是否启用"分层
- **启动预热**：环境变量预热不需要主动操作，是 OS 层面的预热

### 3.3 ruoyi 的 Spring Cache 刷新（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
**核心代码**（简化）：

```java
// DictServiceImpl.java - 数据字典缓存（典型预热场景）
@Service
public class DictServiceImpl {
    @PostConstruct
    public void init() {
        // 应用启动时预热
        refreshCache();
    }

    @Scheduled(fixedRate = 300000)   // 每 5 分钟
    public void refreshCache() {
        List<Dict> dicts = dictMapper.selectList();
        Map<String, Dict> dictMap = dicts.stream()
            .collect(Collectors.toMap(Dict::getType, d -> d));
        redisTemplate.opsForValue().set("system:dict", dictMap, 1, TimeUnit.HOURS);
    }
}
```

**解读**：
- 第 5 行 `@PostConstruct`：应用启动时执行 `refreshCache()`——典型的启动预热
- 第 11 行 `@Scheduled(fixedRate = 300000)`：每 5 分钟自动刷新——典型的主动刷新
- 这种"启动预热 + 定时刷新"的组合是 ruoyi 的标准模式

## 4. 关键要点总结

- **启动预热**：必须**异步**，不能阻塞启动
- **主动刷新**：用定时任务或 MQ 事件，**避免读时延迟**
- **被动失效**：实现简单但首次读慢
- **健康检查**：预热期间返回 503，避免接收未准备的流量
- 多级缓存（env → 本地 → Redis → DB）是性能与一致性的平衡艺术

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `async_warmup(keys: list[str], loader)` 函数：
1. 用 `asyncio.gather` 并发加载所有 key
2. 限制最大并发数为 100
3. 记录每个 key 的加载耗时

### 练习 2：进阶

阅读 `dify/api/services/feature_service.py`，分析 dify 的"预热"策略：
- env → billing → enterprise 三层数据源分别对应什么预热方式？
- 为什么 enterprise 数据是按需加载而不是启动预热？

### 练习 3：挑战（选做）

设计一个**双写一致性**方案：
- 写 DB 时同步发 MQ 消息
- Consumer 收到后更新缓存（不是删缓存）
- 如何处理消费者宕机期间的消息堆积？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/mail_inner_task.py`
- `/Users/xu/code/github/dify/api/services/feature_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- 缓存预热与更新：https://martin.kleppmann.com/2012/10/01/caching-patterns.html

---

**文档版本**：v1.0
**最后更新**：2026-07-14