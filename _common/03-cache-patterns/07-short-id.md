# 3.7 全局唯一短 ID 生成方案

> 掌握短 ID（如 YouTube 视频 ID、Bit.ly 短链接）的设计与实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分短 ID 与传统 ID 的设计目标
- 理解 Base62 / Base58 / Hashids 编码方案
- 实现一个短 ID 生成服务
- 在 dify 中找到相关应用

## 📚 前置知识

- [分布式 ID 生成](./06-distributed-id.md)
- Base64 / Hex 编码基础
- 哈希函数（MD5 / SHA，见 [加密哈希](../06-encryption/03-hash.md)）

## 1. 核心概念

### 1.1 为什么需要短 ID？

**场景**：URL 短链、视频 ID、订单号需要**短且可读**。

**对比**：
- UUID：`550e8400-e29b-41d4-a716-446655440000`（36 字符）
- Snowflake：`7000000001234567890`（19 位数字）
- 短 ID：`aB3xY9`（6 字符）——**用户体验好**

**短 ID 的核心要求**：
- **足够短**（6-10 字符）
- **可读**（避免 0/O、1/I/l 等混淆字符）
- **全局唯一**
- **不可预测**（防止遍历攻击）

### 1.2 三大编码方案对比

| 方案 | 字符集 | 长度（64 位数） | 适用 |
|------|-------|----------------|------|
| **Base62** | 0-9a-zA-Z | 11 字符 | 短链、订单号 |
| **Base58** | 去 0OIl 的 58 字符 | 11 字符 | 比特币地址 |
| **Base32** | A-Z2-7 | 13 字符 | 短 ID |

### 1.3 Base62 vs Base58

**Base62**：`0-9a-zA-Z` 共 62 字符
- 优点：密度最高（2 位 ≈ 1 字节）
- 缺点：含易混淆字符（0/O、1/I/l）

**Base58**：去掉 `0OIl` 后 58 字符
- 优点：人类友好（不可读错）
- 缺点：密度略低
- **适用**：比特币地址、GitHub 短哈希

### 1.4 短 ID 的常见生成方式

**方式 1：自增 ID + Base62 编码**
```
DB 自增 1, 2, 3 → base62(1)="1", base62(62)="10", base62(1000000)="4c92"
```

**方式 2：哈希截断**
```
MD5(uuid)[:6] = "aB3xY9"
```

**方式 3：Snowflake + Base62**
```
snowflake_id=7000000001234567890 → base62 = "1Z4Q8nO3aB"
```

### 1.5 防遍历攻击

**短链被遍历的风险**：
- `https://t.cn/1` → 第一个短链
- `https://t.cn/2` → 第二个
- ... 攻击者遍历出所有短链

**解决方案**：
1. **随机 ID**（不用自增）
2. **加盐哈希**（同一长链生成不同短链）
3. **访问限流**（单位 IP 的访问次数）
4. **验证码**（敏感操作）

## 2. 代码示例

### 2.1 Base62 编解码

```python
# 文件：example_base62.py
import string

BASE62_ALPHABET = string.digits + string.ascii_letters    # "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def base62_encode(num: int) -> str:
    """整数转 Base62 字符串"""
    if num == 0:
        return BASE62_ALPHABET[0]

    result = []
    while num:
        num, remainder = divmod(num, 62)
        result.append(BASE62_ALPHABET[remainder])

    return "".join(reversed(result))


def base62_decode(s: str) -> int:
    """Base62 字符串转整数"""
    num = 0
    for char in s:
        num = num * 62 + BASE62_ALPHABET.index(char)
    return num


# 测试
for i in [0, 1, 61, 62, 1000000, 2**63 - 1]:
    encoded = base62_encode(i)
    decoded = base62_decode(encoded)
    print(f"{i:>20} → {encoded:>15} → {decoded}")
    assert decoded == i
```

### 2.2 短链服务

```python
# 文件：example_short_url.py
import redis
import hashlib

r = redis.Redis(host="localhost", port=6379)


class ShortUrlService:
    def __init__(self):
        self.counter_key = "short_url:counter"      # 自增 ID
        self.url_key = "short_url:url:"             # 短链 → 长链
        self.reverse_key = "short_url:reverse:"     # 长链 → 短链（防重复）

    def shorten(self, long_url: str) -> str:
        """生成长链的短链"""
        # 1. 检查是否已存在
        existing = r.get(f"short_url:reverse:{hashlib.md5(long_url.encode()).hexdigest()}")
        if existing:
            return existing.decode()

        # 2. 用 INCR 生成自增 ID
        short_id = r.incr(self.counter_key)

        # 3. 转 Base62
        short_code = base62_encode(short_id)

        # 4. 双向存储
        r.setex(f"short_url:url:{short_code}", 86400 * 30, long_url)
        r.setex(f"short_url:reverse:{hashlib.md5(long_url.encode()).hexdigest()}", 86400 * 30, short_code)

        return short_code

    def expand(self, short_code: str) -> str | None:
        """短链还原成长链"""
        return r.get(f"short_url:url:{short_code}")


# 测试
service = ShortUrlService()
short = service.shorten("https://www.example.com/very/long/path/to/article?id=12345")
print(f"短链: https://t.cn/{short}")     # 短链只有 6-7 字符

long_url = service.expand(short)
print(f"还原: {long_url}")
```

