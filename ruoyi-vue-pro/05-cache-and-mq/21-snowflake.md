# 4.2 分布式 ID：Snowflake

> 理解分布式 ID 的常见方案，掌握 Snowflake 算法的原理和 ruoyi 的实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解分布式 ID 的需求（分库分表、高并发）
- 掌握常见方案：UUID、DB 自增、Snowflake
- 深入理解 Snowflake 算法的 64 位结构
- 看懂 ruoyi 中 Hutool 封装的 Snowflake 用法

## 📚 前置知识

- 二进制位运算
- Java 基础

## 1. 核心概念

### 1.1 为什么需要分布式 ID？

- 单库自增 ID 性能瓶颈（DB 锁）
- 分库分表后，自增 ID 不再全局唯一
- 需要**全局唯一、趋势递增、高性能**的 ID

### 1.2 常见方案对比

| 方案 | 长度 | 优点 | 缺点 |
|------|------|------|------|
| UUID | 128 位 | 简单、本地生成 | 长、无序、不可读 |
| DB 自增 | 8 字节 | 趋势递增 | DB 性能瓶颈 |
| Snowflake | 8 字节 | 高性能、趋势递增 | 时钟回拨问题 |
| Redis INCR | 8 字节 | 高性能 | 依赖 Redis |

### 1.3 Snowflake 结构（64 位）

```
0 | 0000000 00000000 00000000 00000000 00000000 0 | 00000 | 00000 | 000000000000
^                                                       ^         ^        ^
符号位(1)                                          时间戳(41)  数据中心(5) 机器(5) 序列号(12)
```

- 1 位符号：固定为 0
- 41 位时间戳：毫秒级，可用约 69 年
- 5 位数据中心：32 个
- 5 位机器标识：32 个
- 12 位序列号：每毫秒每机器 4096 个

## 2. 代码示例

### 2.1 Hutool Snowflake（ruoyi 实际使用）

```java
// 文件：SnowflakeDemo.java
import cn.hutool.core.lang.Snowflake;
import cn.hutool.core.net.NetUtil;
import cn.hutool.core.util.IdUtil;

public class SnowflakeDemo {
    public static void main(String[] args) {
        // 0=数据中心，1=机器ID（可基于 IP 自动算）
        long workerId = NetUtil.ipv4ToLong(NetUtil.getLocalhostStr()) & 31;
        long datacenterId = 1L;

        Snowflake snowflake = IdUtil.getSnowflake(workerId, datacenterId);
        long id = snowflake.nextId();
        System.out.println("ID: " + id);  // 18 位数字
    }
}
```

### 2.2 纯算法实现

```java
public class Snowflake {
    private final long twepoch = 1288834974657L;
    private final long workerIdBits = 5L;
    private final long datacenterIdBits = 5L;
    private final long sequenceBits = 12L;
    private long sequence = 0L;
    private long lastTimestamp = -1L;

    public synchronized long nextId() {
        long timestamp = timeGen();
        if (timestamp < lastTimestamp) {
            throw new RuntimeException("时钟回拨");
        }
        if (timestamp == lastTimestamp) {
            sequence = (sequence + 1) & 4095;
            if (sequence == 0) timestamp = tilNextMillis(lastTimestamp);
        } else {
            sequence = 0L;
        }
        lastTimestamp = timestamp;

        return ((timestamp - twepoch) << 22)
                | (datacenterId << 17)
                | (workerId << 12)
                | sequence;
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 使用 Hutool Snowflake

ruoyi 通过 Hutool 的 `IdUtil.getSnowflake()` 使用 Snowflake，未自行实现。

**核心依赖**：`cn.hutool:hutool-core`

### 3.2 ruoyi 的 ID 应用场景

ruoyi 在以下场景使用 Snowflake：
- **订单号**：`pay_order`、`trade_order` 主键
- **日志编号**：操作日志、登录日志的唯一 ID
- **支付回调**：回调请求唯一标识
- **WebSocket session ID**

### 3.3 时钟回拨的应对

Hutool Snowflake 在时钟回拨时会：
- 抛出 `RuntimeException("时间戳比上一次生成 ID 时小")`
- ruoyi 业务层一般通过 **`@Retryable`** 重试或捕获异常后短暂 sleep

生产建议：
- 部署 NTP 时钟同步服务
- 极端情况人工介入

## 4. 关键要点总结

- Snowflake = 1+41+5+5+12 = 64 位
- ruoyi 用 Hutool 的 `IdUtil.getSnowflake()`，未自行实现
- 时钟回拨是 Snowflake 的核心风险
- 适合：订单、日志、消息等需要趋势递增 ID 的场景

## 5. 练习题

### 练习 1：基础（必做）

调用 `IdUtil.getSnowflake(1, 1).nextId()` 生成 3 个 ID，观察它们的位数和递增性。

### 练习 2：进阶

解释为什么 Snowflake 的 41 位时间戳选 `2^41 - 1` 毫秒 ≈ 69 年这个上限？是怎么算的？

### 练习 3：挑战（选做）

实现一个"防时钟回拨"Snowflake：时钟回拨 N 毫秒内，等待 N 毫秒后继续；超过 N 毫秒抛异常。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/`（Hutool Snowflake 用法，依赖 hutool-core）
- Hutool 文档：https://hutool.cn/docs/#/core/工具类/唯一ID工具类-Snowflake
- Twitter Snowflake 原论文：https://blog.twitter.com/engineering/en_us/a/2010/announcing-snowflake

---

**文档版本**：v1.0
**最后更新**：2026-07-13