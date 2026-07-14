# 16 乐观锁：@Version

> 乐观锁是处理并发更新的轻量方案。ruoyi 中部分场景会用到，理解原理对调试并发问题至关重要。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分乐观锁与悲观锁
- 掌握 `@Version` 注解的使用方式
- 理解 MP 乐观锁的实现原理（CAS）
- 能在并发场景下正确应用

## 📚 前置知识

- 09-mybatis-vs-mp.md
- Java 并发基础
- 02-mysql-transaction.md

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

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的乐观锁使用现状

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`

```java
@Bean
public MybatisPlusInterceptor mybatisPlusInterceptor() {
    MybatisPlusInterceptor mybatisPlusInterceptor = new MybatisPlusInterceptor();
    mybatisPlusInterceptor.addInnerInterceptor(new PaginationInnerInterceptor()); // 分页插件
    // ↓↓↓ 按需开启，可能会影响到 updateBatch 的地方：例如说文件配置管理 ↓↓↓
    // mybatisPlusInterceptor.addInnerInterceptor(new BlockAttackInnerInterceptor()); // 拦截没有指定条件的 update 和 delete 语句
    return mybatisPlusInterceptor;
}
```

**解读**：
- 当前 ruoyi 默认**只开启分页插件**，**乐观锁插件未默认开启**
- 设计原因：乐观锁的「`updateById` 返回 0」语义可能被忽略，导致业务不知道更新失败
- **使用建议**：在「库存扣减、金额变更」等高并发场景下，开发者自行引入 OptimisticLockerInnerInterceptor

### 3.2 业务场景：库存扣减（推荐用悲观锁）

```java
// 在事务内使用 selectOneForUpdate 悲观锁（BaseMapperX 提供）
@Override
@Transactional(rollbackFor = Exception.class)
public boolean deductStock(Long productId, Integer quantity) {
    // 加行锁（FOR UPDATE）
    ProductDO product = productMapper.selectOneForUpdate(ProductDO::getId, productId);
    if (product == null) {
        throw exception(PRODUCT_NOT_EXISTS);
    }
    if (product.getStock() < quantity) {
        throw exception(STOCK_NOT_ENOUGH);
    }
    product.setStock(product.getStock() - quantity);
    productMapper.updateById(product);
    return true;
}
```

**解读**：
- 第 5 行：`selectOneForUpdate` —— 来自 `BaseMapperX` 增强，自动追加 `FOR UPDATE`
- **为什么 ruoyi 用悲观锁更多？**
  - 业务复杂时，悲观锁代码更直白（异常即回滚）
  - 乐观锁的「重试机制」需要业务自己实现
- **乐观锁 vs 悲观锁选择**：
  - 冲突概率低（如：用户修改个人资料）→ 乐观锁
  - 冲突概率高（如：秒杀）→ 悲观锁或 Redis 分布式锁

### 3.3 乐观锁配置示例（在 ruoyi 中启用）

如果需要在 ruoyi 中启用乐观锁，修改 `YudaoMybatisAutoConfiguration.java`：

```java
@Bean
public MybatisPlusInterceptor mybatisPlusInterceptor() {
    MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
    interceptor.addInnerInterceptor(new PaginationInnerInterceptor());
    interceptor.addInnerInterceptor(new OptimisticLockerInnerInterceptor());  // 新增
    return interceptor;
}
```

**注意**：启用乐观锁后，**所有带 `@Version` 字段的实体**，`updateById` 都会自动加 `WHERE version = ?` 条件。

## 4. 关键要点总结

- 乐观锁通过 `@Version` 字段 + `OptimisticLockerInnerInterceptor` 实现
- ruoyi 默认不启用乐观锁，悲观锁（`selectOneForUpdate`）更常用
- 乐观锁适合低冲突、读多写少场景
- 悲观锁适合高冲突、写多读少场景
- 秒杀等极端并发场景推荐 Redis 分布式锁

## 5. 练习题

### 练习 1：基础（必做）

实现 Product 实体（含 `@Version` 字段），开启乐观锁插件，模拟两个线程同时扣减库存：观察是否有一个更新失败（影响行数 = 0）。

### 练习 2：进阶

为什么 ruoyi 默认不开启乐观锁插件？搜索 `BlockAttackInnerInterceptor` 注释（`YudaoMybatisAutoConfiguration.java`）思考乐观锁可能带来的副作用。

### 练习 3：挑战（选做）

设计「乐观锁 + 重试」机制：在乐观锁更新失败时，自动重试 3 次，每次间隔 50ms。写出完整的 Service 方法（提示：用 `RetryTemplate` 或自己写循环）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/mapper/BaseMapperX.java`
- MyBatis Plus 乐观锁文档：https://baomidou.com/pages/0d93c0/

---

**文档版本**：v1.0
**最后更新**：2026-07-13