# 26 跨租户查询与超级管理员

> 详解"跨租户访问"的场景、实现和 ruoyi 的超级管理员机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解"跨租户访问"的业务场景
- 掌握 `LoginUser.visitTenantId` 的作用
- 知道 `skipPermissionCheck()` 的设计意图
- 能实现"管理员查看所有租户数据"的功能

## 📚 前置知识

- 21-multi-tenant.md
- 23-tenant-context.md
- 25-tenant-ignore.md

## 1. 核心概念

### 1.1 什么是跨租户访问？

普通用户：登录后只能访问自己租户的数据
超级管理员：可以**切换租户**，查看所有租户的数据

**典型场景**：
1. 平台超管登录
2. 选择"代表租户 A 查看数据"
3. 所有查询都加 `tenant_id = A`
4. 但超管实际身份属于"平台租户"

### 1.2 关键字段：`LoginUser.visitTenantId`

```java
@Data
public class LoginUser {
    private Long tenantId;        // 用户的"真实"租户（平台租户）
    private Long visitTenantId;   // 用户正在访问的租户（可能是其他租户）
}
```

**使用规则**：
- `tenantId == visitTenantId`：正常访问自己租户
- `tenantId != visitTenantId`：跨租户访问

### 1.3 skipPermissionCheck 的设计意图

**为什么跨租户时跳过权限检查？**

跨租户访问通常用于"管理后台"场景：
- 超管代表租户 A 操作
- 但超管**没有**租户 A 的角色/权限
- 如果强制检查租户 A 的权限，会导致超管"无权限"
- **解决方案**：跨租户时跳过功能权限、数据权限检查

```java
public static boolean skipPermissionCheck() {
    LoginUser loginUser = getLoginUser();
    if (loginUser == null) return false;
    if (loginUser.getVisitTenantId() == null) return false;
    // 重点：跨租户访问时，无法进行权限校验
    return ObjUtil.notEqual(loginUser.getVisitTenantId(), loginUser.getTenantId());
}
```

## 2. 代码示例

### 2.1 跨租户访问流程

```java
// 1. 平台超管登录
LoginUser user = login("super_admin", "xxx");
// user.tenantId = 0 (平台租户)
// user.visitTenantId = 0 (默认)

// 2. 切换到租户 A
user.setVisitTenantId(1L);

// 3. 查询租户 A 的用户
List<UserDO> users = userMapper.selectList();
// SQL: SELECT * FROM system_user WHERE tenant_id = 1
// 注意：没有 dept_id 过滤（因为是跨租户，没有租户 A 的部门）
```

### 2.2 切换租户的实现

```java
// 文件：TenantSwitchService.java
@Service
public class TenantSwitchService {

    public void switchTenant(Long newTenantId) {
        LoginUser user = SecurityFrameworkUtils.getLoginUser();
        // 1. 校验：只有超管才能切换
        if (!isSuperAdmin(user)) {
            throw new ServiceException("无权切换租户");
        }
        // 2. 校验：目标租户必须存在
        if (tenantService.getTenant(newTenantId) == null) {
            throw new ServiceException("租户不存在");
        }
        // 3. 设置 visitTenantId
        user.setVisitTenantId(newTenantId);
        // 4. 同时设置 ThreadLocal
        TenantContextHolder.setTenantId(newTenantId);
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 LoginUser 中的跨租户字段

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/LoginUser.java`
**核心代码**（行 41、60-62）：

```java
@Data
public class LoginUser {

    /** 用户编号 */
    private Long id;
    /** 用户类型 */
    private Integer userType;
    /** 额外的用户信息 */
    private Map<String, String> info;
    /** 租户编号 */
    private Long tenantId;
    /** 授权范围 */
    private List<String> scopes;
    /** 过期时间 */
    private LocalDateTime expiresTime;

    /** 上下文字段，不进行持久化 */
    @JsonIgnore
    private Map<String, Object> context;
    /** 访问的租户编号（用于跨租户访问场景） */
    private Long visitTenantId;
    // ...
}
```

**解读**：
- 第 41 行 `tenantId`：用户实际归属的租户
- 第 62 行 `visitTenantId`：用户正在访问的租户（可能不同）

### 3.2 skipPermissionCheck 实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/util/SecurityFrameworkUtils.java`
**核心代码**（行 144-158）：

```java
/**
 * 是否条件跳过权限校验，包括数据权限、功能权限
 *
 * @return 是否跳过
 */
public static boolean skipPermissionCheck() {
    LoginUser loginUser = getLoginUser();
    if (loginUser == null) {
        return false;
    }
    if (loginUser.getVisitTenantId() == null) {
        return false;
    }
    // 重点：跨租户访问时，无法进行权限校验
    return ObjUtil.notEqual(loginUser.getVisitTenantId(), loginUser.getTenantId());
}
```

**逐行解读**：
- 第 148-150 行：未登录时不需要跳过（反正没权限）
- 第 151-153 行：没设置 visitTenantId 时不需要跳过
- 第 157 行：**核心判断** — visitTenantId != tenantId 时跳过

### 3.3 在数据权限中的使用

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/db/DataPermissionRuleHandler.java`
**核心代码**（行 31-35）：

```java
@Override
public Expression getSqlSegment(Table table, Expression where, String mappedStatementId) {
    // 特殊：跨租户访问
    if (skipPermissionCheck()) {
        return null;  // 不加数据权限
    }
    // ...
}
```

**解读**：
- 第 33 行：**关键** — 跨租户时直接返回 null，不加数据权限
- 这就是为什么超管"切换租户"后能看到所有数据

### 3.4 超管自动拥有所有权限

`PermissionServiceImpl.hasAnyPermissions`：

```java
// 情况二：如果是超管，也说明有权限
return roleService.hasAnySuperAdmin(convertSet(roles, RoleDO::getId));
```

**解读**：
- 任何权限判断的"兜底"逻辑
- 超管 (`code = "super_admin"`) 自动通过

## 4. 关键要点总结

- `LoginUser.visitTenantId` 用于"跨租户访问"
- `skipPermissionCheck()` 判断 `visitTenantId != tenantId`
- 跨租户时**跳过**功能权限和数据权限校验
- 超管自动拥有所有权限（`hasAnySuperAdmin` 兜底）
- 跨租户 + 超管 = 平台级管理后台

## 5. 练习题

### 练习 1：基础（必做）

写一个方法判断"当前用户是否在跨租户访问"。

### 练习 2：进阶

实现"租户切换"接口：超管可以切换到任意租户。说明要修改 LoginUser、TenantContextHolder、Token 的哪些字段。

### 练习 3：挑战（选做）

跨租户时跳过权限检查，**是否有安全风险**？如果被恶意利用怎么办？设计一个"跨租户访问审计日志"功能。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/LoginUser.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/util/SecurityFrameworkUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/db/DataPermissionRuleHandler.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
