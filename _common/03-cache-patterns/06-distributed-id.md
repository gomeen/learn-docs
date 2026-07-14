# 3.6 分布式 ID 生成：Snowflake / Leaf / UUID

> 掌握主流分布式唯一 ID 生成方案的原理与实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 UUID / Snowflake / Leaf / 数据库自增的差异
- 理解 Snowflake 的位分配和时钟回拨问题
- 实现一个简单的 Snowflake 算法
- 在 dify 中找到 ID 生成的实际应用

## 📚 前置知识

- 二进制位运算
- 多线程与分布式时钟
- 数据库主键设计基础

## 1. 核心概念

### 1.1 为什么需要分布式 ID？

**场景**：
- 订单 ID、商品 ID、用户 ID
- 跨数据库、跨表的全局唯一标识
- 需要可排序（时间有序）以便分库分表

**传统数据库自增的问题**：
- 单库表的自增 ID 跨库后重复
- 性能瓶颈（每次插入都要拿锁）
- 暴露业务量（从 ID 推算每日订单数）

### 1.2 ID 生成的核心要求

| 要求 | 含义 |
|------|------|
| **全局唯一** | 整个系统内不重复 |
| **趋势递增** | 大致按时间递增（数据库友好） |
| **高性能** | 单机每秒至少 1 万 |
| **高可用** | 不能因 ID 生成器故障影响业务 |
| **短小精悍** | 占用存储少，索引效率高 |

### 1.3 主流方案对比

| 方案 | 长度 | 趋势递增 | 性能 | 实现复杂度 |
|------|------|---------|------|-----------|
| UUID | 128 位 | 否 | 极高 | 极低 |
| 数据库自增 | 64 位 | 是 | 低（DB 瓶颈） | 低 |
| Snowflake | 64 位 | 是 | 极高 | 中 |
| Leaf（美团） | 64 位 | 是 | 极高 | 高 |
| TinyID（滴滴） | 64 位 | 是 | 极高 | 中 |

### 1.4 Snowflake 算法详解

Twitter 开源的 64 位 ID 生成方案：

```
0 | 0000... | 00000... | 00000... | 0000...
1 | 41 位时间戳 | 10 位机器 | 12 位序列号 |

* 1 位符号位（固定 0）
* 41 位时间戳（毫秒，~69 年）
* 10 位机器 ID（1024 台）
* 12 位序列号（每毫秒每台机器 4096 个）
```

**单台机器**：每毫秒 4096 个 = 每秒 409.6 万
**1024 台集群**：每秒 4 亿+

### 1.5 时钟回拨问题

**Snowflake 依赖系统时间**。如果 NTP 校准后时钟回拨：
- **小回拨**（< 5ms）：等待追上即可
- **大回拨**：可能产生重复 ID，必须拒绝或报警

**解决方案**：
- 等待（最长等待几百毫秒）
- 拒绝 + 报警
- 预留扩展位（用更多 bit 标记不同毫秒）

## 2. 代码示例

### 2.1 UUID 生成

```python
# 文件：example_uuid.py
import uuid

# UUID v4：基于随机数（最常用）
u = uuid.uuid4()
print(u)              # 550e8400-e29b-41d4-a716-446655440000
print(u.bytes)        # b'U\x0e\x84\x00\xe2\x9bA\xd4\xa7\x16DfUD@\x00\x00'
print(u.hex)          # 550e8400e29b41d4a716446655440000
print(str(u))         # 字符串形式

# 紧凑形式（去掉横线）
print(u.hex)          # 32 字符
```

### 2.2 Snowflake 实现

