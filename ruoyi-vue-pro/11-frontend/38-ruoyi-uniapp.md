# 11.7.2 yudao-ui-admin-uniapp 项目结构

> 深入了解 yudao-ui-admin-uniapp 的项目结构、模块划分、与 PC 端的差异。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 yudao-ui-admin-uniapp 的目录结构
- 理解移动端特有的模块（登录、扫码、消息推送）
- 区分与 PC 端（Vue3）的差异
- 掌握 uni-app 的多端构建配置

## 📚 前置知识

- uni-app（详见 [uni-app](./37-uniapp.md)）
- Vue3 结构（详见 [Vue3 结构](./28-ruoyi-vue3-structure.md)）
- 会员认证（详见 [会员认证](../07-business-modules/24-member-auth.md)）

## 1. 核心概念

### 1.1 项目定位

`yudao-ui-admin-uniapp` 是 ruoyi-vue-pro 的**移动端**前端，基于 **uni-app + Vue 3 + TypeScript**：

| 维度 | PC 端（yudao-ui-admin-vue3） | 移动端（yudao-ui-admin-uniapp） |
|------|---------------------------|-----------------------------|
| 框架 | Vue 3 + Vite | Vue 3 + uni-app |
| UI | Element Plus | uView Plus / uni-ui |
| 路由 | Vue Router | pages.json |
| 平台 | 浏览器 | 微信小程序、H5、App |
| 状态 | Pinia | Pinia |

### 1.2 顶层结构

```
yudao-ui-admin-uniapp/
├── src/
│   ├── api/                    # 接口定义（与 PC 端一致）
│   ├── components/             # 全局组件
│   ├── composables/            # 组合式函数
│   ├── pages/                  # 页面（按业务模块）
│   │   ├── index/              # 首页
│   │   ├── login/              # 登录
│   │   ├── user/               # 我的
│   │   └── ...
│   ├── static/                 # 静态资源
│   ├── store/                  # Pinia store
│   ├── utils/                  # 工具函数
│   ├── App.vue                 # 应用入口
│   ├── main.ts                 # 入口文件
│   ├── manifest.json           # 应用配置
│   └── pages.json              # 路由配置
├── package.json
└── tsconfig.json
```

### 1.3 src/pages/ 模块组织

uni-app 的页面就是路由，目录结构：

```
src/pages/
├── index/                     # 首页 Tab
│   ├── index.vue              # 首页
│   └── components/
├── login/                     # 登录页
│   ├── index.vue
│   ├── sms-login.vue          # 短信登录
│   └── oauth-login.vue        # 第三方登录
├── user/                      # 我的 Tab
│   ├── index.vue              # 个人中心
│   ├── profile.vue            # 资料
│   └── settings.vue           # 设置
├── mes/                       # MES 业务
│   ├── wm/
│   │   ├── sn/
│   │   │   ├── list.vue       # SN 码列表
│   │   │   └── detail.vue     # SN 码详情
│   │   └── productrecpt/
│   │       ├── list.vue
│   │       └── detail.vue
│   └── ...
└── ...
```

### 1.4 src/store/modules/

```
src/store/modules/
├── user.ts                    # 用户信息、token
├── app.ts                     # 应用配置
└── dict.ts                    # 字典
```

### 1.5 pages.json 路由配置

```json
{
  "pages": [
    {
      "path": "pages/index/index",
      "style": {
        "navigationBarTitleText": "芋道管理",
        "navigationBarBackgroundColor": "#1989fa",
        "enablePullDownRefresh": true
      }
    },
    {
      "path": "pages/login/index",
      "style": { "navigationBarTitleText": "登录" }
    }
  ],
  "tabBar": {
    "color": "#999",
    "selectedColor": "#1989fa",
    "list": [
      { "pagePath": "pages/index/index", "text": "首页", "iconPath": "static/tabbar/home.png" },
      { "pagePath": "pages/user/index", "text": "我的", "iconPath": "static/tabbar/user.png" }
    ]
  }
}
```

### 1.6 移动端特有的功能模块

| 模块 | 用途 |
|------|------|
| 扫码登录 | App 扫 PC 端二维码登录 |
| 手机验证码 | 短信验证码登录 |
| 推送集成 | 集成个推 / 极光推送 |
| 定位 | 获取用户位置（考勤、外勤） |
| 拍照上传 | 调用摄像头拍照上传 |
| 通讯录 | 调通讯录选择联系人 |
| 微信支付 / 支付宝 | 集成支付 SDK |

## 2. 代码示例

### 2.1 接口定义（与 PC 端一致）

