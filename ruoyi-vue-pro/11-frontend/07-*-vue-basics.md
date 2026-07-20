# 小验证：Vue3 基础：组件 / 路由 / Pinia

> 覆盖：
- [组合式 API](./01-vue3-basics.md)
- [computed / watch](./02-computed-watch.md)
- [生命周期](./03-lifecycle.md)
- [组件通信](./04-component.md)
- [Vue Router](./05-vue-router.md)
- [Pinia](./06-pinia.md)
>
> 预计：45～75 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

用最小 Vue3 页面验证组合式 API 与状态路由，为读 yudao-ui 打底。

## 需求

本地 Vite + Vue3 小项目（或在 yudao-ui 中加 demo 页）：

1. 页面：输入名称，computed 显示问候语；watch 变化打日志。
2. 子组件通过 props/emits 回传点击次数。
3. Pinia store 保存计数，跨两个路由页面共享。
4. 路由：`/demo` 与 `/demo/about`，其一使用路由参数。

## 提示

- 优先 `<script setup lang="ts">`。
- 不要污染现有业务路由权限；demo 可放本地未提交分支。

## 验收标准

- [ ] computed/watch 行为正确
- [ ] 组件通信成功
- [ ] Pinia 跨页状态保持
- [ ] 路由跳转与参数可读
- [ ] 页面无控制台报错

## 延伸（选做）

- 用 provide/inject 传主题色。
- 路由守卫模拟登录重定向。
