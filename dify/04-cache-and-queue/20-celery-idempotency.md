# 4.3.7 任务幂等性设计

> 任务可能因重试、崩溃恢复、并发触发而**重复执行**。幂等性设计保证多次执行结果一致。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解为什么需要幂等性
- 掌握业务幂等的设计模式（唯一约束、状态机、补偿）
- 在 dify 中识别幂等性保障
- 用 Redis / 数据库实现幂等性

## 📚 前置知识

- Celery 任务与重试（详见 [任务定义](./15-celery-tasks.md)、[任务重试](./21-celery-retry.md)）
- 关系数据库事务
- 分布式锁原理（详见 [Redis 分布式锁](../../_common/04-distributed-locks/02-redis-redlock.md)）

## 1. 核心概念

### 1.1 什么是幂等性？

任务多次执行的效果**与一次执行相同**。

```
幂等：f(x) = f(f(x))
非幂等：f(x) = x++（每次调用都 +1）
```

### 1.2 为什么需要幂等？

任务重复执行的场景：
1. **Worker 崩溃**：`acks_late=True` 时任务重新入队
2. **Celery 重试**：网络超时等临时错误自动重试
3. **并发触发**：用户重复点击、API 重试
4. **手动重跑**：运维手动 `celery task rerun`

### 1.3 幂等设计模式

#### 模式 1：业务唯一约束

利用数据库的**唯一索引**：

```sql
CREATE TABLE payments (
    id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36),
    amount DECIMAL(10, 2),
    UNIQUE KEY uk_order (order_id)  -- 同订单只能一笔
);
```

```python
@shared_task
def charge(order_id):
    # 重复执行只插入一条
    payment = Payment(order_id=order_id, amount=99.9)
    db.session.add(payment)
    db.session.commit()  # IntegrityError if duplicate
```

#### 模式 2：状态机检查

```python
@shared_task(bind=True)
def ship_order(self, order_id):
    order = db.get(Order, order_id)
    if order.status == "SHIPPED":
        return  # 已发货，幂等返回
    
    if order.status != "PAID":
        raise ValueError(f"Order not paid: {order_id}")
    
    order.status = "SHIPPED"
    db.session.commit()
```

#### 模式 3：分布式锁

用 Redis SETNX 防止重复执行：

```python
@shared_task(bind=True)
def critical_task(self, key):
    lock_key = f"task_lock:{key}"
    # 抢到锁才执行
    if not redis_client.set(lock_key, "1", nx=True, ex=600):
        return  # 其他 worker 正在处理
    
    try:
        process(key)
    finally:
        redis_client.delete(lock_key)
```

#### 模式 4：补偿 / 反向操作

```python
@shared_task(bind=True)
def transfer(self, from_account, to_account, amount):
    # 用事务保证原子
    with db.session.begin():
        from_a = db.get(Account, from_account, with_for_update=True)
        to_a = db.get(Account, to_account, with_for_update=True)
        
        from_a.balance -= amount
        to_a.balance += amount
```

`with_for_update()` 行级锁，**两个账户同时更新**不会出错。

### 1.4 幂等性 vs 重复消费

| 概念 | 区别 |
|------|------|
| 幂等 | 业务逻辑保证多次执行结果一致 |
| 重复消费 | MQ 场景，需要去重 |

### 1.5 业务幂等 vs 技术幂等

**技术幂等**：`x = 5` 赋值任意次都是 5。
**业务幂等**：扣库存、扣款、发邮件等业务操作的幂等性。

## 2. 代码示例

### 2.1 模式 1：唯一约束（最可靠）

```python
from sqlalchemy import UniqueConstraint

class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True)
    order_id = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    
    __table_args__ = (UniqueConstraint("order_id", name="uk_payment_order"),)

@shared_task(bind=True, max_retries=3)
def process_payment(self, order_id):
    try:
        with db.session.begin():
            payment = Payment(id=uuid4(), order_id=order_id, amount=99.9)
            db.session.add(payment)
        return {"status": "success", "payment_id": payment.id}
    except IntegrityError:
        # 重复执行，幂等返回
        existing = db.query(Payment).filter_by(order_id=order_id).first()
        return {"status": "already_paid", "payment_id": existing.id}
```

### 2.2 模式 2：状态机

```python
class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"

@shared_task
def ship_order(order_id):
    order = db.get(Order, order_id)
    
    if order.status == OrderStatus.SHIPPED:
        return  # 幂等：已发货
    if order.status == OrderStatus.COMPLETED:
        return  # 幂等：已完成
    
    if order.status != OrderStatus.PAID:
        raise ValueError(f"Cannot ship order in status {order.status}")
    
    # 标记发货
    order.status = OrderStatus.SHIPPED
    db.session.commit()
    
    # 发通知
    notify_shipment(order_id)
```

### 2.3 模式 3：Redis 锁

```python
@shared_task(bind=True, max_retries=3)
def generate_report(self, report_id):
    lock_key = f"report_lock:{report_id}"
    
    # 抢锁
    if not redis_client.set(lock_key, "1", nx=True, ex=3600):
        # 其他 worker 正在生成
        return {"status": "in_progress"}
    
    try:
        # 生成报告（耗时操作）
        data = db.query(...)
        pdf = render_pdf(data)
        upload_to_s3(pdf, report_id)
        return {"status": "done"}
    finally:
        redis_client.delete(lock_key)
```

### 2.4 模式 4：版本号（乐观锁）

```python
@shared_task
def update_user_profile(user_id, data):
    user = db.get(User, user_id)
    expected_version = user.version
    
    # 带版本号更新
    result = db.execute(
        update(User)
        .where(User.id == user_id, User.version == expected_version)
        .values(**data, version=User.version + 1)
    )
    
    if result.rowcount == 0:
        # 版本号不匹配，说明其他任务已更新
        raise RetryableError("Concurrent update detected")
```

