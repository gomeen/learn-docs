# 11.7.1 uni-app 基础

> 掌握 uni-app 跨端开发框架，能用 Vue 语法开发小程序、H5、App。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 uni-app 的跨端原理（编译时转换）
- 掌握 uni-app 的常用 API（页面、组件、网络）
- 区分 uni-app 与 Vue 的差异
- 在 ruoyi 中使用 uni-app 开发移动端

## 📚 前置知识

- 11-frontend/01-vue3-basics.md
- Vue 3 组合式 API 基础

## 1. 核心概念

### 1.1 什么是 uni-app？

uni-app 是 DCloud 推出的**跨端框架**，基于 Vue 语法，**一套代码可编译到多个平台**：

| 平台 | 输出 |
|------|------|
| 微信小程序 | .wxml + .wxss + .js |
| 支付宝小程序 | .axml + .acss |
| 抖音小程序 | .ttml + .ttss |
| H5 | 浏览器 SPA |
| Android/iOS App | 原生 App（基于 WebView 或 uni-app x） |
| 各类快应用 | … |

### 1.2 uni-app 的特点

**优势**：
- Vue 语法（Vue 2 / Vue 3 都支持）
- 一码多端（开发效率高）
- 生态丰富（插件市场 9000+）
- 性能接近原生（小程序端）

**劣势**：
- 平台差异需要适配（每个端 API 有差异）
- 部分新特性受限（依赖底层框架）

### 1.3 uni-app 与 Vue 的差异

```vue
<!-- 差异点 -->
<script setup>
import { ref } from 'vue'

const userInfo = ref({ name: 'tom' })

// 1. 页面用 onLoad 替代 onMounted
onLoad(() => {
  console.log('页面加载')
})

// 2. 用 uni.request 替代 axios
const fetchUser = async () => {
  const res = await uni.request({ url: '/api/user', method: 'GET' })
  return res.data
}

// 3. 用 uni.navigateTo 替代 router.push
const goToDetail = (id: number) => {
  uni.navigateTo({ url: `/pages/user/detail?id=${id}` })
}
</script>
```

### 1.4 uni-app 三种语法

| 语法 | Vue 版本 | 适用 |
|------|---------|------|
| Vue 2 + 选项式 API | Vue 2 | 老项目 |
| Vue 3 + 组合式 API | Vue 3 | **推荐** |
| TypeScript | Vue 2/3 | 大型项目 |

ruoyi 的 yudao-ui-admin-uniapp 用 **Vue 3 + TypeScript + 组合式 API**。

### 1.5 uni-app 生命周期

```ts
// 应用生命周期（App.vue）
onLaunch(() => { /* 启动 */ })
onShow(() => { /* 从后台进入前台 */ })
onHide(() => { /* 进入后台 */ })

// 页面生命周期（页面 .vue）
onLoad((options) => { /* 加载，options 是 URL 参数 */ })
onShow(() => { /* 显示 */ })
onReady(() => { /* 首次渲染完成 */ })
onPullDownRefresh(() => { /* 下拉刷新 */ })
onReachBottom(() => { /* 上拉触底 */ })
```

### 1.6 uni-app API 分类

```ts
// 网络请求
uni.request({ url, method, data, header, success, fail })

// 页面跳转
uni.navigateTo({ url: '/pages/detail?id=1' })
uni.redirectTo({ url: '/pages/login' })
uni.switchTab({ url: '/pages/index' })
uni.navigateBack({ delta: 1 })

// 数据存储
uni.setStorageSync('key', 'value')
uni.getStorageSync('key')
uni.removeStorageSync('key')

// 系统信息
uni.getSystemInfo({ success: (res) => { ... } })

// 弹窗
uni.showToast({ title: '保存成功', icon: 'success' })
uni.showModal({ title: '提示', content: '确定删除？' })
uni.showActionSheet({ itemList: ['A', 'B', 'C'] })
```

## 2. 代码示例

### 2.1 uni-app 页面基本结构

```vue
<!-- pages/index/index.vue -->
<script setup lang="ts">
import { ref } from 'vue'

const count = ref(0)

onLoad(() => {
  console.log('页面加载')
})

onPullDownRefresh(() => {
  count.value = 0
  uni.stopPullDownRefresh()
})
</script>

<template>
  <view class="container">
    <text>当前计数：{{ count }}</text>
    <button @click="count++">+1</button>
  </view>
</template>

<style scoped>
.container { padding: 20px; }
</style>
```

### 2.2 跨端请求封装

```ts
// utils/request.ts
export function request<T = any>(options: UniApp.RequestOptions): Promise<T> {
  return new Promise((resolve, reject) => {
    uni.request({
      ...options,
      header: {
        'Authorization': `Bearer ${uni.getStorageSync('token')}`,
        ...options.header
      },
      success: (res) => {
        if (res.statusCode === 200) {
          const data = res.data as any
          if (data.code === 0) resolve(data.data)
          else {
            uni.showToast({ title: data.msg, icon: 'none' })
            reject(data)
          }
        } else {
          reject(res)
        }
      },
      fail: (err) => {
        uni.showToast({ title: '网络异常', icon: 'none' })
        reject(err)
      }
    })
  })
}
```

