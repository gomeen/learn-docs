# 14 自动填充：MetaObjectHandler

> 自动填充是 MP 的杀手级特性，让 `createTime/updateTime/creator/updater` 无需手动赋值。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `MetaObjectHandler` 的工作原理
- 掌握 `@TableField(fill = ...)` 的四个阶段
- 知道 ruoyi 如何实现「自动设置当前登录用户」
- 能在自己的项目中实现类似能力

## 📚 前置知识

- 09-mybatis-vs-mp.md
- Java 反射（MetaObject）
- Spring Security 上下文（基础）

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

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 DefaultDBFieldHandler 实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/handler/DefaultDBFieldHandler.java`

```java
public class DefaultDBFieldHandler implements MetaObjectHandler {

    @Override
    public void insertFill(MetaObject metaObject) {
        if (Objects.nonNull(metaObject) && metaObject.getOriginalObject() instanceof BaseDO) {
            BaseDO baseDO = (BaseDO) metaObject.getOriginalObject();

            LocalDateTime current = LocalDateTime.now();
            // 创建时间为空，则以当前时间为插入时间
            if (Objects.isNull(baseDO.getCreateTime())) {
                baseDO.setCreateTime(current);
            }
            // 更新时间为空，则以当前时间为更新时间
            if (Objects.isNull(baseDO.getUpdateTime())) {
                baseDO.setUpdateTime(current);
            }

            Long userId = SecurityFrameworkUtils.getLoginUserId();
            // 当前登录用户不为空，创建人为空，则当前登录用户为创建人
            if (Objects.nonNull(userId) && Objects.isNull(baseDO.getCreator())) {
                baseDO.setCreator(userId.toString());
            }
            // 当前登录用户不为空，更新人为空，则当前登录用户为更新人
            if (Objects.nonNull(userId) && Objects.isNull(baseDO.getUpdater())) {
                baseDO.setUpdater(userId.toString());
            }
        }
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        // 更新时间为空，则以当前时间为更新时间
        Object modifyTime = getFieldValByName("updateTime", metaObject);
        if (Objects.isNull(modifyTime)) {
            setFieldValByName("updateTime", LocalDateTime.now(), metaObject);
        }

        // 当前登录用户不为空，更新人为空，则当前登录用户为更新人
        Object modifier = getFieldValByName("updater", metaObject);
        Long userId = SecurityFrameworkUtils.getLoginUserId();
        if (Objects.nonNull(userId) && Objects.isNull(modifier)) {
            setFieldValByName("updater", userId.toString(), metaObject);
        }
    }
}
```

**解读**：
- 第 3 行：**类型检查**——只有 `BaseDO` 及其子类才填充（避免误伤其他实体）
- 第 9-14 行：使用 setter 而非 `strictInsertFill`，更直接
- 第 17 行：`SecurityFrameworkUtils.getLoginUserId()` —— 从 Spring Security 上下文取当前用户 ID
- 第 19-23 行：用户为空时跳过（如：定时任务无登录用户）
- 第 29-33 行（update）：用 `getFieldValByName/setFieldValByName` 操作 MetaObject（不强制转为 BaseDO，更通用）
- **设计意图**：避免「强制覆盖」——用户已设置的值不被自动填充覆盖，提供更大灵活性

### 3.2 BaseDO 字段定义

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/dataobject/BaseDO.java`

```java
public abstract class BaseDO implements Serializable, TransPojo {

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableField(fill = FieldFill.INSERT, jdbcType = JdbcType.VARCHAR)
    private String creator;

    @TableField(fill = FieldFill.INSERT_UPDATE, jdbcType = JdbcType.VARCHAR)
    private String updater;

    @TableLogic
    private Boolean deleted;

    public void clean() {
        this.creator = null;
        this.createTime = null;
        this.updater = null;
        this.updateTime = null;
    }
}
```

**解读**：
- 第 11、14 行：`jdbcType = JdbcType.VARCHAR` —— creator/updater 是 String（不是 Long），对应 VARCHAR 字段
- 第 17 行：`@TableLogic` —— 启用逻辑删除
- 第 21-26 行：`clean()` 方法 —— 用于「前端传来的 VO 转 DO 时，清掉这些字段，避免被恶意覆盖」

## 4. 关键要点总结

- `MetaObjectHandler` 是 MP 自动填充的入口
- ruoyi 通过 `BaseDO` 让所有实体类继承 → 自动具备 5 个通用字段
- 自动填充应**避免强制覆盖**（用户手动设置的值优先）
- `SecurityFrameworkUtils.getLoginUserId()` 是 ruoyi 获取当前用户的方式
- 定时任务等无用户上下文场景，creator/updater 会保持 null

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `AuditMetaObjectHandler`，在插入时自动填充 `createTime/updateTime/creator/updater` 四个字段，并在 Service 中插入一条数据验证自动填充是否生效。

### 练习 2：进阶

阅读 `DefaultDBFieldHandler` 的 `updateFill` 方法，对比 `insertFill` 有什么区别？为什么 `updateFill` 不强制转换 `metaObject.getOriginalObject()` 为 `BaseDO`？

### 练习 3：挑战（选做）

扩展自动填充能力：实现「多租户自动注入 `tenant_id`」（从 `TenantContextHolder.getTenantId()` 获取）。要求：插入时如果 tenant_id 为空，自动填充；更新时不修改 tenant_id。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/handler/DefaultDBFieldHandler.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/dataobject/BaseDO.java`
- MyBatis Plus 字段自动填充：https://baomidou.com/pages/4c6bcf/

---

**文档版本**：v1.0
**最后更新**：2026-07-13