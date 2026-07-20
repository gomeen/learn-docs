# 16 乐观锁：@Version

> 乐观锁是处理并发更新的轻量方案。ruoyi 中部分场景会用到，理解原理对调试并发问题至关重要。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分乐观锁与悲观锁
- 掌握 `@Version` 注解的使用方式
- 理解 MP 乐观锁的实现原理（CAS）
- 能在并发场景下正确应用

## 📚 前置知识

- [11-mybatis-vs-mp.md](./11-mybatis-vs-mp.md)
- Java 并发基础（CAS 详见 [28-atomic](../01-java-fundamentals/34-atomic.md)；本地锁见 [27-lock](../01-java-fundamentals/33-lock.md)）
- [02-mysql-transaction.md](./02-mysql-transaction.md)

## 1. 核心概念

### 1.1 乐观锁 vs 悲观锁

| 类型 | 思路 | 适用场景 | 实现 |
|------|------|---------|------|
| 悲观锁 | 「一定会有并发」 → 先加锁 | 高冲突、写多读少 | `SELECT ... FOR UPDATE` |
| 乐观锁 | 「应该不会有并发」 → 更新时校验 | 低冲突、读多写少 | 版本号 / 时间戳 |

### 1.2 乐观锁原理（CAS）

```
读取：SELECT id, name, version FROM user WHERE id = 1  → version = 0
更新：UPDATE user SET name = 'new', version = 1 WHERE id = 1 AND version = 0
      → 影响行数 = 1？成功
      → 影响行数 = 0？失败（其他线程已更新）
```

### 1.3 ruoyi 中乐观锁的应用

```java
// 启用插件（YudaoMybatisAutoConfiguration）
mybatisPlusInterceptor.addInnerInterceptor(new OptimisticLockerInnerInterceptor());
```

**典型场景**：扣减库存、抢单、版本号敏感的数据更新。

## 2. 代码示例

### 2.1 实体类配置

```java
@Data
public class ProductDO {
    @TableId
    private Long id;
    private String name;
    private Integer stock;

    @Version  // 关键：标记为版本号字段
    private Integer version;
}
```

### 2.2 业务代码

```java
// 1. 扣减库存
public boolean deductStock(Long productId, Integer quantity) {
    ProductDO product = productMapper.selectById(productId);
    if (product.getStock() < quantity) {
        return false;
    }

    // 2. 扣减 + 版本号 +1
    product.setStock(product.getStock() - quantity);
    int rows = productMapper.updateById(product);

    // 3. 影响行数 = 0 表示版本冲突
    return rows > 0;
}
```

### 2.3 注册乐观锁插件

```java
@Configuration
public class MybatisConfig {
    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        interceptor.addInnerInterceptor(new OptimisticLockerInnerInterceptor());  // 乐观锁插件
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor());        // 分页插件
        return interceptor;
    }
}
```

### 2.4 SQL 表现

```sql
-- 读取后：version = 0, stock = 100
-- 调用 updateById 后生成的 SQL：
UPDATE product SET name = ?, stock = ?, version = 1
WHERE id = ? AND version = 0
```

## 3. 关键要点总结

- 乐观锁通过 `@Version` 字段 + `OptimisticLockerInnerInterceptor` 实现
- ruoyi 默认不启用乐观锁，悲观锁（`selectOneForUpdate`）更常用
- 乐观锁适合低冲突、读多写少场景
- 悲观锁适合高冲突、写多读少场景
- 秒杀等极端并发场景推荐 Redis 分布式锁

---

**文档版本**：v1.0
**最后更新**：2026-07-13