### 2.3 页面跳转传参

```vue
<!-- A 页面 -->
<script setup>
const goToDetail = (id: number) => {
  uni.navigateTo({ url: `/pages/user/detail?id=${id}` })
}
</script>

<!-- B 页面 -->
<script setup>
import { ref } from 'vue'

const userId = ref(0)
const userInfo = ref()

onLoad((options) => {
  userId.value = Number(options.id)
  fetchUser()
})

async function fetchUser() {
  userInfo.value = await request({ url: `/user/${userId.value}` })
}
</script>
```

### 2.4 条件编译：处理平台差异

```vue
<!-- #ifdef MP-WEIXIN -->
<button open-type="share">分享</button>
<!-- #endif -->

<!-- #ifdef H5 -->
<button @click="copyLink">复制链接</button>
<!-- #endif -->
```

```ts
// JS 中的条件编译
// #ifdef MP-WEIXIN
const shareInfo = uni.getShareInfo()
// #endif

// #ifdef H5
const url = window.location.href
// #endif
```

### 2.5 常见错误：用 DOM API

```vue
<!-- ❌ 错误：uni-app 没有 DOM，document.querySelector 会报错 -->
<script setup>
onMounted(() => {
  document.querySelector('#app')  // ❌ 报错
})
</script>

<!-- ✅ 正确：用 ref + 组件实例 -->
<template>
  <view ref="containerRef">Hello</view>
</template>
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 uni-app 子项目位置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-uniapp/`

本仓库的 uni-app 子项目是独立仓库（只有 README.md）。完整代码：

```
# Gitee: https://gitee.com/yudaocode/yudao-ui-admin-uniapp
# GitHub: https://github.com/yudaocode/yudao-ui-admin-uniapp
```

### 3.2 项目结构约定

```
yudao-ui-admin-uniapp/
├── src/
│   ├── api/                  # 接口定义（与 Vue3/Vben 一致）
│   ├── components/           # 组件
│   ├── pages/                # 页面
│   │   ├── index/
│   │   ├── login/
│   │   ├── user/
│   │   └── ...
│   ├── static/               # 静态资源
│   ├── store/                # Pinia store
│   ├── utils/                # 工具函数
│   ├── App.vue               # 应用配置
│   ├── main.ts               # 入口
│   ├── pages.json            # 页面路由配置
│   └── manifest.json         # 应用配置（小程序 AppID 等）
├── package.json
├── vite.config.ts
└── tsconfig.json
```

### 3.3 pages.json：路由配置

```json
{
  "pages": [
    { "path": "pages/index/index", "style": { "navigationBarTitleText": "首页" } },
    { "path": "pages/login/index", "style": { "navigationBarTitleText": "登录" } },
    { "path": "pages/user/index", "style": { "navigationBarTitleText": "我的" } }
  ],
  "tabBar": {
    "list": [
      { "pagePath": "pages/index/index", "text": "首页" },
      { "pagePath": "pages/user/index", "text": "我的" }
    ]
  }
}
```

### 3.4 与本仓库代码的关联

虽然本仓库 `yudao-ui-admin-uniapp` 是独立仓库，但接口约定一致：

```ts
// yudao-ui-admin-uniapp/src/api/mes/wm/sn/index.ts
import request from '@/utils/request'

export const getSnPage = (params: any) => {
  return request({ url: '/mes/wm/sn/page', method: 'GET', data: params })
}
```

**URL 与 Vue3 版本完全一致**，只把 axios 换成 uni.request 封装。

## 4. 关键要点总结

- uni-app = Vue 语法 + 跨端编译（小程序、H5、App）
- 三个核心差异：API（uni.request）、页面（onLoad）、跳转（uni.navigateTo）
- 路由配置在 `pages.json`，不是 Vue Router
- 跨端差异用条件编译 `#ifdef MP-WEIXIN`
- 不要用 DOM API
- ruoyi 的 uni-app 版本接口 URL 与其他前端一致

## 5. 练习题

### 练习 1：基础（必做）

用 uni-app 创建一个简单的登录页：账号、密码、登录按钮。点击登录后跳转到首页（带 token 模拟）。

### 练习 2：进阶

实现一个商品列表页：上拉加载更多（`onReachBottom`）、下拉刷新（`onPullDownRefresh`）。

### 练习 3：挑战（选做）

用条件编译实现"分享到微信"功能：
- 仅在 `MP-WEIXIN` 平台显示分享按钮
- 点击调 `uni.showShareMenu` 开启分享

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-uniapp/`
- uni-app 官方文档：https://uniapp.dcloud.net.cn/
- yudao-ui-admin-uniapp 公开仓库：https://github.com/yudaocode/yudao-ui-admin-uniapp

---

**文档版本**：v1.0
**最后更新**：2026-07-13