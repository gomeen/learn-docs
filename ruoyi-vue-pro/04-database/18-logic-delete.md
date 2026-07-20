# 15 逻辑删除：@TableLogic

> 逻辑删除让「删除」变成「标记」，避免误删后无法恢复。ruoyi 全量启用逻辑删除。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分物理删除 vs 逻辑删除
- 掌握 `@TableLogic` 的配置方式
- 理解逻辑删除对查询的影响
- 知道何时应该用物理删除（如：审计要求、GDPR）

## 📚 前置知识

- [11-mybatis-vs-mp.md](./11-mybatis-vs-mp.md)
- [17-auto-fill.md](./17-auto-fill.md)

## 1. 核心概念

### 1.1 两种删除方式

| 方式 | 操作 | 可恢复性 | 典型场景 |
|------|------|---------|---------|
| 物理删除 | `DELETE FROM ...` | 不可恢复 | 日志清理、GDPR 删除 |
| 逻辑删除 | `UPDATE ... SET deleted = 1` | 可恢复（改回 deleted = 0） | 业务数据 |

### 1.2 @TableLogic 工作机制

```sql
-- MP 自动转换：
DELETE FROM user WHERE id = 1;
-- 实际执行：
UPDATE user SET deleted = 1 WHERE id = 1 AND deleted = 0;

SELECT * FROM user WHERE id = 1;
-- 实际执行：
SELECT * FROM user WHERE id = 1 AND deleted = 0;
```

### 1.3 ruoyi 的全局逻辑删除

```java
// BaseDO 中定义
@TableLogic
private Boolean deleted;

// 配置默认值（在 application.yml 中）：
mybatis-plus:
  global-config:
    db-config:
      logic-delete-field: deleted    # 全局字段名
      logic-delete-value: 1           # 已删除值
      logic-not-delete-value: 0       # 未删除值
```

**效果**：所有继承 `BaseDO` 的实体无需再写 `@TableLogic`，全局生效。

## 2. 代码示例

### 2.1 实体类配置

```java
@Data
public class UserDO {
    @TableId
    private Long id;
    private String username;

    // 方式一：注解配置（默认值）
    @TableLogic
    private Integer deleted;

    // 方式二：自定义删除值
    // @TableLogic(value = "is_active", delval = "false", normalval = "true")
    // private Boolean isActive;
}
```

### 2.2 MySQL 表结构

```sql
CREATE TABLE user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    deleted BIT(1) NOT NULL DEFAULT b'0' COMMENT '是否删除（0否 1是）'
);
```

### 2.3 使用示例

```java
// 删除 → 实际是 UPDATE
userMapper.deleteById(1L);
// SQL: UPDATE user SET deleted = 1 WHERE id = 1 AND deleted = 0

// 查询 → 自动加 WHERE deleted = 0
User u = userMapper.selectById(1L);
// SQL: SELECT * FROM user WHERE id = 1 AND deleted = 0

// 想查全部（含已删除）→ 使用自定义 SQL
@Select("SELECT * FROM user WHERE id = #{id}")
User selectByIdIncludeDeleted(@Param("id") Long id);

// 批量删除
userMapper.deleteByIds(Arrays.asList(1L, 2L, 3L));
// SQL: UPDATE user SET deleted = 1 WHERE id IN (1,2,3) AND deleted = 0
```

## 3. 关键要点总结

- 逻辑删除 = `UPDATE deleted = 1`，保留数据可恢复
- `@TableLogic` 让查询自动加 `WHERE deleted = 0`
- ruoyi 通过 `BaseDO` 全量启用逻辑删除，**无需每个实体单独配置**
- 物理删除场景：日志清理、GDPR 合规、数据归档
- 唯一索引设计要小心逻辑删除（多个「已删除」行会有相同唯一键）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
