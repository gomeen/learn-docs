# 11.3.5 组件库对比与选型

> 对比主流 Vue3 组件库（Element Plus、ant-design-vue、Naive UI、Vuetify），帮助在 ruoyi 生态下做选型决策。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出主流 Vue3 组件库的优缺点
- 区分它们的 API 风格、设计语言、适用场景
- 在 ruoyi 体系下做正确的选型决策
- 理解 ruoyi 为何默认选择 Element Plus / Vben

## 📚 前置知识

- Element Plus（详见 [Element Plus](./10-element-plus.md)）
- Vben（详见 [Vben](./13-vben.md)）

## 1. 核心概念

### 1.1 主流 Vue3 组件库一览

| 组件库 | 维护方 | 风格 | 适用场景 |
|--------|-------|------|---------|
| **Element Plus** | 饿了么 | 现代、简洁 | 中后台、SaaS、ruoyi 默认 |
| **ant-design-vue** | Ant Design 团队 | 企业、商务 | 大型后台、复杂业务、ruoyi Vben 版本 |
| **Naive UI** | 尤雨溪推荐作者 | 现代、TypeScript 友好 | 重视 TS、设计精致 |
| **Vuetify** | Vuetify Team | Material Design | 海外项目 |
| **PrimeVue** | PrimeTek | 完整组件 | 数据密集型应用 |
| **Quasar** | Quasar Framework | 跨端 | 一套代码多端（Web + 移动） |
| **Arco Design Vue** | 字节跳动 | 现代、商务 | 字节系产品 |

### 1.2 4 大主流库详细对比

#### Element Plus
- **优势**：中文文档优秀、上手最快、社区庞大、ruoyi 默认
- **劣势**：组件定制能力不如 antd，主题风格偏现代
- **代表项目**：ruoyi-vue-pro Vue3 版、vue-element-admin

#### ant-design-vue
- **优势**：组件最丰富（100+）、企业级最佳实践、TypeScript 良好
- **劣势**：体积较大、学习曲线中等、中文社区较小
- **代表项目**：ruoyi-vue-pro Vben 版、Ant Design Pro

#### Naive UI
- **优势**：纯 Vue3 + TS，体积小、tree-shaking 友好、设计精致
- **劣势**：社区较小、第三方插件少
- **代表项目**：个人项目、对设计有要求的项目

#### Vuetify
- **优势**：Material Design 标准、海外认可度高
- **劣势**：风格单一（Material）、中文支持弱

### 1.3 选型维度

```
项目背景
├── 中文项目 vs 海外项目
├── To B 后台 vs To C 产品
├── 团队规模（个人/小团队/大团队）
├── 设计要求（精致 vs 实用）
└── 是否需要服务端配套（如 ruoyi）

技术约束
├── 是否需要 SSR（Nuxt）
├── 体积要求（移动端 H5 必须小）
├── 浏览器兼容性（IE11？必须 Vuetify）
└── TypeScript 要求
```

## 2. 代码示例：同一登录页 4 种写法

### 2.1 Element Plus

```vue
<template>
  <el-form :model="form" :rules="rules" label-width="80px">
    <el-form-item label="用户名" prop="username">
      <el-input v-model="form.username" />
    </el-form-item>
    <el-form-item label="密码" prop="password">
      <el-input v-model="form.password" type="password" />
    </el-form-item>
    <el-button type="primary" @click="login">登录</el-button>
  </el-form>
</template>
```

### 2.2 ant-design-vue

```vue
<template>
  <a-form :model="form" :rules="rules" :label-col="{ span: 6 }">
    <a-form-item label="用户名" name="username">
      <a-input v-model:value="form.username" />
    </a-form-item>
    <a-form-item label="密码" name="password">
      <a-input-password v-model:value="form.password" />
    </a-form-item>
    <a-button type="primary" @click="login">登录</a-button>
  </a-form>
</template>
```

### 2.3 Naive UI

```vue
<template>
  <n-form :model="form" :rules="rules" label-placement="left" label-width="80">
    <n-form-item label="用户名" path="username">
      <n-input v-model:value="form.username" />
    </n-form-item>
    <n-form-item label="密码" path="password">
      <n-input v-model:value="form.password" type="password" />
    </n-form-item>
    <n-button type="primary" @click="login">登录</n-button>
  </n-form>
</template>
```

### 2.4 Vuetify

```vue
<template>
  <v-form>
    <v-text-field v-model="form.username" label="用户名" :rules="[required]" />
    <v-text-field v-model="form.password" label="密码" type="password" :rules="[required]" />
    <v-btn color="primary" @click="login">登录</v-btn>
  </v-form>
</template>
```