```ts
// src/api/mes/wm/sn/index.ts
import request from '@/utils/request'

// SN 码 VO
export interface WmSnVO {
  id: number
  snCode: string
  itemId: number
  itemCode: string
  itemName: string
  // ...
}

export const getSnPage = (params: any) => {
  return request({ url: '/mes/wm/sn/page', method: 'GET', data: params })
}

export const generateSnCodes = (data: WmSnVO) => {
  return request({ url: '/mes/wm/sn/generate', method: 'POST', data })
}
```

### 2.2 移动端列表页

```vue
<!-- src/pages/mes/wm/sn/list.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { getSnPage, type WmSnVO } from '@/api/mes/wm/sn'

const list = ref<WmSnVO[]>([])
const loading = ref(false)
const finished = ref(false)
const pageNo = ref(1)

async function loadMore() {
  loading.value = true
  try {
    const res = await getSnPage({ pageNo: pageNo.value, pageSize: 10 })
    list.value.push(...res.list)
    pageNo.value++
    if (list.value.length >= res.total) finished.value = true
  } finally {
    loading.value = false
  }
}

function onRefresh() {
  list.value = []
  pageNo.value = 1
  finished.value = false
  loadMore()
}

onMounted(loadMore)
onPullDownRefresh(onRefresh)
onReachBottom(() => !finished.value && !loading.value && loadMore())
</script>

<template>
  <view class="page">
    <view v-for="item in list" :key="item.id" class="card">
      <view class="title">{{ item.snCode }}</view>
      <view class="desc">{{ item.itemName }} - {{ item.specification }}</view>
      <view class="time">{{ item.createTime }}</view>
    </view>
    <view v-if="loading" class="loading">加载中...</view>
    <view v-if="finished" class="finished">没有更多了</view>
  </view>
</template>

<style scoped>
.page { padding: 20rpx; }
.card { background: white; padding: 24rpx; margin-bottom: 20rpx; border-radius: 16rpx; }
.title { font-size: 32rpx; font-weight: bold; }
.desc { color: #666; margin-top: 8rpx; }
.time { color: #999; font-size: 24rpx; margin-top: 8rpx; }
</style>
```

### 2.3 用户 store

```ts
// src/store/modules/user.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const token = ref('')
  const userInfo = ref({})

  async function login(form: any) {
    const res = await request({ url: '/system/auth/login', method: 'POST', data: form })
    token.value = res.token
    uni.setStorageSync('token', res.token)
  }

  function logout() {
    token.value = ''
    uni.removeStorageSync('token')
    uni.reLaunch({ url: '/pages/login/index' })
  }

  return { token, userInfo, login, logout }
})
```

### 2.4 移动端特有的扫码功能

```vue
<!-- 扫一扫按钮 -->
<script setup>
function onScan() {
  // #ifdef MP-WEIXIN
  uni.scanCode({
    success: (res) => {
      console.log('扫到内容:', res.result)
      // 用扫码结果查 SN 码
      fetchSnByCode(res.result)
    }
  })
  // #endif

  // #ifdef APP-PLUS
  plus.barcode.scan('', (type, code) => {
    console.log('扫到内容:', code)
  })
  // #endif
}
</script>

<template>
  <view class="scan-btn" @click="onScan">
    <text>📷 扫码查询</text>
  </view>
</template>
```

### 2.5 移动端列表常见的"下拉刷新 + 上拉加载"

```vue
<script setup>
const list = ref([])
const loading = ref(false)
const finished = ref(false)
const pageNo = ref(1)

onLoad(() => {
  loadMore()
})

// 下拉刷新
onPullDownRefresh(() => {
  list.value = []
  pageNo.value = 1
  finished.value = false
  loadMore().then(() => uni.stopPullDownRefresh())
})

// 上拉触底
onReachBottom(() => {
  if (!finished.value && !loading.value) loadMore()
})

async function loadMore() {
  loading.value = true
  try {
    const res = await getList({ pageNo: pageNo.value, pageSize: 10 })
    list.value.push(...res.list)
    pageNo.value++
    if (list.value.length >= res.total) finished.value = true
  } finally {
    loading.value = false
  }
}
</script>
```

### 2.6 常见错误：单位用 px

```vue
<!-- ❌ 错误：在小程序中，px 会很小 -->
<style>
.card { padding: 16px; font-size: 14px; }
</style>

<!-- ✅ 正确：用 rpx（小程序自适应单位，750rpx = 屏幕宽度） -->
<style>
.card { padding: 32rpx; font-size: 28rpx; }
</style>
```

## 3. 关键要点总结

- yudao-ui-admin-uniapp = uni-app + Vue 3 + TypeScript + Pinia
- 接口定义 URL 与 PC 端完全一致
- 路由配置在 `pages.json`，不是 Vue Router
- 移动端特有功能：扫码、定位、推送、拍照上传
- 列表模式：下拉刷新 + 上拉加载更多
- 单位用 `rpx`（小程序自适应），不用 `px`
- 跨端用条件编译 `#ifdef MP-WEIXIN`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
