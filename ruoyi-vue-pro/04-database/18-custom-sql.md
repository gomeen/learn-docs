# 18 自定义 SQL：@Select / @Update

> 不是所有 SQL 都能用条件构造器实现。ruoyi 在复杂场景下使用 XML/注解自定义 SQL。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 MyBatis XML 与注解两种自定义 SQL 方式
- 知道何时应该用自定义 SQL（而非条件构造器）
- 掌握 ruoyi 实战中的自定义 SQL 模式
- 能阅读 ruoyi 中 XML Mapper 文件

## 📚 前置知识

- [09-mybatis-vs-mp.md](./09-mybatis-vs-mp.md)
- [12-query-wrapper.md](./12-query-wrapper.md)
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

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 自定义 SQL 实战：角色菜单删除

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/resources/mapper/system/RoleMenuMapper.xml`（节选自典型自定义 XML）

```xml
<mapper namespace="cn.iocoder.yudao.module.system.dal.mysql.permission.RoleMenuMapper">

    <delete id="deleteListByRoleIdAndMenuIds">
        UPDATE system_role_menu
        SET deleted = 1
        WHERE role_id = #{roleId}
          AND menu_id IN
            <foreach collection="menuIds" item="menuId" open="(" separator="," close=")">
                #{menuId}
            </foreach>
          AND deleted = 0
    </delete>

    <select id="selectListByRoleId" resultType="cn.iocoder.yudao.module.system.dal.dataobject.permission.RoleMenuDO">
        SELECT id, role_id, menu_id, creator, create_time
        FROM system_role_menu
        WHERE role_id = #{roleId} AND deleted = 0
    </select>

</mapper>
```

**解读**：
- **第 3-13 行**：自定义批量删除（用 foreach 拼接 IN）
- **第 15-20 行**：自定义单条查询（无动态条件，简单 SELECT 仍可用 XML）
- **设计意图**：批量删除 + IN 列表是条件构造器无法优雅表达的场景

### 3.2 复杂统计 SQL：infra_api_access_log

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/mapper/infra/ApiAccessLogMapper.xml`

```xml
<mapper namespace="cn.iocoder.yudao.module.infra.dal.mysql.logger.ApiAccessLogMapper">

    <select id="selectApiAccessLogList" resultType="cn.iocoder.yudao.module.infra.controller.admin.logger.vo.apiaccesslog.ApiAccessLogRespVO">
        SELECT id, trace_id, user_id, user_type, application_name,
               request_method, request_url, request_params, response_body,
               user_ip, user_agent, oper_module, oper_name, oper_time,
               cost_ms, status_code, process_status
        FROM infra_api_access_log
        <where>
            <if test="reqVO.userId != null">AND user_id = #{reqVO.userId}</if>
            <if test="reqVO.userType != null">AND user_type = #{reqVO.userType}</if>
            <if test="reqVO.applicationName != null">AND application_name = #{reqVO.applicationName}</if>
            <if test="reqVO.beginTime != null">AND create_time &gt;= #{reqVO.beginTime}</if>
            <if test="reqVO.endTime != null">AND create_time &lt;= #{reqVO.endTime}</if>
            <if test="reqVO.status != null">AND process_status = #{reqVO.status}</if>
        </where>
        ORDER BY id DESC
        LIMIT #{reqVO.offset}, #{reqVO.pageSize}
    </select>

</mapper>
```

**解读**：
- **动态条件**：用 `<if>` + `<where>` 实现多条件查询
- **特殊字符转义**：`>=` 转 `&gt;=`，`<=` 转 `&lt;=`
- **设计意图**：自定义 XML 在多字段模糊/精确混合查询时，比条件构造器更清晰

### 3.3 使用方法签名

```java
// 对应 Mapper 接口
public interface ApiAccessLogMapper extends BaseMapperX<ApiAccessLogDO> {
    List<ApiAccessLogRespVO> selectApiAccessLogList(@Param("reqVO") ApiAccessLogPageReqVO reqVO);
}
```

## 4. 关键要点总结

- 简单 SQL → 条件构造器；复杂 SQL → XML
- 复杂场景：批量操作、复杂 JOIN、GROUP BY + HAVING
- XML 动态 SQL 标签：`<if>`、`<where>`、`<foreach>`、`<set>`、`<choose>`
- ruoyi 实战中，**80% 的查询用条件构造器，20% 用 XML**

## 5. 练习题

### 练习 1：基础（必做）

写一个自定义 XML：查询「最近 30 天每天的订单数和总金额」，要求返回 `[{date, count, totalAmount}]` 结构。

### 练习 2：进阶

阅读 `RoleMenuMapper.xml`，用条件构造器（`LambdaQueryWrapperX`）重写 `deleteListByRoleIdAndMenuIds`。对比两种实现的差异，说明 XML 的优势在哪。

### 练习 3：挑战（选做）

为 ruoyi 设计一个自定义 SQL：统计「每个部门的人数 + 每个部门的角色数 + 每个部门的在线用户数」，要求用一条 SQL 完成，并解释为何此 SQL 不适合用条件构造器实现。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/resources/mapper/system/RoleMenuMapper.xml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/mapper/infra/ApiAccessLogMapper.xml`
- MyBatis 动态 SQL：https://mybatis.org/mybatis-3/dynamic-sql.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13