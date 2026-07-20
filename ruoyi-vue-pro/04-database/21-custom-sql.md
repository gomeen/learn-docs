# 18 自定义 SQL：@Select / @Update

> 不是所有 SQL 都能用条件构造器实现。ruoyi 在复杂场景下使用 XML/注解自定义 SQL。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 MyBatis XML 与注解两种自定义 SQL 方式
- 知道何时应该用自定义 SQL（而非条件构造器）
- 掌握 ruoyi 实战中的自定义 SQL 模式
- 能阅读 ruoyi 中 XML Mapper 文件

## 📚 前置知识

- [11-mybatis-vs-mp.md](./11-mybatis-vs-mp.md)
- [14-query-wrapper.md](./14-query-wrapper.md)
- 防 SQL 注入见 [SQL 注入](../../_common/05-web-security/03-sql-injection.md)

## 1. 核心概念

### 1.1 两种自定义 SQL 方式

| 方式 | 优点 | 缺点 |
|------|------|------|
| XML Mapper | 支持动态 SQL、复用片段 | 文件多、需切换 IDE 窗口 |
| 注解（@Select 等） | 与 Java 代码在一起 | 复杂 SQL 可读性差 |

### 1.2 何时用自定义 SQL

| 场景 | 推荐 |
|------|------|
| 单表 CRUD | 条件构造器 |
| 简单 JOIN | MPJ 连表 |
| **复杂 JOIN + GROUP BY + HAVING** | **XML 自定义** |
| 存储过程调用 | XML |
| 批量 UPDATE 多字段 | XML |

### 1.3 ruoyi 中自定义 SQL 的位置

```
yudao-module-system/src/main/resources/mapper/
├── system/
│   ├── RoleMapper.xml
│   ├── UserMapper.xml
│   └── ...
```

## 2. 代码示例

### 2.1 注解方式

```java
public interface UserMapper extends BaseMapperX<UserDO> {

    @Select("SELECT id, username, email FROM system_user WHERE username = #{username} AND deleted = 0")
    UserDO selectByUsernameAnno(@Param("username") String username);

    @Update("UPDATE system_user SET status = #{status}, update_time = NOW() WHERE id = #{id}")
    int updateStatus(@Param("id") Long id, @Param("status") Integer status);
}
```

### 2.2 XML 方式

```xml
<!-- UserMapper.xml -->
<mapper namespace="com.example.UserMapper">

    <select id="selectByCondition" resultType="com.example.UserDO">
        SELECT id, username, email, status, create_time
        FROM system_user
        <where>
            <if test="username != null and username != ''">
                AND username LIKE CONCAT('%', #{username}, '%')
            </if>
            <if test="status != null">
                AND status = #{status}
            </if>
            AND deleted = 0
        </where>
        ORDER BY create_time DESC
        LIMIT #{offset}, #{limit}
    </select>

</mapper>
```

### 2.3 复杂 JOIN + 聚合

```xml
<select id="statUserByDept" resultType="com.example.DeptUserStatVO">
    SELECT d.id AS dept_id,
           d.name AS dept_name,
           COUNT(u.id) AS user_count,
           SUM(CASE WHEN u.status = 0 THEN 1 ELSE 0 END) AS active_count
    FROM dept d
    LEFT JOIN system_user u ON d.id = u.dept_id AND u.deleted = 0
    WHERE d.deleted = 0
    GROUP BY d.id, d.name
    HAVING user_count > 0
    ORDER BY user_count DESC
</select>
```

## 3. 关键要点总结

- 简单 SQL → 条件构造器；复杂 SQL → XML
- 复杂场景：批量操作、复杂 JOIN、GROUP BY + HAVING
- XML 动态 SQL 标签：`<if>`、`<where>`、`<foreach>`、`<set>`、`<choose>`
- ruoyi 实战中，**80% 的查询用条件构造器，20% 用 XML**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
