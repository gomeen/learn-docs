# 11.1.5 路由：Vue Router 4

> 掌握 Vue Router 4 的路由配置、动态路由、导航守卫，能在 ruoyi 中实现"动态菜单 + 权限路由"。

## 🎯 学习目标

完成本文档后，你将能够：
- 配置 Vue Router 4：静态路由、动态路由、嵌套路由
- 掌握 3 种路由传参方式（path / query / params）
- 掌握导航守卫（`beforeEach`、`beforeEnter`）
- 能理解 ruoyi 的"动态菜单 + 权限路由"方案

## 📚 前置知识

- Vue3 基础（详见 [Vue3 基础](./01-vue3-basics.md)）
- ES6 模块化基础
- 动态菜单路由（ruoyi，详见 [菜单动态路由](./24-ruoyi-menu.md)）

## 1. 核心概念

### 1.1 Vue Router 4 的核心概念

| 概念 | 说明 |
|------|------|
| `createRouter` | 创建路由实例（替代 Vue2 的 `new VueRouter`） |
| `createWebHistory` | HTML5 History 模式（无 `#`，需要服务端配置） |
| `createWebHashHistory` | Hash 模式（带 `#`，无需服务端配置） |
| `RouterView` | 路由出口组件（显示当前路由对应的组件） |
| `RouterLink` | 路由跳转组件（替代 `<a>`） |
| 路由记录 | `path`、`component`、`name`、`meta`、`children` 等 |

### 1.2 路由配置基本结构

```ts
import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/home' },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/home/index.vue'),
    meta: { title: '首页', icon: 'home', requiresAuth: true }
  },
  {
    path: '/user/:id',  // 动态段
    name: 'UserDetail',
    component: () => import('@/views/user/detail.vue')
  },
  {
    path: '/admin',
    component: () => import('@/views/admin/layout.vue'),
    children: [
      { path: 'users', component: () => import('@/views/admin/users.vue') }
    ]
  },
  { path: '/:pathMatch(.*)*', component: () => import('@/views/404.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

### 1.3 3 种路由传参方式

```vue
<!-- 1) path 动态段（params） -->
<RouterLink :to="`/user/${userId}`">查看</RouterLink>
<!-- 取值：route.params.id -->

<!-- 2) query 传参（URL 上 ?key=val） -->
<RouterLink :to="{ path: '/user', query: { id: 123 } }">查看</RouterLink>
<!-- 取值：route.query.id -->

<!-- 3) name + params（推荐，无 path 动态段时） -->
<RouterLink :to="{ name: 'UserDetail', params: { id: 123 } }">查看</RouterLink>
```

### 1.4 编程式导航

```ts
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

router.push('/home')
router.push({ name: 'UserDetail', params: { id: 1 } })
router.push({ path: '/search', query: { keyword: 'vue' } })
router.replace('/login')   // 不留历史
router.back()              // 后退
router.go(-1)              // 前进/后退 N 步

// 当前路由信息
console.log(route.path, route.query, route.params)
```

### 1.5 导航守卫

```ts
// 全局前置守卫：每次跳转前都会执行
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')  // 重定向到登录
  } else {
    next()
  }
})

// 路由独享守卫
{ path: '/admin', component: Admin, beforeEnter: (to, from, next) => {...} }

// 组件内守卫
onBeforeRouteEnter((to, from, next) => { /* 进入前 */ })
onBeforeRouteUpdate((to, from) => { /* 当前路由变化但组件复用 */ })
onBeforeRouteLeave((to, from) => { /* 离开前 */ })
```

### 1.6 动态路由

```ts
// 登录后根据用户权限动态添加路由
const userMenus = await fetchMenus(userId)

userMenus.forEach(menu => {
  router.addRoute({
    path: menu.path,
    name: menu.name,
    component: () => import(`@/views${menu.component}.vue`),
    meta: { title: menu.title }
  })
})
```

## 2. 代码示例

### 2.1 基础路由配置

```ts
// router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue')
    },
    {
      path: '/users',
      name: 'Users',
      component: () => import('@/views/Users.vue')
    }
  ]
})

export default router
```

### 2.2 嵌套路由 + Layout

```ts
{
  path: '/system',
  component: () => import('@/layout/SystemLayout.vue'),
  children: [
    { path: 'user', component: () => import('@/views/system/User.vue') },
    { path: 'role', component: () => import('@/views/system/Role.vue') }
  ]
}
```

```vue
<!-- SystemLayout.vue -->
<template>
  <div>
    <Sidebar />
    <main>
      <RouterView />  <!-- 子路由出口 -->
    </main>
  </div>
</template>
```

### 2.3 登录守卫

```ts
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.path === '/login') return next()

  if (!token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})
