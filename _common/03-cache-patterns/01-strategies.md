# 3.1 缓存策略：Cache-Aside / Read-Through / Write-Through / Write-Behind

> 理解四大经典缓存策略的读写路径及适用场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Cache-Aside / Read-Through / Write-Through / Write-Behind 四大策略
- 画出每种策略的读写时序图
- 为不同业务场景选择合适的策略
- 在 dify 中找到缓存策略的实际应用

## 📚 前置知识

- 缓存基本概念（命中率、过期时间）
- 数据库事务与一致性基础
- [Redis 数据结构](../01-redis/01-data-structures.md)（推荐）

## 1. 核心概念

### 1.1 为什么缓存策略重要？

缓存不是"存进去、读出来"这么简单。**读写顺序**决定了：
- 数据一致性
- 系统复杂度
- 性能特性

### 1.2 Cache-Aside（旁路缓存）——最常用

**读流程**：
```
1. 应用先读缓存
2. 命中 → 返回
3. 未命中 → 读 DB
4. 把 DB 数据写入缓存
5. 返回数据
```

**写流程**：
```
1. 更新 DB
2. 删除缓存（不是更新！）
3. 下次读时按读流程重新加载
```

**特点**：
- **应用层控制**：缓存只做"加速器"，不参与写逻辑
- **失效而非更新**：写 DB 后删缓存，避免并发写导致脏数据
- **适用场景**：绝大多数业务（dify 的 feature service）

### 1.3 Read-Through（读穿透）

**读流程**：
```
1. 应用读缓存
2. 命中 → 返回
3. 未命中 → 缓存层自己读 DB 加载（应用不感知）
4. 返回数据
```

**与 Cache-Aside 的区别**：
- Cache-Aside：应用读 DB 加载
- Read-Through：缓存层读 DB 加载（**封装在缓存库内**）

### 1.4 Write-Through（写穿透）

**写流程**：
```
1. 应用写缓存
2. 缓存层同步写 DB（应用不感知）
3. 返回写入成功
```

**特点**：
- **缓存和 DB 强一致**：写完缓存 = 写完 DB
- **慢**：每次写都等 DB 确认
- **读性能好**：缓存总是最新的

### 1.5 Write-Behind（异步写回）

**写流程**：
```
1. 应用写缓存
2. 立即返回成功
3. 缓存层异步批量写 DB（积攒一波再写）
```

**特点**：
- **极快**：应用感知不到 DB 延迟
- **可能丢数据**：缓存宕机则未落库的数据丢失
- **适用场景**：读写比例悬殊、可容忍少量丢失（计数器、浏览数）

### 1.6 五大策略对比

| 策略 | 读性能 | 写性能 | 一致性 | 复杂度 |
|------|-------|-------|-------|-------|
| **Cache-Aside** | 高 | 高 | 最终一致 | 低 |
| **Read-Through** | 高 | 高 | 最终一致 | 中 |
| **Write-Through** | 高 | 中 | 强一致 | 中 |
| **Write-Behind** | 高 | 极高 | 弱 | 高 |
| **Write-Around** | 中 | 高 | 最终一致 | 低 |

### 1.7 Cache-Aside 的"先更新 DB 再删缓存"为什么安全？

假设两个并发操作：
- **A：写线程**（更新 DB → 删缓存）
- **B：读线程**（读缓存未命中 → 读 DB → 写缓存）

**时序**：
1. B 读缓存未命中
2. B 读 DB（旧值 V1）
3. A 更新 DB 为 V2
4. A 删缓存
5. B 写缓存 V1 ← **脏数据！**

**解决方案**：**延迟双删**——A 删完缓存后，过几秒再删一次。

## 2. 代码示例

### 2.1 Cache-Aside 基础实现

```python
# 文件：example_cache_aside.py
import redis
import time

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

def get_user(user_id: str) -> dict:
    """Cache-Aside 读"""
    cache_key = f"user:{user_id}"

    # 1. 先读缓存
    cached = r.get(cache_key)
    if cached:
        print(f"[Cache HIT] {cached}")
        return eval(cached)

    # 2. 未命中 → 读 DB（模拟）
    user = db_query_user(user_id)   # {"id": user_id, "name": "alice"}

    # 3. 写入缓存，TTL 5 分钟
    r.setex(cache_key, 300, str(user))
    print(f"[Cache MISS] loaded from DB: {user}")
    return user


def update_user(user_id: str, name: str):
    """Cache-Aside 写"""
    # 1. 更新 DB
    db_update_user(user_id, name)

    # 2. 删除缓存（不是更新！）
    r.delete(f"user:{user_id}")
    # 下次读时会重新加载
```

### 2.2 Write-Behind 实现

```python
# 文件：example_write_behind.py
import redis
from collections import defaultdict
import threading
import time

r = redis.Redis(host="localhost", port=6379)
write_buffer = defaultdict(int)    # 待写 DB 的累积
buffer_lock = threading.Lock()

def increment_view(article_id: str):
    """Write-Behind：写缓存，异步落 DB"""
    # 1. 缓存自增（应用立即返回）
    new_count = r.incr(f"article:{article_id}:views")

    # 2. 累积到 write buffer（异步）
    with buffer_lock:
        write_buffer[article_id] += 1

    return new_count


def flush_to_db():
    """后台线程：定期把 write buffer 批量写 DB"""
    while True:
        time.sleep(10)   # 每 10 秒刷一次
        with buffer_lock:
            if not write_buffer:
                continue
            # 批量写入 DB（一条 SQL 搞定）
            rows = [(article_id, count) for article_id, count in write_buffer.items()]
            db_batch_update_views(rows)
            write_buffer.clear()
            print(f"刷盘: {rows}")


# 启动后台刷盘线程
threading.Thread(target=flush_to_db, daemon=True).start()

# 业务调用
for _ in range(100):
    increment_view("article-001")
# 应用立即返回，DB 10 秒后才更新
```