## 3. 体积与性能

### 3.1 打包体积对比（全量引入）

```
ant-design-vue:  ~1.4MB (gzipped)
Element Plus:    ~1.1MB (gzipped)
Vuetify:         ~1.3MB (gzipped)
Naive UI:        ~0.5MB (gzipped)  ← 最小
Quasar:          ~0.8MB (gzipped)
```

### 3.2 按需加载

**全部组件库都支持按需加载**（unplugin-vue-components 或官方 babel 插件）：

```ts
// Vite + Element Plus
import { ElButton } from 'element-plus'
app.use(ElButton)
```

```ts
// Vite + ant-design-vue
import { Button } from 'ant-design-vue'
app.use(Button)
```

### 3.3 SSR 支持

| 组件库 | Nuxt 集成 |
|--------|----------|
| Element Plus | 良好（社区 nuxtjs element-plus） |
| ant-design-vue | 良好（官方推荐） |
| Naive UI | 优秀（原生支持） |
| Vuetify | 良好 |

## 4. ruoyi-vue-pro 仓库源码解读

### 4.1 ruoyi 提供的 4 套前端

```
yudao-ui/
├── yudao-ui-admin-vue3/        # Vue3 + Element Plus（最常用）
├── yudao-ui-admin-vben/        # Vue3 + ant-design-vue（大型项目）
├── yudao-ui-admin-vue2/        # Vue2 + Element UI（老项目维护）
├── yudao-ui-admin-uniapp/      # 移动端（uni-app + uView）
└── yudao-ui-mall-uniapp/       # 商城 H5
```

### 4.2 选型推荐

| 场景 | 推荐 | 理由 |
|------|------|------|
| 中小型后台 / 内部系统 | **yudao-ui-admin-vue3** | 上手快、中文文档、组件够用 |
| 大型企业级后台 | **yudao-ui-admin-vben** | 组件丰富、主题多样、设计专业 |
| 维护 Vue2 老项目 | **yudao-ui-admin-vue2** | 平滑迁移 |
| 移动端 App / 小程序 | **yudao-ui-admin-uniapp** | 跨端 |
| 商城 H5 | **yudao-ui-mall-uniapp** | 内置营销组件 |

### 4.3 与本仓库代码的对照

本仓库 `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue` 是 **Vue3 + Element Plus** 版本，使用了：
- `el-form`、`el-input`、`el-table`、`el-button`、`el-dialog`、`el-input-number`
- 二次封装：`ContentWrap`、`Pagination`、`<Icon>`、`useMessage`
- 自定义指令：`v-hasPermi`

如改用 Vben 版本，所有 `el-*` 替换为 `a-*`，但**后端接口完全不变**。

## 5. 选型决策树

```
需要 SSR 吗？
├── 是 → Naive UI（原生支持）/ Ant Design Vue（文档完善）
└── 否 ↓

是 To B 后台吗？
├── 是 → Element Plus（中文友好）/ Ant Design Vue（企业级）
└── 否 ↓

需要多端吗？（Web + App + 小程序）
├── 是 → uni-app + uView / Quasar
└── 否 ↓

设计要求高吗？
├── 是 → Naive UI
└── 否 ↓

默认 → Element Plus
```

## 6. 关键要点总结

- 国内主流：**Element Plus**、**ant-design-vue**、**Naive UI**
- ruoyi 默认：**Vue3 + Element Plus**（上手快）
- ruoyi 进阶：**Vben + ant-design-vue**（大型项目）
- 体积最小：**Naive UI**（纯 Vue3 + TS）
- 海外项目：**Vuetify**（Material Design）
- **核心原则**：选团队熟悉的，不要追新；后端 API 不变即可随时切换

## 7. 练习题

### 练习 1：基础（必做）

列出当前项目所在团队的 3 个真实需求场景（如内部 OA、电商后台、运营报表），分别为它们选择最合适的 Vue3 组件库并说明理由。

### 练习 2：进阶

把 SN 码管理页的 `el-table-column` 翻译为 ant-design-vue 的 `a-table-column`，对比 prop / dataIndex、formatter / customRender 等差异。

### 练习 3：挑战（选做）

基于现有项目（Element Plus）做一个"主题切换器"，允许切换 3 套主题：
1. 默认（蓝）
2. 商务（深绿）
3. 暗色

切换时通过 CSS 变量实时生效。

## 8. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/`
- Element Plus 官方：https://element-plus.org/
- Ant Design Vue：https://antdv.com/
- Naive UI：https://www.naiveui.com/
- Vuetify：https://vuetifyjs.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13