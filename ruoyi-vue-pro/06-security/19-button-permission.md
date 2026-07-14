# 19 按钮权限：自定义注解

> 详解 ruoyi 的"按钮权限"机制：如何在前端按粒度控制按钮的显示和隐藏。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解按钮权限的两种实现方式：后端注解 vs 前端指令
- 掌握 ruoyi 的 `@PreAuthorize` 注解用法
- 知道前端 Vue 自定义指令 `v-hasPermi` 如何实现
- 能为系统添加按钮级别的细粒度控制

## 📚 前置知识

- 16-rbac.md
- 18-dynamic-menu.md
- Vue 自定义指令

## 1. 核心概念

### 1.1 按钮权限 vs 菜单权限

| 维度 | 菜单权限 | 按钮权限 |
|------|---------|---------|
| 控制对象 | 整个页面 | 单个按钮 |
| 粒度 | 粗 | 细 |
| 实现方式 | 动态路由 | 注解 + 指令 |
| 配置位置 | 角色-菜单 | 角色-按钮权限 |

### 1.2 ruoyi 的实现：双重防护

**后端**（强制）：`@PreAuthorize("@ss.hasPermission('system:user:create')")`
- 没权限直接返回 403
- **安全防线**（前端可以被绕过）

**前端**（美化）：Vue 指令 `v-hasPermi="['system:user:create']"`
- 没权限按钮直接隐藏
- **用户体验**（更友好）

## 2. 代码示例

### 2.1 后端按钮权限

```java
// 文件：UserController.java
@RestController
@RequestMapping("/admin-api/system/user")
public class UserController {

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('system:user:create')")  // 后端校验
    public CommonResult<Long> createUser(@RequestBody UserCreateReqVO reqVO) {
        return success(userService.createUser(reqVO));
    }

    @DeleteMapping("/delete")
    @PreAuthorize("@ss.hasPermission('system:user:delete')")
    public CommonResult<Boolean> deleteUser(@RequestParam Long id) {
        userService.deleteUser(id);
        return success(true);
    }
}
```

### 2.2 前端 Vue 自定义指令

```typescript
// 文件：directives/hasPermi.ts
import type { Directive, DirectiveBinding } from 'vue';
import { useUserStore } from '@/store/modules/user';

function checkPermission(el: Element, binding: DirectiveBinding) {
  const userStore = useUserStore();
  const requiredPerms = binding.value;  // ['system:user:create']

  if (!requiredPerms || requiredPerms.length === 0) return;

  const userPerms = userStore.permissions;  // 当前用户的所有权限
  const hasPermission = requiredPerms.some(p => userPerms.includes(p));

  if (!hasPermission) {
    el.parentNode?.removeChild(el);  // 移除按钮
  }
}

const hasPermi: Directive = {
  mounted(el, binding) {
    checkPermission(el, binding);
  },
  updated(el, binding) {
    checkPermission(el, binding);
  }
};

export default hasPermi;
```

### 2.3 在模板中使用

```vue
<template>
  <div>
    <el-button v-hasPermi="['system:user:create']" @click="handleCreate">
      新增用户
    </el-button>

    <el-button v-hasPermi="['system:user:delete']" @click="handleDelete">
      删除
    </el-button>
  </div>
</template>
```

## 3. ruoyi 仓库源码解读

### 3.1 后端按钮权限示例

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/permission/PermissionController.java`
**核心代码**（行 53-59）：

```java
@PostMapping("/assign-role-data-scope")
@Operation(summary = "赋予角色数据权限")
@PreAuthorize("@ss.hasPermission('system:permission:assign-role-data-scope')")
public CommonResult<Boolean> assignRoleDataScope(@Valid @RequestBody PermissionAssignRoleDataScopeReqVO reqVO) {
    permissionService.assignRoleDataScope(reqVO.getRoleId(), reqVO.getDataScope(), reqVO.getDataScopeDeptIds());
    return success(true);
}
```

**解读**：
- `@PreAuthorize("@ss.hasPermission('system:permission:assign-role-data-scope')")` 是**按钮级**权限校验
- 即使前端显示了按钮，没有这个权限的用户调用也会返回 403

### 3.2 权限标识命名规范

ruoyi 的权限标识采用三段式：
```
{模块}:{资源}:{操作}
```

| 权限标识 | 含义 |
|---------|------|
| `system:user:create` | 系统模块的用户新增 |
| `system:user:delete` | 系统模块的用户删除 |
| `system:permission:assign-role-menu` | 权限模块的分配角色菜单 |
| `infra:file:upload` | 基础设施的文件上传 |

**为什么用三段？**
- **模块**：定位功能模块
- **资源**：定位表/实体
- **操作**：增删改查

### 3.3 完整链路

```
用户点击"新增用户"按钮
    ↓
后端 @PreAuthorize("@ss.hasPermission('system:user:create')")
    ↓
PermissionServiceImpl.hasAnyPermissions(userId, "system:user:create")
    ↓
1. 查用户的角色（缓存）
2. permission → menuId
3. 判断角色是否拥有该 menu
4. 超管兜底
    ↓
有权限 → 执行 createUser()
无权限 → 抛 AccessDeniedException
    ↓
AccessDeniedHandlerImpl 返回 403
```

## 4. 关键要点总结

- 按钮权限 = **后端 `@PreAuthorize`** + **前端 `v-hasPermi` 指令**
- 后端是**安全防线**（不可绕过）
- 前端是**体验优化**（隐藏按钮）
- 权限标识命名规范：`{模块}:{资源}:{操作}`
- ruoyi 通过 `system_menu.permission` 字段记录按钮权限

## 5. 练习题

### 练习 1：基础（必做）

写一个 Controller 方法，用 `@PreAuthorize("@ss.hasPermission('order:order:create')")` 保护订单创建接口。

### 练习 2：进阶

实现 Vue 指令 `v-hasRole="['super_admin']"`，要求支持单角色、角色数组、与运算（`+` 开头）、或运算（无前缀）三种模式。

### 练习 3：挑战（选做）

设计"按钮权限批量管理"功能：管理员可以勾选"哪些角色拥有哪些按钮权限"。说明前端交互、后端批量接口、Service 实现。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/permission/PermissionController.java`
- Vue 自定义指令：https://cn.vuejs.org/guide/reusability/custom-directives.html
- Spring @PreAuthorize：https://docs.spring.io/spring-security/reference/servlet/authorization/method-security.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
