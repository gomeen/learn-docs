# 7.2.2 角色管理

> 理解 ruoyi 中角色（Role）管理的实现，角色绑定菜单的关联关系。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握角色管理接口的设计
- 理解角色与菜单的多对多关系
- 学会角色代码（code）唯一性校验
- 理解 ruoyi RBAC 模型的角色设计

## 📚 前置知识

- 用户管理（详见 [用户管理](./07-user.md)）
- RBAC 通用模型（详见 [RBAC](../../_common/08-authorization/01-rbac.md)）
- 数据库多对多关联基础
- 命名规范（详见 [命名](./03-naming.md)）

## 1. 核心概念

### 1.1 RBAC 模型中的角色

ruoyi 使用 **RBAC（Role-Based Access Control）** 权限模型：

```
用户（User）── 1:N ── 用户角色关联（UserRole）── N:1 ── 角色（Role）
                                                          │
                                                          │ N:M
                                                          ↓
                                                       菜单（Menu）
```

### 1.2 角色与菜单的关系

一个角色可以绑定多个菜单（权限点），一个菜单也可以被多个角色共享：

```
admin 角色 → system:user:*  + system:role:* + ...
普通用户角色 → system:user:query
```

**核心字段**：
- `code`：角色代码（如 `admin`），全局唯一
- `name`：角色名称（如 "管理员"）
- `sort`：排序号
- `status`：启用/禁用
- `type`：类型（内置 / 自定义）

### 1.3 角色与用户的关联

`system_user_role` 中间表：
```sql
CREATE TABLE system_user_role (
    user_id BIGINT,
    role_id BIGINT,
    PRIMARY KEY (user_id, role_id)
);
```

## 2. 代码示例

### 2.1 角色 Controller 基础

```java
@PostMapping("/create")
@PreAuthorize("@ss.hasPermission('system:role:create')")
public CommonResult<Long> createRole(@Valid @RequestBody RoleSaveReqVO createReqVO) {
    return success(roleService.createRole(createReqVO, null));
}

@GetMapping("/page")
public CommonResult<PageResult<RoleRespVO>> getRolePage(RolePageReqVO pageReqVO) {
    PageResult<RoleDO> pageResult = roleService.getRolePage(pageReqVO);
    return success(BeanUtils.toBean(pageResult, RoleRespVO.class));
}
```

### 2.2 角色保存 ReqVO

```java
@Schema(description = "管理后台 - 角色创建/修改 Request VO")
@Data
public class RoleSaveReqVO {

    @Schema(description = "角色编号", example = "1")
    private Long id;

    @Schema(description = "角色名称", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "角色名称不能为空")
    private String name;

    @Schema(description = "角色代码", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "角色标志不能为空")
    private String code;

    @Schema(description = "显示顺序", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotNull(message = "显示顺序不能为空")
    private Integer sort;

    @Schema(description = "状态", requiredMode = Schema.RequiredMode.REQUIRED)
    private CommonStatusEnum status;

    @Schema(description = "菜单编号列表")
    private Set<Long> menuIds;
}
```

## 3. ruoyi 仓库源码解读

### 3.1 RoleController 完整代码

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/permission/RoleController.java`

**核心代码**（行 33-89）：

```java
@Tag(name = "管理后台 - 角色")
@RestController
@RequestMapping("/admin-api/system/role")
@Validated
public class RoleController {

    @Resource
    private RoleService roleService;

    @PostMapping("/create")
    @Operation(summary = "创建角色")
    @PreAuthorize("@ss.hasPermission('system:role:create')")
    public CommonResult<Long> createRole(@Valid @RequestBody RoleSaveReqVO createReqVO) {
        return success(roleService.createRole(createReqVO, null));
    }

    @PutMapping("/update")
    @Operation(summary = "修改角色")
    @PreAuthorize("@ss.hasPermission('system:role:update')")
    public CommonResult<Boolean> updateRole(@Valid @RequestBody RoleSaveReqVO updateReqVO) {
        roleService.updateRole(updateReqVO);
        return success(true);
    }

