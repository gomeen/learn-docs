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
- RBAC / 按钮权限（详见 [RBAC](../../_common/08-authorization/01-rbac.md)、[@PreAuthorize](../06-security/06-preauthorize.md)）

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 SN 码页：完整的按钮权限应用

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`

```vue
<!-- line 52-59: 生成按钮 -->
<el-button
  type="primary"
  plain
  @click="openForm()"
  v-hasPermi="['mes:wm-sn:create']"
>
  <Icon icon="ep:plus" class="mr-5px" /> 生成 SN 码
</el-button>

<!-- line 60-68: 导出按钮 -->
<el-button
  type="success"
  plain
  @click="handleExport"
  :loading="exportLoading"
  v-hasPermi="['mes:wm-sn:export']"
>
  <Icon icon="ep:download" class="mr-5px" /> 导出
</el-button>
```

```vue
<!-- line 88-99: 删除按钮（行内） -->
<el-table-column label="操作" align="center" width="120" fixed="right">
  <template #default="scope">
    <el-button
      link
      type="danger"
      @click="handleDelete(scope.row.id)"
      v-hasPermi="['mes:wm-sn:delete']"
    >
      删除
    </el-button>
  </template>
</el-table-column>
```

**解读**：
- 第 4 行：`v-hasPermi="['mes:wm-sn:create']"` —— 数组形式（虽然只有一个值）
- 第 14 行：`v-hasPermi="['mes:wm-sn:export']"` —— 导出权限
- 第 27 行：`v-hasPermi="['mes:wm-sn:delete']"` —— 行内删除按钮
- **perms 命名**：`mes:wm-sn:操作`，模块 = `mes`，资源 = `wm-sn`，操作 = `create/export/delete`
- **效果**：用户没有该权限时，按钮被 `removeChild` 从 DOM 中移除（不是 display:none）

### 3.2 后端权限约定（Java 端）

ruoyi 后端用 Spring Security + 自研 `@PreAuthorize` 注解：

```java
@PreAuthorize("@ss.hasPermission('mes:wm-sn:delete')")
@DeleteMapping("/delete-batch")
public CommonResult<Boolean> deleteSnBatch(@RequestParam String ids) {
    // ...
}
```

**前端权限是体验优化，后端权限是安全保障**。

### 3.3 权限数据来源

```ts
// store/modules/user.ts（约定）
export const useUserStore = defineStore('user', () => {
  const permissions = ref<string[]>([])

  async function fetchUserInfo() {
    const data = await getUserInfoApi()
    permissions.value = data.permissions  // ['system:user:query', 'mes:wm-sn:create', ...]
    // ...
  }

  return { permissions, fetchUserInfo }
})
```

## 4. 关键要点总结

- **perms 格式**：`模块:资源:操作`（如 `mes:wm-sn:create`）
- **v-hasPermi** 自定义指令：读 store 判断，没有权限直接 `removeChild`
- **前端权限是体验**：只控制 UI 显示/隐藏
- **后端权限是安全**：必须用 `@PreAuthorize` 等做接口级校验
- **超管短路**：`roles.includes('super_admin')` 跳过所有权限校验
- **权限数据**：登录后从 `/system/user/get-info` 拉到 `useUserStore.permissions`

## 5. 练习题

### 练习 1：基础（必做）

实现 v-hasPermi 指令：
- 接受字符串或字符串数组
- 从 store 读 permissions 判断
- 没有权限时移除元素

### 练习 2：进阶

为 SN 码页添加 4 个按钮：
- 新增（`mes:wm-sn:create`）
- 修改（`mes:wm-sn:update`）—— 用 `messageBox` 弹框
- 删除（`mes:wm-sn:delete`）
- 审批（`mes:wm-sn:approve`）—— 仅 admin 角色可见

### 练习 3：挑战（选做）

实现"权限测试模式"：URL 加 `?test=1` 时，所有按钮都显示并加上红色边框，方便测试人员检查权限覆盖。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
- ruoyi 官方文档 - 权限：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13