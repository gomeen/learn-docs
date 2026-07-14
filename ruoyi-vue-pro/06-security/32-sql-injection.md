# 32 SQL 注入防护：MyBatis 参数化

> 详解 SQL 注入的原理、危害，以及 MyBatis 参数化如何防御。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 SQL 注入的原理
- 掌握 MyBatis 参数化查询（`#{}` vs `${}`）
- 知道 ruoyi 是如何防御 SQL 注入的
- 能识别和修复潜在的 SQL 注入漏洞

## 📚 前置知识

- MyBatis 基础
- MySQL 基础

## 1. 核心概念

### 1.1 什么是 SQL 注入？

**SQL 注入**：攻击者把 SQL 语句片段"注入"到原本的 SQL 中，改变查询逻辑。

**经典例子**：
```java
// 登录查询
String username = "' OR '1'='1";
String password = "anything";

String sql = "SELECT * FROM user WHERE username = '" + username + "' AND password = '" + password + "'";
// 实际执行: SELECT * FROM user WHERE username = '' OR '1'='1' AND password = 'anything'
// '1'='1' 永远为真，绕过密码验证！
```

### 1.2 攻击向量

| 类型 | 攻击示例 | 危害 |
|------|---------|------|
| 登录绕过 | `' OR '1'='1` | 绕过认证 |
| 数据泄露 | `'; DROP TABLE user; --` | 删表 |
| 数据修改 | `' UNION SELECT * FROM credit_card --` | 读其他表 |
| 提权 | `' OR 1=1 LIMIT 1 --` | 获取管理员 |

### 1.3 防御方案

| 方案 | 作用 |
|------|------|
| **参数化查询**（**最关键**） | 用 `?` 占位符，传参时不拼接 SQL |
| 输入验证 | 白名单校验（数字、邮箱） |
| 最小权限 | DB 账号只给 SELECT，不给 DROP |
| ORM 框架 | MyBatis-Plus、Hibernate 自动用参数化 |
| WAF | Web 应用防火墙（兜底） |

## 2. 代码示例

### 2.1 MyBatis #{} vs ${}

**`#{}`（参数化，安全）**：
```java
// MyBatis XML
<select id="getUser" resultType="User">
    SELECT * FROM user WHERE username = #{username} AND password = #{password}
</select>

// 实际执行（PreparedStatement）
// SELECT * FROM user WHERE username = ? AND password = ?
// 传入: username="' OR '1'='1", password="xxx"
// 结果: 查不到用户（'1'='1' 被当作普通字符串）
```

**`${}`（字符串拼接，危险）**：
```java
// ❌ 危险！
<select id="getUser">
    SELECT * FROM user WHERE username = '${username}'
</select>

// 实际执行: SELECT * FROM user WHERE username = '' OR '1'='1'
// 注入成功！
```

### 2.2 何时用 ${}？

**唯一合法场景**：表名、列名等**不能参数化**的字段。

```java
// ✅ 正确：表名是变量，用 ${}，但要做白名单校验
String tableName = "user";  // 来自白名单
sql = "SELECT * FROM " + tableName;

// ❌ 错误：直接拼用户输入
String tableName = request.getParameter("table");  // 危险！
sql = "SELECT * FROM " + tableName;
```

## 3. ruoyi 的 SQL 注入防护

### 3.1 全面使用 MyBatis-Plus

ruoyi 全量使用 MyBatis-Plus 的 `LambdaQueryWrapperX`，避免手写 SQL：

```java
// ✅ ruoyi 的标准写法
public List<UserDO> listUsers(String username) {
    return userMapper.selectList(
        new LambdaQueryWrapperX<UserDO>()
            .likeIfPresent(UserDO::getUsername, username)
    );
}

// 内部生成的 SQL: SELECT * FROM system_user WHERE username LIKE ?
// 永远参数化
```

### 3.2 自定义 XML 中的安全写法

```java
// yudao 中的 Mapper XML（示例）
<select id="selectByUsername" resultType="UserDO">
    SELECT * FROM system_user
    WHERE username = #{username}    -- 安全：参数化
      AND status = #{status}         -- 安全
    ORDER BY ${sortField}            -- 危险：必须确保 sortField 是白名单
</select>
```

**白名单校验示例**（ruoyi 的做法）：

```java
private static final Set<String> SORT_FIELDS = Set.of("id", "create_time", "username");

public List<UserDO> listUsers(String sortField) {
    // 关键：白名单校验
    if (!SORT_FIELDS.contains(sortField)) {
        sortField = "id";  // 默认值
    }
    return userMapper.selectListOrderBy(sortField);
}
```

### 3.3 租户隔离自动加 WHERE

ruoyi 的 `TenantDatabaseInterceptor` 自动加 `tenant_id = ?`，也是参数化（安全）。

### 3.4 数据权限自动加 WHERE

`DataPermissionRuleHandler` 生成的 SQL 条件也用参数化（`?` 占位符）。

## 4. 常见 SQL 注入点

```
1. 登录 SQL（最常见）
2. 搜索功能（LIKE 查询）
3. 排序字段（ORDER BY）
4. IN 列表
5. 报表/导出（动态 SQL）
6. 后台管理（用户输入直接拼 SQL）
```

## 5. 关键要点总结

- SQL 注入本质：用户输入**改变**了 SQL 逻辑
- **最关键的防御**：用 `#{}` 参数化，避免 `${}` 拼接
- ruoyi 全量用 MyBatis-Plus，自动参数化
- `${}` 只用于"无法参数化"的字段（表名、列名），且**必须白名单**
- 配合最小权限 DB 账号、WAF 兜底

## 6. 参考资料

- OWASP SQL Injection：https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- MyBatis 动态 SQL：https://mybatis.org/mybatis-3/zh/dynamic-sql.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