### 2.5 常见错误：用时间戳防重复

```python
# ❌ 错误：用 `if not exists` 检查不可靠
def process_payment(order_id):
    if db.query(Payment).filter_by(order_id=order_id).first():
        return  # TOCTOU 漏洞！
    payment = Payment(order_id=order_id, ...)
    db.session.add(payment)
    db.session.commit()

# ✅ 正确：依赖数据库唯一约束
```

## 3. dify 仓库源码解读

### 3.1 异步工作流：trigger_log 状态机

**文件位置**：`/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`
**核心代码**（行 188-200）：

```python
except Exception as e:
    # Calculate elapsed time for failed execution
    elapsed_time = (datetime.now(UTC) - start_time).total_seconds()

    # Update trigger log with failure
    trigger_log.status = WorkflowTriggerStatus.FAILED
    trigger_log.error = str(e)
    trigger_log.finished_at = datetime.now(UTC)
    trigger_log.elapsed_time = elapsed_time
    trigger_log_repo.update(trigger_log)

    # Final failure - no retry logic (simplified like RAG tasks)
    session.commit()
```

**解读**：
- 工作流执行失败 → `status = FAILED` + `error` + `elapsed_time`
- **幂等性**：同一个 `trigger_log_id` 被多次处理时：
  - Worker 通过 `get_by_id` 找到 log
  - 已 `SUCCESS` / `FAILED` 状态就跳过
  - 重新执行不会创建新 log
- 失败重试由 `AsyncWorkflowService.reinvoke_trigger()` 创建**新 log**：

### 3.2 重试触发（创建新 log）

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 222-234）：

```python
# Reset log for retry
trigger_log.status = WorkflowTriggerStatus.RETRYING
trigger_log.retry_count += 1
trigger_log.error = None
trigger_log.triggered_at = datetime.now(UTC)
trigger_log_repo.update(trigger_log)
session.commit()

# Re-trigger workflow (this will create a new trigger log)
return cls.trigger_workflow_async(user, trigger_data, session=session)
```

**解读**：
- **重试 = 新 trigger_log**（原 log 标记为 RETRYING + retry_count++）
- 这样可以保留历史记录（旧 log 不被覆盖）
- **幂等性保证**：数据库主键 `id` 唯一，新 log 不影响旧 log

### 3.3 配额预留与回滚

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 138-152）：

```python
# 7. Reserve quota (commit after successful dispatch)
quota_charge = unlimited()
try:
    quota_charge = QuotaService.reserve(QuotaType.WORKFLOW, trigger_data.tenant_id)
except QuotaExceededError as e:
    # Update trigger log status
    trigger_log.status = WorkflowTriggerStatus.RATE_LIMITED
    trigger_log.error = f"Quota limit reached: {e}"
    trigger_log_repo.update(trigger_log)
    session.commit()

    raise WorkflowQuotaLimitError(
        f"Workflow execution quota limit reached for tenant {trigger_data.tenant_id}"
    ) from e
```

**解读**：
- `QuotaService.reserve()` 立即扣配额（**预扣**）
- 任务入队成功 → `quota_charge.commit()` 确认
- 任务入队失败 → `quota_charge.refund()` 退还
- **幂等性**：同一任务重复触发，每次都扣配额，不会"重复扣"吗？
  - 不会：因为每次触发都用**不同 trigger_log**，配额记录也是新的
  - **但要小心**：用户恶意点击 100 次 → 扣 100 次配额（防护：API 层限流）

### 3.4 文档索引任务用 log 状态防重复

**文件位置**：`/Users/xu/code/github/dify/api/tasks/retry_document_indexing_task.py`
**核心代码**（行 49、71、110、118）：

```python
retry_indexing_cache_key = f"document_{document_id}_is_retried"
# ...
redis_client.delete(retry_indexing_cache_key)
```

**解读**：
- 用 Redis key `document_{id}_is_retried` 标记"正在重试"
- 任务成功/失败都 `delete()` 清理
- **简化幂等**：检查 key 存在就跳过
- **不完美**：Redis 故障时 key 可能残留（但**重试是幂等的**，重跑无害）

## 4. 关键要点总结

- **幂等性**：任务多次执行结果一致
- 场景：崩溃恢复、重试、并发触发
- 设计模式：
  1. **唯一约束**（最可靠）
  2. **状态机**（订单状态）
  3. **分布式锁**（短任务防并发）
  4. **补偿**（带版本号更新）
- dify 用 **trigger_log 状态机** 实现幂等
- 配额预扣 + 失败回滚，避免重复扣费

## 5. 练习题

### 练习 1：基础（必做）

实现一个幂等的"扣款"任务：
- 数据库有 `payments` 表，`order_id` 唯一索引
- 重复执行返回已有 payment_id，不重复扣款

### 练习 2：进阶

实现订单状态机：
- PENDING → PAID → SHIPPED → COMPLETED
- `ship_order` 任务只能从 PAID 转 SHIPPED，重复执行幂等

### 练习 3：挑战（选做）

阅读 `services/async_workflow_service.py` 的 `reinvoke_trigger` 方法，画出"重试 → 新 trigger_log"的完整流程。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`（第 188-200 行）
- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`（第 138-234 行）
- `/Users/xu/code/github/dify/api/tasks/retry_document_indexing_task.py`
- 幂等性设计：https://en.wikipedia.org/wiki/Idempotence

---

**文档版本**：v1.0
**最后更新**：2026-07-13