# 7.2.1 用户管理

> 深入理解 ruoyi 系统模块中用户管理的实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 用户管理模块的完整代码结构
- 理解用户 CRUD、密码、状态、导入导出接口
- 学会用户唯一性校验、密码加密等业务逻辑
- 能仿照用户管理开发其他业务模块

## 📚 前置知识

- 02-mvc-layers.md（三层架构）
- 04-dto-vo-do.md（对象转换）
- 06-common-result.md（统一响应）

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

1. **多租户**：继承 `TenantBaseDO`，自动支持多租户隔离
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

## 3. ruoyi 仓库源码解读

### 3.1 UserController 完整代码片段

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/user/UserController.java`

**核心代码**（行 41-100）：

```java
@Tag(name = "管理后台 - 用户")
@RestController
@RequestMapping("/admin-api/system/user")
@Validated
public class UserController {

    @Resource
    private AdminUserService userService;
    @Resource
    private DeptService deptService;

    @PostMapping("/create")
    @Operation(summary = "新增用户")
    @PreAuthorize("@ss.hasPermission('system:user:create')")
    public CommonResult<Long> createUser(@Valid @RequestBody UserSaveReqVO reqVO) {
        Long id = userService.createUser(reqVO);
        return success(id);
    }

    @PutMapping("update")
    @Operation(summary = "修改用户")
    @PreAuthorize("@ss.hasPermission('system:user:update')")
    public CommonResult<Boolean> updateUser(@Valid @RequestBody UserSaveReqVO reqVO) {
        userService.updateUser(reqVO);
        return success(true);
    }

    @DeleteMapping("/delete")
    @Operation(summary = "删除用户")
    @Parameter(name = "id", description = "编号", required = true, example = "1024")
    @PreAuthorize("@ss.hasPermission('system:user:delete')")
    public CommonResult<Boolean> deleteUser(@RequestParam("id") Long id) {
        userService.deleteUser(id);
        return success(true);
    }
```

**解读**：
- 第 1-2 行：Swagger 标签 + REST 控制器
- 第 3 行：路由前缀 `/admin-api/system/user`
- 第 7-8 行：注入两个 Service（用户、部门）
- 第 10-14 行：创建用户接口，需要 `system:user:create` 权限
- 第 16-20 行：修改用户接口
- 第 22-27 行：删除用户接口

### 3.2 AdminUserServiceImpl 核心方法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserServiceImpl.java`

**核心代码**（行 50-90）：

```java
@Override
@Transactional(rollbackFor = Exception.class)
public Long createUser(UserSaveReqVO reqVO) {
    // 1. 校验用户名唯一
    validateUserUsernameUnique(reqVO.getId(), reqVO.getUsername());
    // 2. 校验手机号唯一
    validateUserMobileUnique(reqVO.getId(), reqVO.getMobile());
    // 3. 校验部门
    deptService.validateDeptList(reqVO.getDeptIds());
    // 4. 转换 VO -> DO
    AdminUserDO user = UserConvert.INSTANCE.convert(reqVO);
    if (reqVO.getPassword() == null) {
        user.setPassword(encodePassword("123456"));  // 默认密码
    } else {
        user.setPassword(encodePassword(reqVO.getPassword()));
    }
    // 5. 插入数据库
    userMapper.insert(user);
    return user.getId();
}
```

**解读**：
- 第 2 行：事务注解，任何异常回滚
- 第 4-8 行：业务校验（唯一性、关联性）
- 第 10 行：使用 UserConvert 把 ReqVO 转 DO
- 第 11-15 行：密码处理（默认 `123456` 或用户传入）
- 第 17 行：插入数据库并返回自增 ID

### 3.3 AdminUserMapper 查询方法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/user/AdminUserMapper.java`

**核心代码**（行 1-30）：

```java
@Mapper
public interface AdminUserMapper extends BaseMapperX<AdminUserDO> {

    default AdminUserDO selectByUsername(String username) {
        return selectOne(AdminUserDO::getUsername, username);
    }

    default PageResult<AdminUserDO> selectPage(UserPageReqVO reqVO) {
        return selectPage(reqVO, this::buildQuery);
    }

    private MPJLambdaWrapper<AdminUserDO> buildQuery(UserPageReqVO reqVO) {
        return new LambdaQueryWrapperX<AdminUserDO>()
                .likeIfPresent(AdminUserDO::getUsername, reqVO.getUsername())
                .eqIfPresent(AdminUserDO::getStatus, reqVO.getStatus())
                .betweenIfPresent(AdminUserDO::getCreateTime, reqVO.getCreateTime());
    }
}
```

**解读**：
- 第 2 行：继承 `BaseMapperX`，自动获得 CRUD 能力
- 第 4-6 行：使用 `default` 方法实现单表查询，无需 XML
- 第 8-10 行：分页查询
- 第 12-17 行：动态查询条件（`likeIfPresent` 当字段非空时拼接）

## 4. 关键要点总结

- ruoyi 用户管理是典型的"CRUD + 业务校验"模块
- 继承 `TenantBaseDO` 自动获得多租户 + 审计字段
- 密码使用 `BCryptPasswordEncoder` 加密
- JSON 字段（如 `postIds`）用 `JacksonTypeHandler` 存储
- 唯一性校验通过 `selectByXxx` + 业务异常实现
- 所有写操作都有 `@Transactional` 事务控制

## 5. 练习题

### 练习 1：基础（必做）

打开 `AdminUserServiceImpl.java`，找到 `updateUserPassword` 方法，理解密码加密和更新流程。

### 练习 2：进阶

阅读 `importUserList` 方法的实现，理解 Excel 导入用户的完整流程（包含唯一性校验、错误收集）。

### 练习 3：挑战（选做）

如果要给用户管理添加"批量修改部门"功能，需要修改哪些文件？列出具体步骤和代码位置。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/user/UserController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/user/AdminUserMapper.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/user/AdminUserDO.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