```python
# 文件：example_snowflake.py
import time
import threading


class SnowflakeGenerator:
    """64 位 Snowflake ID 生成器"""

    # 位分配
    EPOCH = 1704067200000     # 自定义起始时间（2024-01-01）
    MACHINE_BITS = 10
    SEQUENCE_BITS = 12

    MAX_MACHINE = -1 ^ (-1 << MACHINE_BITS)      # 1023
    MAX_SEQUENCE = -1 ^ (-1 << SEQUENCE_BITS)    # 4095

    # 位偏移
    MACHINE_SHIFT = SEQUENCE_BITS
    TIMESTAMP_SHIFT = SEQUENCE_BITS + MACHINE_BITS

    def __init__(self, machine_id: int):
        if machine_id < 0 or machine_id > self.MAX_MACHINE:
            raise ValueError(f"machine_id 必须在 0~{self.MAX_MACHINE}")

        self.machine_id = machine_id
        self.sequence = 0
        self.last_timestamp = -1
        self._lock = threading.Lock()

    def _current_ms(self) -> int:
        return int(time.time() * 1000)

    def _wait_next_ms(self, last_ts: int) -> int:
        """等待下一毫秒"""
        ts = self._current_ms()
        while ts <= last_ts:
            time.sleep(0.001)
            ts = self._current_ms()
        return ts

    def next_id(self) -> int:
        """生成下一个 ID"""
        with self._lock:
            ts = self._current_ms()

            # 时钟回拨处理
            if ts < self.last_timestamp:
                raise RuntimeError(f"时钟回拨 {self.last_timestamp - ts} ms，拒绝生成")

            if ts == self.last_timestamp:
                # 同一毫秒内，序列号递增
                self.sequence = (self.sequence + 1) & self.MAX_SEQUENCE
                if self.sequence == 0:
                    # 序列号溢出，等下一毫秒
                    ts = self._wait_next_ms(self.last_timestamp)
            else:
                # 新毫秒，序列号归零
                self.sequence = 0

            self.last_timestamp = ts

            # 组装 64 位 ID
            return (
                ((ts - self.EPOCH) << self.TIMESTAMP_SHIFT)
                | (self.machine_id << self.MACHINE_SHIFT)
                | self.sequence
            )


# 测试
gen = SnowflakeGenerator(machine_id=1)
for i in range(5):
    id = gen.next_id()
    print(f"ID {i}: {id} (hex: {hex(id)})")
    # 输出：64 位整数，约 18-19 位十进制
```

### 2.3 Leaf-segment 思路（数据库号段）

```python
# 文件：example_leaf_segment.py
import threading
import redis

r = redis.Redis(host="localhost", port=6379)


class LeafSegmentGenerator:
    """Leaf-segment：从 Redis 一次拿一段号，用完再拿"""

    SEGMENT_KEY = "leaf:user_id:segment"
    SEGMENT_SIZE = 1000    # 每次拿 1000 个 ID

    def __init__(self, biz_tag: str):
        self.biz_tag = biz_tag
        self._current = 0
        self._max = 0
        self._lock = threading.Lock()

    def _load_segment(self):
        """从 Redis 加载一段号"""
        # INCRBY 拿下一段起点（原子）
        max_id = r.incrby(self.SEGMENT_KEY, self.SEGMENT_SIZE)
        self._current = max_id - self.SEGMENT_SIZE + 1
        self._max = max_id

    def next_id(self) -> int:
        with self._lock:
            if self._current >= self._max:
                self._load_segment()
            self._current += 1
            return self._current


# 测试
gen = LeafSegmentGenerator("user_id")
for i in range(2500):
    id = gen.next_id()
    # 每 1000 次访问 Redis 一次（性能高）
```

### 2.4 常见错误：用 UUID 做数据库主键

```python
# ❌ 反例：用 UUID v4 做主键
user_id = str(uuid.uuid4())  # "550e8400-e29b-41d4-a716-446655440000"

# 问题：
# 1. UUID 是字符串，占用 36 字节（Snowflake 只需 8 字节 long）
# 2. 无序 → B+ 树频繁页分裂，性能差
# 3. 不利于分库分表（无法按时间分片）

# ✅ 正例：用 Snowflake
user_id = snowflake.next_id()  # 整数，可排序，8 字节
```

## 3. dify 仓库源码解读

### 3.1 dify 使用 UUID（不依赖 Snowflake）

