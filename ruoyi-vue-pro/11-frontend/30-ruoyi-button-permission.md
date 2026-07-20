# 11.6.3 按钮权限控制

> 掌握 ruoyi 的按钮级权限方案：v-hasPermi 自定义指令，控制按钮的显示/隐藏。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 的 RBAC 按钮权限模型（perms 字段）
- 编写 v-hasPermi 自定义指令
- 在按钮、表格列、菜单项上做权限控制
- 区分前端权限（体验）和后端权限（安全）

## 📚 前置知识

- Pinia（详见 [Pinia](./06-pinia.md)）
- Vue3 自定义指令
- RBAC / 按钮权限（详见 [RBAC](../../_common/08-authorization/01-rbac.md)、[@PreAuthorize](../06-security/01-preauthorize.md)）

## 1. 核心概念

### 1.1 为什么需要按钮权限？

页面权限（菜单）控制**能否访问某个页面**。但页面内还有大量操作按钮：
- 新增、删除、修改、导出、审批……

这些按钮不能所有人都能用。**按钮权限 = 控制谁能点哪个按钮**。

### 1.2 ruoyi 的 RBAC 模型

```
用户 ──角色──▶ 权限（菜单 + 按钮 + 数据）
                  ↓
              perms 字段
```

`perms` 是权限字符串，常见格式：
- `system:user:query`（查询）
- `system:user:create`（新增）
- `system:user:update`（修改）
- `system:user:delete`（删除）
- `system:user:export`（导出）

格式约定：**`模块:资源:操作`**

### 1.3 用户权限加载流程

```
登录
 ↓
后端返回 permissions: ['system:user:query', 'system:user:create', ...]
 ↓
存入 useUserStore.permissions
 ↓
v-hasPermi 指令从 store 读取、判断是否显示按钮
```

### 1.4 自定义指令 v-hasPermi

```ts
// directives/hasPermi.ts
import type { Directive } from 'vue'
import { useUserStore } from '@/store/modules/user'

export const hasPermi: Directive<HTMLElement, string | string[]> = {
  mounted(el, binding) {
    const userStore = useUserStore()
    const requiredPerms = Array.isArray(binding.value)
      ? binding.value
      : [binding.value]

    const hasPermission = requiredPerms.some(perm =>
      userStore.permissions.includes(perm)
    )

    if (!hasPermission) {
      el.parentNode?.removeChild(el)  // 直接移除 DOM
    }
  }
}
```

### 1.5 使用方式

```vue
<el-button v-hasPermi="['mes:wm-sn:create']">生成 SN 码</el-button>
<el-button v-hasPermi="'mes:wm-sn:delete'">删除</el-button>
<el-button v-hasPermi="['mes:wm-sn:export']">导出</el-button>
```

支持单字符串或字符串数组。

## 2. 代码示例

### 2.1 完整 v-hasPermi 指令

```ts
// directives/hasPermi.ts
import type { Directive, DirectiveBinding } from 'vue'
import { useUserStore } from '@/store/modules/user'

function checkPermission(binding: DirectiveBinding<string | string[]>): boolean {
  const userStore = useUserStore()
  const value = binding.value
  if (!value) return true

  const requiredPerms: string[] = Array.isArray(value) ? value : [value]
  // 超管跳过校验
  if (userStore.roles.includes('super_admin')) return true

  return requiredPerms.some(perm => userStore.permissions.includes(perm))
}

export const hasPermi: Directive<HTMLElement, string | string[]> = {
  mounted(el, binding) {
    if (!checkPermission(binding)) el.parentNode?.removeChild(el)
  },
  updated(el, binding) {
    if (!checkPermission(binding)) el.parentNode?.removeChild(el)
  }
}
```

### 2.2 注册指令

```ts
// directives/index.ts
import type { App } from 'vue'
import { hasPermi } from './hasPermi'

export function setupDirectives(app: App) {
  app.directive('hasPermi', hasPermi)
}
```

```ts
// main.ts
import { setupDirectives } from './directives'
setupDirectives(app)
```

### 2.3 进阶：表格列权限

```vue
<el-table-column label="操作" align="center" width="200">
  <template #default="scope">
    <el-button v-hasPermi="['mes:wm-sn:update']" @click="handleEdit(scope.row)">
      编辑
    </el-button>
    <el-button v-hasPermi="['mes:wm-sn:delete']" @click="handleDelete(scope.row.id)">
      删除
    </el-button>
    <el-button v-hasPermi="['mes:wm-sn:approve']" @click="handleApprove(scope.row)">
      审批
    </el-button>
  </template>
</el-table-column>
```

### 2.4 进阶：组件级别权限

```ts
// composables/useAuth.ts
import { useUserStore } from '@/store/modules/user'

export function useAuth() {
  const userStore = useUserStore()

  function hasPermi(perm: string | string[]) {
    const required = Array.isArray(perm) ? perm : [perm]
    return required.some(p => userStore.permissions.includes(p))
  }

  function hasRole(role: string | string[]) {
    const required = Array.isArray(role) ? role : [role]
    return required.some(r => userStore.roles.includes(r))
  }

  return { hasPermi, hasRole }
}
```

```vue
<script setup lang="ts">
const { hasPermi } = useAuth()
</script>

<template>
  <el-button v-if="hasPermi('mes:wm-sn:create')">新增</el-button>
</template>
```

### 2.5 常见错误：只做前端权限

```ts
// ❌ 错误：只在前端隐藏按钮，后端没校验
// 用户可以绕过前端直接调 API
if (!user.permissions.includes('system:user:delete')) {
  throw new Error('无权限')
}

// ✅ 正确：前端 + 后端双重校验
// 前端：v-hasPermi 隐藏按钮（提升体验）
// 后端：Spring Security @PreAuthorize 校验（保证安全）
```

## 3. 关键要点总结

- **perms 格式**：`模块:资源:操作`（如 `mes:wm-sn:create`）
- **v-hasPermi** 自定义指令：读 store 判断，没有权限直接 `removeChild`
- **前端权限是体验**：只控制 UI 显示/隐藏
- **后端权限是安全**：必须用 `@PreAuthorize` 等做接口级校验
- **超管短路**：`roles.includes('super_admin')` 跳过所有权限校验
- **权限数据**：登录后从 `/system/user/get-info` 拉到 `useUserStore.permissions`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
