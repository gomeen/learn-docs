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
- 动态菜单路由（ruoyi，详见 [菜单动态路由](./29-ruoyi-menu.md)）

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

## 3. 关键要点总结

- `createRouter` + `createWebHistory` 是 Vue Router 4 的标准写法
- 路由懒加载：`component: () => import('@/views/...')`
- 3 种传参：path 动态段、query（URL 可见）、name + params
- 导航守卫：`beforeEach` 全局、`beforeEnter` 路由级、`onBeforeRouteLeave` 组件级
- ruoyi 的核心模式：**后端返回菜单 → 前端动态 addRoute → 侧边栏按路由 meta 渲染**
- 动态路由刷新丢失：用"路由恢复守卫 + `next({...to, replace: true})`"解决

---

**文档版本**：v1.0
**最后更新**：2026-07-13
