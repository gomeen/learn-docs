# 15 逻辑删除：@TableLogic

> 逻辑删除让「删除」变成「标记」，避免误删后无法恢复。ruoyi 全量启用逻辑删除。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分物理删除 vs 逻辑删除
- 掌握 `@TableLogic` 的配置方式
- 理解逻辑删除对查询的影响
- 知道何时应该用物理删除（如：审计要求、GDPR）

## 📚 前置知识

- 09-mybatis-vs-mp.md
- 14-auto-fill.md

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

## 3. ruoyi 仓库源码解读

### 3.1 BaseDO 中的 @TableLogic

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

    /**
     * 是否删除
     */
    @TableLogic
    private Boolean deleted;
}
```

**解读**：
- 第 17 行：`@TableLogic` —— 全表逻辑删除字段
- **设计意图**：所有业务表都有 deleted 字段，行为统一

### 3.2 ruoyi 的删除业务示例

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/RoleServiceImpl.java`

```java
@Override
@Transactional(rollbackFor = Exception.class)
@CacheEvict(value = RedisKeyConstants.ROLE, key = "#id")
public void deleteRole(Long id) {
    // 1. 校验是否可以更新
    RoleDO role = validateRoleForUpdate(id);

    // 2.1 标记删除（实际是 UPDATE deleted = 1）
    roleMapper.deleteById(id);
    // 2.2 删除相关数据
    permissionService.processRoleDeleted(id);
    // ...
}
```

**解读**：
- 第 1 行：`@Transactional` —— 业务级事务
- 第 2 行：`@CacheEvict` —— 删除时清除 Redis 缓存
- 第 7 行：**「标记删除」注释**清晰表达意图（实际是逻辑删除）
- **设计意图**：业务代码不需要知道是物理还是逻辑删除，`roleMapper.deleteById(id)` 屏蔽了实现细节

### 3.3 级联逻辑删除

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`

```java
@Override
@Transactional(rollbackFor = Exception.class)
public void processRoleDeleted(Long roleId) {
    // 标记删除 UserRole
    userRoleMapper.deleteListByRoleId(roleId);
    // 标记删除 RoleMenu
    roleMenuMapper.deleteListByRoleId(roleId);
}
```

**解读**：
- 第 4 行：删除「用户-角色」关联（实际是 update deleted=1）
- 第 6 行：删除「角色-菜单」关联
- **整体设计意图**：删除角色时级联清理关联数据（也是逻辑删除），保证业务数据完整性

## 4. 关键要点总结

- 逻辑删除 = `UPDATE deleted = 1`，保留数据可恢复
- `@TableLogic` 让查询自动加 `WHERE deleted = 0`
- ruoyi 通过 `BaseDO` 全量启用逻辑删除，**无需每个实体单独配置**
- 物理删除场景：日志清理、GDPR 合规、数据归档
- 唯一索引设计要小心逻辑删除（多个「已删除」行会有相同唯一键）

## 5. 练习题

### 练习 1：基础（必做）

新建 User 表（含 deleted 字段），用 MP 实现：
- 插入一条 user
- 逻辑删除它
- 再查询它（应返回 null）
- 直接 SQL 查询它（应能看到 deleted = 1）

### 练习 2：进阶

阅读 `RoleServiceImpl.deleteRole`，追踪完整的级联删除流程：`role` → `role_menu` → `user_role`。说明每个 Mapper 调用实际执行的 SQL。

### 练习 3：挑战（选做）

设计一个「逻辑删除 + 唯一索引」的冲突场景：用户的 username 字段加了唯一索引，用户 A 删除后，用户 B 想用相同 username 注册 —— 会失败。设计方案解决此问题（提示：删除值用时间戳代替 0/1）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/dataobject/BaseDO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/RoleServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
- MyBatis Plus 逻辑删除文档：https://baomidou.com/pages/6b03c5/

---

**文档版本**：v1.0
**最后更新**：2026-07-13