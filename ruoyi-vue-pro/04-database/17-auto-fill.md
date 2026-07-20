# 14 自动填充：MetaObjectHandler

> 自动填充是 MP 的杀手级特性，让 `createTime/updateTime/creator/updater` 无需手动赋值。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `MetaObjectHandler` 的工作原理
- 掌握 `@TableField(fill = ...)` 的四个阶段
- 知道 ruoyi 如何实现「自动设置当前登录用户」
- 能在自己的项目中实现类似能力

## 📚 前置知识

- [11-mybatis-vs-mp.md](./11-mybatis-vs-mp.md)
- Java 反射（MetaObject，详见 [05-reflection](../01-java-fundamentals/05-reflection.md)）
- Spring Security 上下文（基础，详见 [20-spring-security](../03-spring-boot-starters/24-spring-security.md) / [30-threadlocal](../01-java-fundamentals/36-threadlocal.md)）

## 1. 核心概念

### 1.1 自动填充的四个阶段

| 阶段 | 触发时机 | 典型字段 |
|------|---------|---------|
| `FieldFill.INSERT` | 插入时 | `createTime`, `creator` |
| `FieldFill.UPDATE` | 更新时 | `updateTime`（只更新时） |
| `FieldFill.INSERT_UPDATE` | 插入和更新时 | `updateTime`, `updater` |
| `FieldFill.DEFAULT` | 默认不填充 | - |

### 1.2 MetaObjectHandler 接口

```java
public interface MetaObjectHandler {
    default void insertFill(MetaObject metaObject) { }
    default void updateFill(MetaObject metaObject) { }
}
```

MP 在执行 `insert/update` 时，会回调这两个方法。开发者可在内部读取/修改实体对象的字段。

### 1.3 ruoyi 的 BaseDO 设计

```java
public abstract class BaseDO {
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableField(fill = FieldFill.INSERT)
    private String creator;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private String updater;

    @TableLogic
    private Boolean deleted;
}
```

**所有 DO 继承 `BaseDO`** → 自动具备 5 个通用字段 + 自动填充能力。

## 2. 代码示例

### 2.1 自定义 MetaObjectHandler

```java
@Component
public class MyMetaObjectHandler implements MetaObjectHandler {

    @Override
    public void insertFill(MetaObject metaObject) {
        this.strictInsertFill(metaObject, "createTime", LocalDateTime.class, LocalDateTime.now());
        this.strictInsertFill(metaObject, "creator", String.class, getCurrentUserId());
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        this.strictUpdateFill(metaObject, "updateTime", LocalDateTime.class, LocalDateTime.now());
        this.strictUpdateFill(metaObject, "updater", String.class, getCurrentUserId());
    }

    private String getCurrentUserId() {
        // 从 SecurityContext 等上下文获取
        return "1"; // 示例
    }
}
```

### 2.2 实体类配置

```java
@Data
public class OrderDO {
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableField(fill = FieldFill.INSERT)
    private String creator;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private String updater;

    private String orderNo;
    private BigDecimal amount;
}
```

### 2.3 使用效果

```java
// 创建订单
OrderDO order = new OrderDO();
order.setOrderNo("O20250101001");
order.setAmount(new BigDecimal("100"));
orderMapper.insert(order);
// ✅ 自动填充：createTime=now, creator=userId, updateTime=now, updater=userId
```

## 3. 关键要点总结

- `MetaObjectHandler` 是 MP 自动填充的入口
- ruoyi 通过 `BaseDO` 让所有实体类继承 → 自动具备 5 个通用字段
- 自动填充应**避免强制覆盖**（用户手动设置的值优先）
- `SecurityFrameworkUtils.getLoginUserId()` 是 ruoyi 获取当前用户的方式
- 定时任务等无用户上下文场景，creator/updater 会保持 null

---

**文档版本**：v1.0
**最后更新**：2026-07-13