    @GetMapping("/page")
    @Operation(summary = "获得角色分页")
    @PreAuthorize("@ss.hasPermission('system:role:query')")
    public CommonResult<PageResult<RoleRespVO>> getRolePage(RolePageReqVO pageReqVO) {
        PageResult<RoleDO> pageResult = roleService.getRolePage(pageReqVO);
        return success(BeanUtils.toBean(pageResult, RoleRespVO.class));
    }

    @GetMapping({"/list-all-simple", "/simple-list"})
    @Operation(summary = "获取角色精简信息列表", description = "只包含被开启的角色，主要用于前端的下拉选项")
    public CommonResult<List<RoleRespVO>> getSimpleRoleList() {
        List<RoleDO> list = roleService.getRoleListByStatus(singleton(CommonStatusEnum.ENABLE.getStatus()));
        list.sort(Comparator.comparing(RoleDO::getSort));
        return success(BeanUtils.toBean(list, RoleRespVO.class));
    }
}
```

**解读**：
- 第 1-6 行：标准 Controller 三件套（Swagger 标签 + REST + 路由）
- 第 9-13 行：创建角色，返回角色 ID
- 第 15-19 行：修改角色
- 第 24-27 行：分页查询，使用 `BeanUtils.toBean` 一行转换
- 第 30-35 行：精简角色列表（用于前端下拉框），按 sort 排序

### 3.2 角色创建（Service）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/RoleServiceImpl.java`

**核心代码**（行 30-60）：

```java
@Override
@Transactional(rollbackFor = Exception.class)
public Long createRole(RoleSaveReqVO createReqVO, Integer type) {
    // 1. 校验角色
    validateRoleDuplicate(createReqVO.getCode(), createReqVO.getName(), null);
    // 2. 插入角色
    RoleDO role = new RoleDO();
    BeanUtils.copyProperties(createReqVO, role);
    role.setType(ObjectUtil.defaultIfNull(type, RoleTypeEnum.CUSTOM.getType()));
    roleMapper.insert(role);
    // 3. 插入角色与菜单的关联
    if (!CollectionUtils.isEmpty(createReqVO.getMenuIds())) {
        roleMenuService.createRoleMenuList(role.getId(), createReqVO.getMenuIds());
    }
    return role.getId();
}
```

**解读**：
- 第 4 行：校验角色 code 和 name 是否重复
- 第 6-9 行：创建 RoleDO 实体，设置类型（默认 CUSTOM）
- 第 10 行：插入角色
- 第 12-14 行：处理角色-菜单的关联（多对多）
- **设计点**：创建角色和绑定菜单在一个事务中

### 3.3 角色唯一性校验

```java
private void validateRoleDuplicate(String code, String name, Long id) {
    // 校验角色编码唯一
    RoleDO existByCode = roleMapper.selectByCode(code);
    if (existByCode != null && !existByCode.getId().equals(id)) {
        throw exception(ROLE_CODE_DUPLICATE);
    }
    // 校验角色名称唯一
    RoleDO existByName = roleMapper.selectByName(name);
    if (existByName != null && !existByName.getId().equals(id)) {
        throw exception(ROLE_NAME_DUPLICATE);
    }
}
```

## 4. 关键要点总结

- 角色管理是 RBAC 模型的核心
- 角色与菜单是多对多关系，通过中间表 `system_role_menu` 关联
- 角色与用户也是多对多关系，通过中间表 `system_user_role` 关联
- 角色有 `code`（代码）和 `name`（名称），需要唯一性校验
- 角色类型分内置（SYSTEM）和自定义（CUSTOM）
- 创建/修改角色时同时处理菜单绑定

## 5. 练习题

### 练习 1：基础（必做）

打开 `RoleMapper.java`，找到 `selectByCode` 和 `selectByName` 方法，理解如何实现唯一性校验。

### 练习 2：进阶

阅读 `RoleMenuServiceImpl.java`，理解 `createRoleMenuList` 如何处理"先删后增"的菜单绑定逻辑。

### 练习 3：挑战（选做）

如果用户属于多个角色，需要"用户拥有的所有权限 = 所有角色的并集"。请说明这个去重逻辑应该在哪里实现？列出可能的 3 个位置。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/permission/RoleController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/RoleServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/permission/RoleDO.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
