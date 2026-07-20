# 7.2.1 用户管理

> 深入理解 ruoyi 系统模块中用户管理的实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 用户管理模块的完整代码结构
- 理解用户 CRUD、密码、状态、导入导出接口
- 学会用户唯一性校验、密码加密等业务逻辑
- 能仿照用户管理开发其他业务模块

## 📚 前置知识

- 三层架构（详见 [MVC 分层](./02-mvc-layers.md)）
- 对象转换（详见 [DTO/VO/DO](./03-dto-vo-do.md)）
- 统一响应（详见 [CommonResult](./05-common-result.md)）
- RBAC 与权限标识（详见 [RBAC](../../_common/08-authorization/01-rbac.md)）
- 密码哈希（详见 [哈希](../../_common/06-encryption/03-hash.md)）

## 1. 核心概念

### 1.1 用户管理功能全景

ruoyi 用户管理提供完整的用户生命周期管理：

| 功能 | 接口 | 权限标识 |
|------|------|----------|
| 创建用户 | `POST /system/user/create` | `system:user:create` |
| 修改用户 | `PUT /system/user/update` | `system:user:update` |
| 删除用户 | `DELETE /system/user/delete` | `system:user:delete` |
| 用户分页 | `GET /system/user/page` | `system:user:query` |
| 用户详情 | `GET /system/user/get` | `system:user:query` |
| 重置密码 | `PUT /system/user/update-password` | `system:user:update-password` |
| 修改状态 | `PUT /system/user/update-status` | `system:user:update` |
| 导入用户 | `POST /system/user/import` | `system:user:import` |
| 导出用户 | `GET /system/user/export-excel` | `system:user:export` |

### 1.2 用户 DO 字段

**文件位置**：`yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/user/AdminUserDO.java`

```java
@TableName(value = "system_users", autoResultMap = true)
@KeySequence("system_users_seq")
@Data
@EqualsAndHashCode(callSuper = true)
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AdminUserDO extends TenantBaseDO {
    @TableId
    private Long id;
    private String username;       // 用户账号
    private String password;       // 加密后的密码
    private String nickname;       // 昵称
    private String remark;         // 备注
    private Long deptId;           // 部门 ID
    @TableField(typeHandler = JacksonTypeHandler.class)
    private Set<Long> postIds;     // 岗位编号数组
    private String email;
    private String mobile;
    private Integer sex;           // 性别
    private String avatar;         // 头像
    private Integer status;        // 状态
    private String loginIp;        // 最后登录 IP
    private LocalDateTime loginDate; // 最后登录时间
}
```

### 1.3 关键设计点

1. **多租户**：继承 `TenantBaseDO`，自动支持多租户隔离（详见 [多租户](../../_common/08-authorization/05-multi-tenant.md)）
2. **密码加密**：使用 `BCryptPasswordEncoder`，自带 salt
3. **JSON 字段**：`postIds` 用 `JacksonTypeHandler` 存储到 MySQL 的 JSON 列
4. **逻辑删除**：继承 `TenantBaseDO` 后自动获得 createTime、updateTime、creator、updater 等字段

## 2. 代码示例

### 2.1 用户创建（Controller + Service）

```java
// Controller
@PostMapping("/create")
@PreAuthorize("@ss.hasPermission('system:user:create')")
public CommonResult<Long> createUser(@Valid @RequestBody UserSaveReqVO reqVO) {
    Long id = userService.createUser(reqVO);
    return success(id);
}

// Service
@Transactional(rollbackFor = Exception.class)
public Long createUser(UserSaveReqVO reqVO) {
    // 1. 校验用户名唯一
    validateUserUsernameUnique(null, reqVO.getUsername());
    // 2. 校验手机号唯一
    validateUserMobileUnique(null, reqVO.getMobile());
    // 3. 校验部门
    deptService.validateDeptList(reqVO.getDeptIds());
    // 4. 转换 VO -> DO
    AdminUserDO user = UserConvert.INSTANCE.convert(reqVO);
    // 5. 设置默认密码
    user.setPassword(encodePassword("123456"));
    // 6. 插入数据库
    userMapper.insert(user);
    return user.getId();
}
```

### 2.2 密码加密

```java
private String encodePassword(String password) {
    // 使用 Spring Security 的 BCrypt 加密，自动加盐
    return passwordEncoder.encode(password);
}
```

### 2.3 用户名唯一性校验

```java
private void validateUserUsernameUnique(Long id, String username) {
    if (StrUtil.isBlank(username)) return;
    AdminUserDO user = userMapper.selectByUsername(username);
    if (user == null) return;
    if (id == null || !user.getId().equals(id)) {
        throw exception(USER_USERNAME_EXISTS);  // 抛业务异常
    }
}
```

## 3. 关键要点总结

- ruoyi 用户管理是典型的"CRUD + 业务校验"模块
- 继承 `TenantBaseDO` 自动获得多租户 + 审计字段
- 密码使用 `BCryptPasswordEncoder` 加密
- JSON 字段（如 `postIds`）用 `JacksonTypeHandler` 存储
- 唯一性校验通过 `selectByXxx` + 业务异常实现
- 所有写操作都有 `@Transactional` 事务控制

---

**文档版本**：v1.0
**最后更新**：2026-07-13
