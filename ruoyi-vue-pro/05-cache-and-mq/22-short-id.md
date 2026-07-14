# 4.3 全局唯一短 ID 生成

> 理解短 ID 的需求场景，掌握常见短 ID 生成算法和 ruoyi 的实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解短 ID 的应用场景（短链、订单号、邀请码）
- 掌握哈希、随机数、Base62、Redis 自增等方案
- 知道 ruoyi 中如何平衡可读性和唯一性

## 📚 前置知识

- Redis 基础（参见 `01-redis-basics.md`）
- Snowflake（参见 `21-snowflake.md`）
- Base 编码基础

## 1. 核心概念

### 1.1 为什么需要短 ID？

Snowflake ID 是 18 位数字，太长不适合：
- 短链：`https://a.cn/3kZ` vs `https://a.cn/1234567890123456789`
- 订单号：用户口头沟通不方便
- 邀请码：6 位比 18 位更友好

### 1.2 常见短 ID 方案

| 方案 | 长度 | 唯一性 | 可读性 |
|------|------|-------|--------|
| 哈希截断 | 6-8 | 弱（碰撞） | 较差 |
| 随机字符 | 6-8 | 中 | 较好 |
| Base62 编码 | 8-10 | 强 | 较好 |
| Redis 自增 | 8 | 强 | 较好 |
| Snowflake 截断 | 13-15 | 强 | 一般 |

### 1.3 Base62 编码

Base62 = `[0-9a-zA-Z]`，6 位 Base62 = 62^6 ≈ 568 亿种组合。

## 2. 代码示例

### 2.1 短链生成（基于哈希）

```java
public class ShortUrlDemo {
    public static String shortUrl(String longUrl) {
        // 1. MD5 哈希
        String md5 = DigestUtils.md5Hex(longUrl);
        // 2. 取前 8 位
        return md5.substring(0, 8);
    }
}
```

### 2.2 Redis 自增 + Base62

```java
@Resource
private StringRedisTemplate redisTemplate;

public String nextShortId() {
    // 1. Redis 自增
    Long id = redisTemplate.opsForValue().increment("short:id");
    // 2. Base62 编码
    return toBase62(id);
}

private String toBase62(long num) {
    String chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
    StringBuilder sb = new StringBuilder();
    while (num > 0) {
        sb.append(chars.charAt((int) (num % 62)));
        num /= 62;
    }
    return sb.reverse().toString();
}
```

### 2.3 Hutool NanoId

```java
import cn.hutool.core.util.IdUtil;

String id = IdUtil.nanoId();  // 21 字符 URL 安全
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 ID 策略选择

ruoyi 在不同业务用不同 ID 策略：

| 业务 | ID 类型 | 长度 | 备注 |
|------|---------|------|------|
| 用户 ID | Snowflake (Long) | 18 | 主键 |
| 订单号 | 业务编码+时间 | 20+ | 业务可读 |
| 短链 | 哈希截断 | 8 | pay 模块 |
| 操作日志 | Snowflake (Long) | 18 | 主键 |

### 3.2 业务编码 + 时间模式

ruoyi 订单号常见格式：`业务前缀 + yyyyMMddHHmmss + 序列号`

例如：
- `PAY20260713103000001`
- `MALL20260713103000002`

实现：
```java
String orderNo = "PAY" + DateUtil.format(new Date(), "yyyyMMddHHmmss")
    + String.format("%04d", redisTemplate.opsForValue().increment("order:seq"));
```

### 3.3 ruoyi 的短 ID 思想

短 ID 的核心是**业务可读 + 全局唯一**：
- 时间前缀：天然排序
- 业务前缀：人工识别
- 序列号后缀：避免冲突

## 4. 关键要点总结

- 短 ID 适合用户沟通、URL 美化
- Base62 是性价比最高的编码方案
- Redis 自增 + Base62 = 强唯一性 + 高可读性
- ruoyi 业务号采用"业务前缀+时间+序列号"模式

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `longToBase62(123456)`，返回 Base62 字符串。

### 练习 2：进阶

比较 Snowflake 截断 vs Redis 自增+Base62 的差异：
- 性能：哪种 QPS 更高？
- 可用性：哪种更不依赖中心节点？
- 长度：相同位数下哪种能表示更大范围？

### 练习 3：挑战（选做）

设计一个"短链服务"：输入 longUrl，输出 8 字符 shortKey，要求高 QPS、零冲突。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/`（业务 ID 生成策略散落在各业务模块）
- Hutool NanoId：https://hutool.cn/docs/#/core/工具类/唯一ID工具类-NanoId

---

**文档版本**：v1.0
**最后更新**：2026-07-13