### 2.3 防遍历的随机短链

```python
# 文件：example_secure_short.py
import secrets
import redis

r = redis.Redis(host="localhost", port=6379)


def generate_secure_short_code(length: int = 7) -> str:
    """生成密码学安全的随机短链（防遍历）"""
    # Base58 字符集（去掉 0OIl 避免误读）
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

    while True:
        # 用 secrets 模块生成密码学安全的随机串
        code = "".join(secrets.choice(alphabet) for _ in range(length))

        # 检查是否已存在（防碰撞）
        if not r.exists(f"short_url:url:{code}"):
            return code


def shorten_secure(long_url: str) -> str:
    """安全的短链生成（不可遍历）"""
    code = generate_secure_short_code()
    r.setex(f"short_url:url:{code}", 86400 * 30, long_url)
    return code


# 测试
short = shorten_secure("https://www.example.com/article/1")
print(f"短链: {short}")    # 如 "aB3xY9k"
```

### 2.4 常见错误：用自增 ID 做短链（可遍历）

```python
# ❌ 反例：自增短链
short_code = base62_encode(r.incr("counter"))

# 问题：攻击者从 1 开始遍历，窃取所有短链

# ✅ 正例：随机短链 + 防遍历
short_code = generate_secure_short_code()  # 7 位随机 Base58
# 或：用 Snowflake ID + Base62（不可预测但可排序）
```

## 3. dify 仓库源码解读

### 3.1 dify 的 ID 生成（UUID 为主）

**说明**：dify 主要是 SaaS 后端 + API 服务，对外暴露的是 **UUID 形式的 ID**（如 `app_id`、`workflow_id`），不需要短链。

**文件位置**：`/Users/xu/code/github/dify/api/tasks/workflow_execution_tasks.py`
**核心代码**（行 24-33）：

```python
@shared_task(queue="workflow_storage", bind=True, max_retries=3, default_retry_delay=60)
def save_workflow_execution_task(
    self,
    execution_data: dict[str, Any],
    tenant_id: str,
    app_id: str,
    triggered_from: str,
    creator_user_id: str,
    creator_user_role: str,
) -> bool:
```

**解读**：
- 第 4-10 行：`tenant_id`、`app_id`、`creator_user_id` 都是**字符串形式**（UUID）
- **设计哲学**：dify 是面向开发者 / 企业用户的 API 系统，**UUID 的可读性不重要**，多租户隔离和不可预测更重要
- **短 ID 的缺失场景**：dify 没有公开"短链"功能（短链主要是 toC 应用需要）

### 3.2 ruoyi 的短 ID 应用（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
**核心代码**（简化）：

```java
// CodeGenerator.java - 业务代码生成器（短 ID 应用）
@Service
public class CodeGenerator {
    @Resource
    private StringRedisTemplate redisTemplate;

    public String generateCode(String bizType) {
        // 1. 从 Redis 自增 ID
        Long seq = redisTemplate.opsForValue().increment("code:seq:" + bizType);

        // 2. 拼前缀（如订单号: "SO" + 时间 + 序号）
        String prefix = getPrefixByBizType(bizType);     // "SO" 订单 / "PY" 支付 / "US" 用户
        String datePart = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"));

        // 3. 拼接：SO202407140001（短且可读）
        return prefix + datePart + String.format("%04d", seq);
    }
}
```

**解读**：
- 第 7 行：用 Redis `INCR` 生成序号（不依赖数据库）
- 第 11 行：日期 + 序号组合，每日自动从 1 开始——**自带的限流作用**
- 第 14 行：4 位序号，每天最多 9999 单（不够再扩位）

## 4. 关键要点总结

- **Base62** 是短 ID 的主流编码（密度高）
- **Base58** 适合人类可读场景（比特币地址）
- **短链必须防遍历**：用随机 ID 或 Snowflake（不用纯自增）
- **业务编号设计**：前缀 + 日期 + 序号（如 `SO202407140001`）既可读又能携带业务信息
- dify 用 UUID 而非短 ID（多租户场景）；ruoyi 用前缀+日期+序号的业务编号

## 5. 练习题

### 练习 1：基础（必做）

实现 `base62_encode/decode`：
1. 把 64 位整数编码为 Base62
2. 把 Base62 字符串解码回整数
3. 测试 10 个边界值

### 练习 2：进阶

设计一个**订单号生成器**：
- 格式：`SO` + `yyyyMMdd` + `4 位序号`
- 每天从 1 开始
- 用 Redis `INCR` 实现
- 保证全局唯一

### 练习 3：挑战（选做）

设计一个**支持高并发的短链服务**：
1. 短链 7 位 Base58（62^7 = 3.5 万亿空间）
2. 写入吞吐 1 万 QPS
3. 防遍历、防碰撞
4. 画出架构图

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/workflow_execution_tasks.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- Base62 实现细节：https://en.wikipedia.org/wiki/Base62
- YouTube ID 设计：https://web.archive.org/web/20210309031848/https://www.youtu.be/watch?v=g4wT2K1J1-4

---

**文档版本**：v1.0
**最后更新**：2026-07-14