```

### 2.4 常见错误：动态路由刷新丢失

```ts
// ❌ 错误：动态 addRoute 后，刷新页面路由丢失
// 因为刷新时 Vue 实例重建，路由表回到初始

// ✅ 正确：在路由守卫中先"恢复"动态路由
router.beforeEach(async (to, from, next) => {
  if (!store.state.menusLoaded) {
    await store.dispatch('loadMenus')
    // 内部已 addRoute
    next({ ...to, replace: true })  // 用 replace 重新跳一次
  } else {
    next()
  }
})
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 约定式文件结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/`

虽然本仓库的 vue3 目录只包含 `src/api` 和 `src/views` 的 MES 模块，但根据 ruoyi 的通用约定（基于 yudao-ui-admin-vue3 公开仓库 https://github.com/yudaocode/yudao-ui-admin-vue3）：

```
src/
├── api/             # 接口定义（每个业务模块一个目录）
├── views/           # 页面组件（对应路由的 component）
├── router/          # 路由配置
│   ├── index.ts     # 路由入口
│   └── modules/     # 按业务模块拆分路由
├── layout/          # 整体布局
├── components/      # 全局组件
├── store/           # Pinia 状态
└── utils/           # 工具函数
```

### 3.2 典型路由配置（基于公开仓库约定）

```ts
// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const Layout = () => import('@/layout/index.vue')

export const constantRoutes = [
  { path: '/login', component: () => import('@/views/Login.vue') },
  { path: '/404', component: () => import('@/views/Error/404.vue') },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        component: () => import('@/views/Dashboard.vue'),
        name: 'Dashboard',
        meta: { title: '首页', icon: 'dashboard' }
      }
    ]
  }
]

export const dynamicRoutes = [
  // 登录后根据用户权限动态添加
]

const router = createRouter({
  history: createWebHistory(),
  routes: constantRoutes
})

export default router
```

### 3.3 菜单驱动的动态路由（核心模式）

ruoyi 的动态菜单流程：

```
用户登录
  ↓
后端返回菜单树（含 component 路径）
  ↓
前端 addRoute 动态注册
  ↓
侧边栏根据路由 meta.icon/title 渲染
  ↓
访问无权限路由 → 重定向到 404
```

典型实现（基于约定）：

```ts
// src/utils/routerHelper.ts
import { addRoute } from '@/router'

// 把后端菜单转成路由记录
export function generateRoutes(menus: MenuVO[]) {
  menus.forEach(menu => {
    const route = {
      path: menu.path,
      name: menu.name,
      component: menu.component.startsWith('Layout')
        ? Layout
        : () => import(`@/views${menu.component}.vue`),
      meta: { title: menu.title, icon: menu.icon, permissions: menu.perms }
    }
    addRoute(route)
  })
}
```

### 3.4 与本仓库代码的对照

本仓库 `src/views/mes/wm/sn/index.vue` 是**叶子页面**（不含 `<RouterView>`），它的路由配置大致是：

```ts
{
  path: '/mes/wm-sn',
  component: Layout,
  children: [
    {
      path: '',
      component: () => import('@/views/mes/wm/sn/index.vue'),
      name: 'MesWmSn',
      meta: { title: 'SN 码管理', icon: 'ep:histogram', permissions: ['mes:wm-sn:query'] }
    }
  ]
}
```

## 4. 关键要点总结

- `createRouter` + `createWebHistory` 是 Vue Router 4 的标准写法
- 路由懒加载：`component: () => import('@/views/...')`
- 3 种传参：path 动态段、query（URL 可见）、name + params
- 导航守卫：`beforeEach` 全局、`beforeEnter` 路由级、`onBeforeRouteLeave` 组件级
- ruoyi 的核心模式：**后端返回菜单 → 前端动态 addRoute → 侧边栏按路由 meta 渲染**
- 动态路由刷新丢失：用"路由恢复守卫 + `next({...to, replace: true})`"解决

## 5. 练习题

### 练习 1：基础（必做）

搭建一个最小 Vue3 + Vue Router 项目：路由 `/`（首页）、`/about`（关于）、`/user/:id`（用户详情），首页有导航链接，详情页显示 `route.params.id`。

### 练习 2：进阶

为 SN 码管理页设计完整路由（嵌套在 Layout 下），meta 中声明 `permissions: ['mes:wm-sn:query']`。模拟一个 `beforeEach` 守卫：没有该权限直接跳 401 页面。

### 练习 3：挑战（选做）

实现完整的"动态路由 + 刷新恢复"流程：登录 → 获取菜单 → addRoute → 路由守卫中持久化菜单 → 刷新页面时从 localStorage 恢复路由。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
- yudao-ui-admin-vue3 公开仓库：https://github.com/yudaocode/yudao-ui-admin-vue3
- Vue Router 4 官方文档：https://router.vuejs.org/zh/

---

**文档版本**：v1.0
**最后更新**：2026-07-13