### 2.3 常见错误：先更新缓存再更新 DB

```python
# ❌ 反例：先更新缓存再更新 DB
def update_user_bad(user_id, name):
    r.set(f"user:{user_id}", name)       # 1. 更新缓存
    db_update_user(user_id, name)        # 2. 更新 DB（可能失败）

# 问题：
# 1. DB 更新失败 → 缓存和 DB 不一致
# 2. 并发写时两线程交叉 → 旧值覆盖新值

# ✅ 正例：先更新 DB 再删除缓存
def update_user_good(user_id, name):
    db_update_user(user_id, name)        # 1. 更新 DB
    r.delete(f"user:{user_id}")          # 2. 删缓存（下次读重新加载）
```

## 3. dify 仓库源码解读

### 3.1 dify 的 FeatureService（典型 Cache-Aside 模式）

**文件位置**：`/Users/xu/code/github/dify/api/services/feature_service.py`
**核心代码**（行 188-215）：

```python
class FeatureService:
    @classmethod
    def get_features(cls, tenant_id: str, exclude_vector_space: bool = False) -> FeatureModel:
        features = FeatureModel()
        if exclude_vector_space:
            features.vector_space = None

        cls._fulfill_params_from_env(features)

        if dify_config.BILLING_ENABLED and tenant_id:
            cls._fulfill_params_from_billing_api(
                features,
                tenant_id,
                exclude_vector_space=exclude_vector_space,
            )

        if dify_config.ENTERPRISE_ENABLED:
            features.webapp_copyright_enabled = True
            features.knowledge_pipeline.publish_enabled = True
            cls._fulfill_params_from_workspace_info(features, tenant_id)
```

**解读**：
- **方法命名风格**：`get_features` 不是 `load_features`——表示先尝试从某处取（缓存），取不到再回源
- 第 10-15 行：先调 `_fulfill_params_from_env`（环境变量，**最快的"缓存"**），然后才访问慢的 billing API
- 第 21 行：bill API 是远端服务，是**典型的"DB"角色**——`FeatureService` 把"近端"和"远端"组装成一个对象返回
- **策略应用**：dify 在**应用层**做了多级缓存（环境变量 → 内存对象 → Redis → DB），这是 Cache-Aside 思想的扩展

### 3.2 ruoyi 的 Spring Cache（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
**核心代码**（简化）：

```java
// UserServiceImpl.java - Spring Cache 抽象
@Service
public class UserServiceImpl implements UserService {
    @Resource
    private UserMapper userMapper;

    @Override
    @Cacheable(cacheNames = "user", key = "#userId")
    // ↑ 读流程：先查缓存，未命中 → 执行方法 → 结果入缓存
    public User getUser(Long userId) {
        return userMapper.selectById(userId);
    }

    @Override
    @CachePut(cacheNames = "user", key = "#user.id")
    // ↑ 写流程：执行方法 → 结果入缓存（覆盖）
    public User updateUser(User user) {
        userMapper.updateById(user);
        return user;
    }

    @Override
    @CacheEvict(cacheNames = "user", key = "#userId")
    // ↑ 失效流程：执行方法 → 删除缓存
    public void deleteUser(Long userId) {
        userMapper.deleteById(userId);
    }
}
```

**解读**：
- `@Cacheable` = **Read-Through**（框架自动处理缓存加载）
- `@CachePut` = **Write-Through**（写完 DB 立即更新缓存）
- `@CacheEvict` = **Cache-Aside 失效模式**（先写 DB 再删缓存）
- ruoyi 用 Spring Cache 注解把策略封装，业务代码不感知

## 4. 关键要点总结

- **Cache-Aside** 是最常用的策略（应用层控制）
- **Read/Write-Through** 把读写逻辑封装到缓存库
- **Write-Behind** 性能最高但可能丢数据
- **先更新 DB 再删缓存** 是 Cache-Aside 的标准做法
- 并发写场景考虑 **延迟双删** 避免脏数据
- Spring Cache 的 `@Cacheable` / `@CachePut` / `@CacheEvict` 对应三种策略

## 5. 练习题

### 练习 1：基础（必做）

实现一个简单的 Cache-Aside 工具类 `CacheAside`：
- `get(key)`：先读缓存，未命中读 DB 并加载
- `set(key, value)`：写 DB 后删缓存
- `delete(key)`：直接删缓存

### 练习 2：进阶

阅读 `dify/api/services/feature_service.py` 的 `_fulfill_params_from_env` 和 `_fulfill_params_from_billing_api`，分析 dify 用了几级"缓存"？分别是什么？

### 练习 3：挑战（选做）

设计一个**延迟双删**实现：
1. 写 DB
2. 删缓存
3. 延迟 N 秒后再删一次
4. 解释为什么延迟 N 秒能解决并发脏数据问题

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/feature_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- 缓存模式详解：https://docs.microsoft.com/en-us/azure/architecture/patterns/cache-aside

---

**文档版本**：v1.0
**最后更新**：2026-07-14