# 09 MyBatis 与 MyBatis Plus 区别

> ruoyi-vue-pro 核心使用 MyBatis Plus（MP），不是原生 MyBatis。理解差异是入门关键。

## 🎯 学习目标

完成本文档后，你将能够：
- 说出 MyBatis 与 MyBatis Plus 的本质区别
- 理解 MP 的「增强」点
- 知道 MP 在 ruoyi 中承担什么职责
- 选择合适的 ORM 框架

## 📚 前置知识

- MyBatis 基础（可选）
- Java 反射机制（可选，详见 [05-reflection](../01-java-fundamentals/05-reflection.md)）
- Starter 架构见 [06-mybatis-starter](../03-spring-boot-starters/07-mybatis-starter.md)

## 1. 核心概念

### 1.1 MyBatis 是什么？

MyBatis 是一款**半自动化 ORM** 框架：
- 开发者写 SQL，MyBatis 负责参数映射、结果集映射
- 优点：SQL 灵活可控
- 缺点：CRUD 全靠手写 SQL

### 1.2 MyBatis Plus 是什么？

MyBatis Plus（MP）是 MyBatis 的**增强工具**，在 MyBatis 基础上：
- 内置通用 CRUD（`selectById`、`insert`、`updateById`、`deleteById`）
- 内置条件构造器（`QueryWrapper`、`LambdaQueryWrapper`）
- 内置分页插件（`PaginationInnerInterceptor`）
- 内置逻辑删除、乐观锁、自动填充

**本质**：MP 不修改 MyBatis 核心，只是增强。

### 1.3 对比表

| 能力 | MyBatis | MyBatis Plus |
|------|---------|--------------|
| 基础 CRUD | 手写 XML/注解 | 内置（无需 SQL） |
| 条件构造 | 手写 WHERE | `QueryWrapper` 链式调用 |
| 分页 | 手写 LIMIT | `Page` 对象 + 插件 |
| 逻辑删除 | 手写过滤 | `@TableLogic` 自动处理 |
| 性能分析 | 第三方插件 | 内置 `PerformanceInterceptor` |
| 乐观锁 | 手写 | `@Version` 注解 |

## 2. 代码示例

### 2.1 纯 MyBatis：手写 XML

```xml
<!-- UserMapper.xml -->
<mapper namespace="com.example.UserMapper">
    <select id="selectById" resultType="com.example.User">
        SELECT id, name, email FROM user WHERE id = #{id}
    </select>

    <insert id="insert">
        INSERT INTO user(name, email) VALUES(#{name}, #{email})
    </insert>

    <update id="updateById">
        UPDATE user SET name = #{name}, email = #{email} WHERE id = #{id}
    </update>

    <delete id="deleteById">
        DELETE FROM user WHERE id = #{id}
    </delete>
</mapper>
```

### 2.2 MyBatis Plus：内置 CRUD

```java
// 不需要 XML！直接继承 BaseMapper
public interface UserMapper extends BaseMapper<User> {
    // 自动拥有：insert、updateById、selectById、deleteById、selectList、selectCount ...
}

// 使用
userMapper.insert(user);              // 插入
userMapper.updateById(user);          // 更新
userMapper.selectById(1L);            // 查询
userMapper.deleteById(1L);            // 物理删除
```

### 2.3 条件构造器对比

```java
// ❌ 纯 MyBatis：手写 SQL（容易拼错、有 SQL 注入风险）
@Select("SELECT * FROM user WHERE name LIKE CONCAT('%', #{name}, '%') AND status = #{status}")
List<User> selectByConditions(@Param("name") String name, @Param("status") Integer status);

// ✅ MyBatis Plus：链式 + Lambda（编译期类型安全）
List<User> users = userMapper.selectList(
    new LambdaQueryWrapper<User>()
        .like(User::getName, name)
        .eq(User::getStatus, status)
);
```

## 3. 关键要点总结

- MP 是 MyBatis 的**增强**，不是替代品
- ruoyi **100% 使用 MP**，XML 文件仅在复杂 SQL 场景使用
- MP 核心能力：CRUD 通用、条件构造、分页、逻辑删除、乐观锁、自动填充
- 生产环境建议开启 `BlockAttackInnerInterceptor`（防全表更新）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
