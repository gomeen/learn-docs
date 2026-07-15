# 2.2 MyBatis Plus 核心功能

> 掌握 MyBatis Plus 的核心概念与常用 API，能看懂 ruoyi 中所有 MyBatis Plus 相关代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 MyBatis Plus 的核心组件（BaseMapper、IService、Wrapper）
- 掌握 `LambdaQueryWrapper` 链式 API
- 理解 `@TableField`、`@TableLogic`、`@TableName` 等注解（逻辑删除详见 [15-logic-delete](../04-database/15-logic-delete.md)）
- 能在 yudao 中熟练使用 MyBatis Plus 进行 CRUD

## 📚 前置知识

- MyBatis 基础（Mapper.xml 方式；对比见 [09-mybatis-vs-mp](../04-database/09-mybatis-vs-mp.md)）
- Java 8 Lambda 表达式（详见 [08-stream-lambda](../01-java-fundamentals/08-stream-lambda.md)）
- [06-mybatis-starter.md](./06-mybatis-starter.md)

## 1. 核心概念

### 1.1 MyBatis Plus 是什么？

**MyBatis Plus（MP）** 是 MyBatis 的增强工具，在 MyBatis 基础上**只做增强不做改变**。官方口号："为简化开发、提高效率而生"。

### 1.2 核心组件

| 组件 | 作用 |
|------|------|
| `BaseMapper<T>` | 通用 CRUD Mapper 基类 |
| `IService<T>` | 通用 Service 基类 |
| `ServiceImpl<M, T>` | IService 的实现（聚合 Mapper） |
| `Wrapper<T>` | 查询/更新条件包装器 |
| `LambdaQueryWrapper<T>` | Lambda 风格的 Wrapper |
| `Page<T>` | 分页对象 |
| `MetaObjectHandler` | 字段自动填充接口 |

### 1.3 ruoyi 的增强

ruoyi 在 MP 之上做了**三层增强**：
1. `BaseMapperX extends MPJBaseMapper` — 加入多表 Join 能力
2. `LambdaQueryWrapperX` — 加入 `*IfPresent` 系列方法
3. `BaseDO` — 统一 createTime/creator/deleted 字段

## 2. 代码示例

### 2.1 基础 CRUD（MP 原生）

```java
public interface UserMapper extends BaseMapper<UserDO> { }

// 插入
userMapper.insert(userDO);
// 更新（根据 ID）
userMapper.updateById(userDO);
// 删除（根据 ID）
userMapper.deleteById(1L);
// 查询单个
UserDO user = userMapper.selectById(1L);
// 查询列表
List<UserDO> users = userMapper.selectList(null);
// 统计
Long count = userMapper.selectCount(null);
```

### 2.2 条件查询（Lambda Wrapper）

```java
LambdaQueryWrapper<UserDO> wrapper = new LambdaQueryWrapper<>();
wrapper.eq(UserDO::getStatus, 1)
       .like(UserDO::getName, "张")
       .ge(UserDO::getCreateTime, startDate)
       .orderByDesc(UserDO::getId);

List<UserDO> users = userMapper.selectList(wrapper);
```

### 2.3 常见错误

```java
// ❌ 错误：字符串列名，重构时易出错
QueryWrapper<UserDO> w = new QueryWrapper<>();
w.eq("user_name", "zhang");  // 字段名拼错不会报错

// ✅ 正确：Lambda 列名，重构安全
LambdaQueryWrapper<UserDO> w = new LambdaQueryWrapper<>();
w.eq(UserDO::getUserName, "zhang");  // 编译期检查
```

## 3. ruoyi 仓库源码解读

### 3.1 BaseDO 的字段自动填充

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/dataobject/BaseDO.java`
**核心代码**（行 24-66）：

```java
@Data
@JsonIgnoreProperties(value = "transMap")
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

    public void clean(){
        this.creator = null;
        this.createTime = null;
        this.updater = null;
        this.updateTime = null;
    }
}
```

**解读**：
- **`@TableField(fill = FieldFill.INSERT)`** — 插入时自动填充（由 `DefaultDBFieldHandler` 实现）
- **`@TableLogic`** — 逻辑删除标记（MP 自动把 `deleteById` 转成 `UPDATE ... SET deleted = 1`）
- **`clean()` 方法** — 避免前端直接传入 creator 字段后被意外更新
- **使用 String 而非 Long** 的 creator/updater 是为了未来可能存在的非数值情况

### 3.2 DefaultDBFieldHandler

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/handler/DefaultDBFieldHandler.java`
**核心代码**（行 1-50）：

```java
@Slf4j
public class DefaultDBFieldHandler implements MetaObjectHandler {

    @Override
    public void insertFill(MetaObject metaObject) {
        // 1. 创建时间
        fill(metaObject, "createTime", LocalDateTime.now(), LocalDateTime.class);
        // 2. 更新时间
        fill(metaObject, "updateTime", LocalDateTime.now(), LocalDateTime.class);
        // 3. 创建人
        fill(metaObject, "creator", getLoginUserId(), String.class);
        // 4. 更新人
        fill(metaObject, "updater", getLoginUserId(), String.class);
        // 5. 租户编号（如果开启多租户）
        fill(metaObject, "tenantId", getTenantId(), Long.class);
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        fill(metaObject, "updateTime", LocalDateTime.now(), LocalDateTime.class);
        fill(metaObject, "updater", getLoginUserId(), String.class);
        // 租户编号
        fill(metaObject, "tenantId", getTenantId(), Long.class);
    }

    private String getLoginUserId() {
        LoginUser loginUser = SecurityFrameworkUtils.getLoginUser();
        return loginUser != null ? String.valueOf(loginUser.getId()) : null;
    }
}
```

**解读**：
- 实现了 MP 的 `MetaObjectHandler` 接口
- 在 `insertFill` / `updateFill` 中自动填充 5 个基础字段
- **`creator` 来自 `SecurityFrameworkUtils.getLoginUser()`** — 即从 Spring Security 上下文获取当前登录用户
- 这就是 ruoyi 实体类**自动拥有审计字段**的原因

### 3.3 LogicDeleteByIdWithFill 增强

ruoyi 在删除时**同时填充** deleted 和 updateTime / updater：

```java
// MP 默认的 deleteById：
//   UPDATE table SET deleted=1 WHERE id=? AND deleted=0
//
// yudao 增强：
//   UPDATE table SET deleted=1, update_time=NOW(), updater=? WHERE id=? AND deleted=0
```

## 4. 关键要点总结

- **MyBatis Plus = MyBatis + 通用 CRUD + Wrapper + 分页 + 逻辑删除**
- **`@TableField(fill = FieldFill.INSERT)`** + `MetaObjectHandler` 实现自动填充
- **`@TableLogic`** 把物理删除转为逻辑删除
- **Lambda Wrapper** 防止字段名拼写错误
- **ruoyi 通过 `BaseDO` 统一所有实体的基础字段**

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-admin-server 中找 3 个 DO 类，确认它们都继承 `BaseDO` 并查看自动填充的字段。

### 练习 2：进阶

在 `UserMapper` 中加一个方法 `selectByName(String name)`，使用 `LambdaQueryWrapper` 实现。运行测试确认。

### 练习 3：挑战（选做）

写一段代码，验证 `BaseDO.deleted` 字段：调用 `userMapper.deleteById(1L)` 后，再用 `selectById(1L)` 看看返回什么。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/dataobject/BaseDO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/handler/DefaultDBFieldHandler.java`
- MyBatis-Plus 官方文档：https://baomidou.com/
- MyBatis-Plus 字段自动填充：https://baomidou.com/pages/4c6bcf/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