**说明**：dify 用 PostgreSQL 的 UUID 类型，主键生成策略多样：
- 用 Python `uuid.uuid4()` 生成应用层 ID
- 用数据库自增 ID（部分表）
- 用 ULID（部分新表）

**文件位置**：`/Users/xu/code/github/dify/api/tasks/annotation/add_annotation_to_index_task.py`
**核心代码**（行 18-30）：

```python
@shared_task(queue="dataset", bind=True, max_retries=3, default_retry_delay=60)
def add_annotation_to_index_task(
    annotation_id: str, question: str, tenant_id: str, app_id: str, collection_binding_id: str
):
    """
    Add annotation to index.
    :param annotation_id: annotation id
    :param question: question
    :param tenant_id: tenant id
    :param app_id: app id
    :param collection_binding_id: embedding binding id
    """
```

**解读**：
- 第 2 行 `annotation_id: str, ...`：dify 的 ID 都是**字符串形式**（通常是 UUID）
- **设计选择**：dify 是 SaaS 多租户系统，UUID 隔离租户最简单（不依赖中央 ID 生成器）
- **代价**：UUID 在 PostgreSQL 中虽然是 `uuid` 类型（16 字节），但**无序性导致 B+ 树频繁分裂**——dify 的折中是多租户隔离收益 > 索引性能损失

### 3.2 ruoyi 的多种 ID 策略（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/`
**核心代码**（简化）：

```java
// YudaoIdGenerator.java - 自定义 ID 生成器
@Component
public class YudaoIdGenerator {
    private static final Snowflake SNOWFLAKE = new Snowflake(
        IdUtil.getWorkerId(IdUtil.datacenterId(), 1)
    );

    public static long nextId() {
        return SNOWFLAKE.nextId();
    }

    public static String nextIdStr() {
        return String.valueOf(SNOWFLAKE.nextId());
    }
}

// UserDO.java - 实体使用
@TableName("system_user")
public class UserDO {
    @TableId(type = IdType.ASSIGN_ID)    // MyBatis-Plus 自动用雪花算法
    private Long id;
}
```

**解读**：
- 第 4 行：使用 Hutool 的 `Snowflake` 工具类（基于 Snowflake 算法）
- 第 13 行 `IdType.ASSIGN_ID`：MyBatis-Plus 注解，自动用雪花算法生成 ID
- **与 dify 对比**：ruoyi 用 Snowflake（性能优先），dify 用 UUID（多租户隔离优先）

## 4. 关键要点总结

- **UUID**：实现最简单，但无序且占空间
- **Snowflake**：64 位趋势递增，性能极高，但有时钟回拨问题
- **Leaf-segment**：用数据库号段，性能和可用性平衡
- **选择策略**：
  - 多租户 SaaS → UUID（dify 的选择）
  - 订单/支付核心系统 → Snowflake（ruoyi 的选择）
  - 跨数据库唯一标识 → UUID 或 Snowflake
- **不要用 UUID v4 做 MySQL 主键**（影响性能）

## 5. 练习题

### 练习 1：基础（必做）

实现一个简化版 Snowflake：
1. 41 位时间戳（毫秒）
2. 5 位机器 ID（32 台）
3. 8 位序列号（每毫秒 256 个）
4. 单进程下生成 1000 个 ID，验证唯一性和递增性

### 练习 2：进阶

阅读 `dify/api/tasks/annotation/add_annotation_to_index_task.py`：
- dify 用的是哪种 ID 生成方式？
- 为什么 dify 不用 Snowflake？

### 练习 3：挑战（选做）

设计一个**支持时钟回拨**的 Snowflake 改进版：
1. 检测到回拨后等待追上（最多 5ms）
2. 超过 5ms 则拒绝生成 + 报警
3. 增加"扩展位"用 seq 溢出标记不同毫秒

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/annotation/add_annotation_to_index_task.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/`
- Snowflake 原论文：https://blog.twitter.com/engineering/en_us/algorithms/distributed-systems-snowflake
- 美团 Leaf：https://tech.meituan.com/2019/03/07/leaf-id.html

---

**文档版本**：v1.0
**最后更新**：2026-07-14