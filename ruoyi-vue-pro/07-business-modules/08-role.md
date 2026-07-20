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
- 命名规范（详见 [命名](../../_common/20-engineering/01-naming.md)）

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

## 3. 关键要点总结

- 角色管理是 RBAC 模型的核心
- 角色与菜单是多对多关系，通过中间表 `system_role_menu` 关联
- 角色与用户也是多对多关系，通过中间表 `system_user_role` 关联
- 角色有 `code`（代码）和 `name`（名称），需要唯一性校验
- 角色类型分内置（SYSTEM）和自定义（CUSTOM）
- 创建/修改角色时同时处理菜单绑定

---

**文档版本**：v1.0
**最后更新**：2026-07-13
