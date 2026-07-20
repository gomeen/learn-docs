# 11.6.2 动态菜单与路由

> 掌握 ruoyi 的动态菜单方案：登录后从后端拉菜单树 → 前端动态注册路由 → 侧边栏按路由渲染。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 的"后端返回菜单"模式
- 掌握菜单树转 Vue Router 配置的算法
- 实现动态 `router.addRoute`
- 处理路由刷新丢失问题

## 📚 前置知识

- Vue Router（详见 [Vue Router](./05-vue-router.md)）
- Pinia（详见 [Pinia](./06-pinia.md)）
- 项目结构（详见 [Vue3 结构](./28-ruoyi-vue3-structure.md)）
- 后端菜单 / RBAC（详见 [菜单](../07-business-modules/09-menu.md)、[RBAC](../../_common/08-authorization/01-rbac.md)）

## 1. 核心概念

### 1.1 静态路由 vs 动态路由

**静态路由**（写死在代码里）：
```ts
const staticRoutes = [
  { path: '/login', component: () => import('@/views/Login.vue') },
  { path: '/dashboard', component: () => import('@/views/Dashboard.vue') }
]
```

**动态路由**（登录后从后端拉）：
```ts
// 登录后
const menus = await api.getMenus()
menus.forEach(menu => router.addRoute(menu))
```

### 1.2 ruoyi 的菜单流程

```
1. 用户登录
   ↓
2. 后端返回 access_token
   ↓
3. 用 token 调 /system/user/get-info
   ↓ 后端返回：
   {
     permissions: ['system:user:query', ...],
     roles: ['admin'],
     menus: [
       {
         id: 1,
         name: '系统管理',
         path: '/system',
         component: 'Layout',
         icon: 'system',
         children: [
           { id: 11, name: '用户管理', path: 'user', component: 'system/user/index', perms: ['system:user:query'] },
           ...
         ]
       }
     ]
   }
   ↓
4. 前端把 menus 树转为 Vue Router 配置
   ↓
5. router.addRoute 注册
   ↓
6. el-menu 根据路由 meta 渲染侧边栏
```

### 1.3 菜单数据结构

后端返回的菜单项典型字段：

```ts
interface MenuVO {
  id: number
  parentId: number
  name: string              // 路由名
  path: string              // 路由路径
  component?: string        // 组件路径（Layout / system/user/index）
  redirect?: string         // 重定向
  icon?: string             // 图标
  perms?: string[]          // 权限标识
  type: number              // 0=目录 1=菜单 2=按钮
  sort: number              // 排序
  hidden?: boolean          // 是否隐藏
  keepAlive?: boolean       // 是否缓存
}
```

### 1.4 菜单 → 路由的转换算法

```ts
function buildRoutes(menus: MenuVO[]): RouteRecordRaw[] {
  return menus.map(menu => ({
    path: menu.path,
    name: menu.name,
    component: menu.component === 'Layout'
      ? () => import('@/layout/index.vue')
      : () => import(`@/views/${menu.component}.vue`),
    meta: {
      title: menu.name,
      icon: menu.icon,
      permissions: menu.perms,
      hidden: menu.hidden,
      keepAlive: menu.keepAlive
    },
    children: menu.children?.length
      ? buildRoutes(menu.children)
      : undefined,
    redirect: menu.redirect
  }))
}
```

## 2. 代码示例

### 2.1 完整动态路由注册

```ts
// store/modules/permission.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { router, constantRoutes } from '@/router'
import { getUserMenusApi } from '@/api/system/permission'

export const usePermissionStore = defineStore('permission', () => {
  const dynamicRoutes = ref<RouteRecordRaw[]>([])
  const sidebarRoutes = ref<MenuVO[]>([])

  async function generateRoutes() {
    const menus = await getUserMenusApi()
    sidebarRoutes.value = menus

    const routes = buildRoutes(menus)
    dynamicRoutes.value = constantRoutes.concat(routes)

    // 动态注册
    routes.forEach(route => router.addRoute(route))

    // 最后添加 404
    router.addRoute({ path: '/:pathMatch(.*)*', redirect: '/404' })
  }

  function resetRoutes() {
    dynamicRoutes.value.forEach(route => router.removeRoute(route.name!))
    dynamicRoutes.value = []
  }

  return { dynamicRoutes, sidebarRoutes, generateRoutes, resetRoutes }
})
```

### 2.2 路由守卫：刷新时恢复路由

```ts
// router/guard.ts
import { usePermissionStore } from '@/store/modules/permission'
import { useUserStore } from '@/store/modules/user'

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  const permissionStore = usePermissionStore()

  if (to.path === '/login') return next()

  if (!userStore.token) return next('/login')

  // 已登录但动态路由未注册
  if (permissionStore.dynamicRoutes.length === 0) {
    try {
      await permissionStore.generateRoutes()
      next({ ...to, replace: true })  // 用 replace 重新跳转
    } catch (err) {
      userStore.logout()
      next('/login')
    }
  } else {
    next()
  }
})
```

### 2.3 侧边栏渲染

```vue
<!-- layout/components/Sidebar.vue -->
<script setup lang="ts">
import { usePermissionStore } from '@/store/modules/permission'

const permissionStore = usePermissionStore()
const routes = computed(() => permissionStore.sidebarRoutes)
</script>

<template>
  <el-menu :default-active="route.path">
    <SidebarItem
      v-for="route in routes"
      :key="route.id"
      :item="route"
      :base-path="route.path"
    />
  </el-menu>
</template>
```

### 2.4 常见错误：刷新后路由丢失

```ts
// ❌ 错误：动态 addRoute 后刷新页面，路由消失
router.beforeEach((to, from, next) => {
  // 直接放行，但路由已经丢失
  next()
})

// ✅ 正确：刷新时重新加载
router.beforeEach(async (to, from, next) => {
  if (needReload) {
    await permissionStore.generateRoutes()
    next({ ...to, replace: true })  // 关键：用 replace 重新跳转
  } else {
    next()
  }
})
```

## 3. 关键要点总结

- **菜单数据**：登录后从 `/system/user/get-info` 拉取
- **核心流程**：登录 → 拉菜单 → 转路由 → `addRoute` → 渲染侧边栏
- **关键技巧**：`next({ ...to, replace: true })` 解决刷新路由丢失
- **侧边栏组件**：递归渲染，支持目录+叶子
- **菜单树结构**：parentId / id / children 三级
- **perms 字段**：用于按钮级权限控制（v-hasPermi）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
