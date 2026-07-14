# 11.6.2 动态菜单与路由

> 掌握 ruoyi 的动态菜单方案：登录后从后端拉菜单树 → 前端动态注册路由 → 侧边栏按路由渲染。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 的"后端返回菜单"模式
- 掌握菜单树转 Vue Router 配置的算法
- 实现动态 `router.addRoute`
- 处理路由刷新丢失问题

## 📚 前置知识

- 11-frontend/05-vue-router.md
- 11-frontend/06-pinia.md
- 11-frontend/23-ruoyi-vue3-structure.md

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 菜单数据来源

虽然本仓库的 vue3 子项目是独立仓库，但菜单数据来源是后端接口 `/system/user/get-info`，**返回字段在所有 5 个子项目都一致**。

### 3.2 侧边栏组件约定

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/layout/components/Sidebar/SidebarItem.vue`（约定）

```vue
<script setup lang="ts">
interface MenuItem {
  id: number
  name: string
  path: string
  icon?: string
  children?: MenuItem[]
  hidden?: boolean
}

interface Props {
  item: MenuItem
  basePath: string
}

const props = defineProps<Props>()

// 只显示一个子项时，直接显示子项（不留目录）
const showChildren = computed(() => {
  return props.item.children?.length !== 1
})

const onlyChild = computed(() => {
  if (props.item.children?.length === 1) {
    return { ...props.item.children[0], path: resolvePath(props.item.children[0].path) }
  }
  return null
})

function resolvePath(routePath: string) {
  if (/^https?:/.test(routePath)) return routePath
  if (/^https?:/.test(props.basePath)) return props.basePath
  return path.resolve(props.basePath, routePath)
}
</script>

<template>
  <!-- 隐藏菜单不渲染 -->
  <template v-if="!item.hidden">
    <!-- 没有子菜单或只有一个子菜单且不显示父级 -->
    <template v-if="showChildren && (!item.children || item.children.length === 0)">
      <el-menu-item :index="resolvePath(item.path)">
        <Icon v-if="item.icon" :icon="item.icon" />
        <template #title>{{ item.name }}</template>
      </el-menu-item>
    </template>

    <!-- 只有一个子菜单 -->
    <el-menu-item v-else-if="onlyChild" :index="onlyChild.path">
      <Icon v-if="onlyChild.icon" :icon="onlyChild.icon" />
      <template #title>{{ onlyChild.name }}</template>
    </el-menu-item>

    <!-- 多个子菜单 -->
    <el-sub-menu v-else :index="resolvePath(item.path)">
      <template #title>
        <Icon v-if="item.icon" :icon="item.icon" />
        <span>{{ item.name }}</span>
      </template>
      <SidebarItem
        v-for="child in item.children"
        :key="child.id"
        :item="child"
        :base-path="resolvePath(item.path)"
      />
    </el-sub-menu>
  </template>
</template>
```

**解读**：
- 第 17-19 行：只有一个子菜单时，直接渲染子菜单（不显示父级目录）
- 第 33 行：用 `<SidebarItem>` 递归渲染（多级菜单）
- 第 39-44 行：`<el-sub-menu>` 渲染目录
- 第 22-28 行：`<el-menu-item>` 渲染叶子菜单

### 3.3 与本仓库代码的关联

本仓库 `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue` 是 **SN 码菜单**对应的页面，在侧边栏菜单树中表现为：

```
MES（顶级目录）
└── 仓库管理（子目录）
    └── SN 码管理（叶子菜单）
        └── component: mes/wm/sn/index.vue
        └── path: /mes/wm-sn
        └── perms: ['mes:wm-sn:query']
```

## 4. 关键要点总结

- **菜单数据**：登录后从 `/system/user/get-info` 拉取
- **核心流程**：登录 → 拉菜单 → 转路由 → `addRoute` → 渲染侧边栏
- **关键技巧**：`next({ ...to, replace: true })` 解决刷新路由丢失
- **侧边栏组件**：递归渲染，支持目录+叶子
- **菜单树结构**：parentId / id / children 三级
- **perms 字段**：用于按钮级权限控制（v-hasPermi）

## 5. 练习题

### 练习 1：基础（必做）

为 SN 码项目模拟一个菜单树：

```ts
const menus = [
  {
    id: 1, name: 'MES', path: '/mes', component: 'Layout',
    children: [
      { id: 11, name: 'SN 码管理', path: 'sn', component: 'mes/wm/sn/index' }
    ]
  }
]
```

并把它转为 Vue Router 配置。

### 练习 2：进阶

实现"菜单搜索"功能：在侧边栏顶部加一个搜索框，输入关键字过滤菜单（只显示匹配项及其父级）。

### 练习 3：挑战（选做）

实现"菜单拖拽排序"：管理员可以拖拽菜单调整顺序，提交后调 `api.updateMenuSort` 持久化。

## 6. 参考资料

- yudao-ui-admin-vue3 公开约定：https://github.com/yudaocode/yudao-ui-admin-vue3
- Vue Router 4 `addRoute`：https://router.vuejs.org/zh/api/#addroute

---

**文档版本**：v1.0
**最后更新**：2026-07-13