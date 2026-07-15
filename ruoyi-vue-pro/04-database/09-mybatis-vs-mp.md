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
- Starter 架构见 [06-mybatis-starter](../03-spring-boot-starters/06-mybatis-starter.md)

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

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 引入 MyBatis Plus 的依赖

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/pom.xml`

```xml
<dependencies>
    <!-- MyBatis Plus 核心 -->
    <dependency>
        <groupId>com.baomidou</groupId>
        <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
    </dependency>
    <!-- MyBatis Plus Join（连表查询） -->
    <dependency>
        <groupId>com.github.yulichang</groupId>
        <artifactId>mybatis-plus-join-boot-starter</artifactId>
    </dependency>
    <!-- dynamic-datasource（多数据源） -->
    <dependency>
        <groupId>com.baomidou</groupId>
        <artifactId>dynamic-datasource-spring-boot3-starter</artifactId>
    </dependency>
</dependencies>
```

**解读**：
- **核心依赖**：`mybatis-plus-spring-boot3-starter`（适配 Spring Boot 3）
- **扩展依赖**：`mybatis-plus-join` —— 支持连表 Join 语法糖
- **多数据源依赖**：`dynamic-datasource` —— ruoyi 实现读写分离的核心
- **设计意图**：以 MP 为核心，扩展多表 Join 和多数据源能力

### 3.2 ruoyi 的 MP 自动配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`

**核心代码**（行 47-59）：

```java
@Bean
public MybatisPlusInterceptor mybatisPlusInterceptor() {
    MybatisPlusInterceptor mybatisPlusInterceptor = new MybatisPlusInterceptor();
    mybatisPlusInterceptor.addInnerInterceptor(new PaginationInnerInterceptor()); // 分页插件
    // ↓↓↓ 按需开启，可能会影响到 updateBatch 的地方：例如说文件配置管理 ↓↓↓
    // mybatisPlusInterceptor.addInnerInterceptor(new BlockAttackInnerInterceptor()); // 拦截没有指定条件的 update 和 delete 语句
    return mybatisPlusInterceptor;
}

@Bean
public MetaObjectHandler defaultMetaObjectHandler() {
    return new DefaultDBFieldHandler(); // 自动填充参数类
}
```

**解读**：
- 第 4 行：`PaginationInnerInterceptor` —— MP 分页插件（ruoyi 列表分页必备）
- 第 8 行（注释）：`BlockAttackInnerInterceptor` —— 拦截「不带条件的 update/delete」防误删（生产环境强烈建议开启）
- 第 13-15 行：`DefaultDBFieldHandler` —— 自动填充 `creator/create_time/updater/update_time`（继承自 `BaseDO` 的所有表都受益）
- **设计意图**：通过 starter 统一注入 MP 拦截器，模块只需继承 BaseMapperX 即可享受完整能力

## 4. 关键要点总结

- MP 是 MyBatis 的**增强**，不是替代品
- ruoyi **100% 使用 MP**，XML 文件仅在复杂 SQL 场景使用
- MP 核心能力：CRUD 通用、条件构造、分页、逻辑删除、乐观锁、自动填充
- 生产环境建议开启 `BlockAttackInnerInterceptor`（防全表更新）

## 5. 练习题

### 练习 1：基础（必做）

新建 Java 项目，引入 MyBatis Plus 依赖，定义 `User` 实体和 `UserMapper extends BaseMapper<User>`，实现 `insert/selectById/updateById/deleteById` 四个操作（无需 XML）。

### 练习 2：进阶

用 MP 实现「分页查询 status=0 且 name 包含 'admin' 的用户，按 id 倒序」，对比纯 MyBatis 实现，体会 MP 的优势。

### 练习 3：挑战（选做）

阅读 MP 官方文档，列出至少 5 个 ruoyi 未使用但可能有用的 MP 特性，写一篇简短的使用建议。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/pom.xml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
- MyBatis Plus 官方文档：https://baomidou.com/
- MyBatis 官方文档：https://mybatis.org/mybatis-3/

---

**文档版本**：v1.0
**最后更新**：2026-07-13