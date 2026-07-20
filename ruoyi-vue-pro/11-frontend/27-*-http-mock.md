# 小验证：Axios 封装 / 拦截器 / Swagger / Mock

> 覆盖：
- [Axios 封装](./23-axios.md)
- [拦截器](./24-interceptor.md)
- [Swagger](./25-swagger.md)
- [Mock](./26-mock.md)
>
> 预计：30～45 分钟 · 改 yudao-ui 仓库

## 背景

读 yudao-ui 的请求层比从零造轮子更重要：Token、401、错误提示与类型化 API。

## 需求

在 yudao-ui-admin-vue3：

1. 找到 Axios 封装与请求/响应拦截器：Token 注入、401 处理、错误提示。
2. 本地代理成功请求一个真实接口（如获取用户信息）。
3. 找到 Swagger/OpenAPI 入口，用其辅助写一个 API TS 方法。
4. 说明项目 Mock 方案（vite-plugin-mock / 其它）或如何关闭 mock。
5. 给新增 API 方法补上返回类型。

## 提示

- 代理路径与 Token Header 以项目为准。
- 401 处理可能触发登出，注意测试账号。
- 不要提交本地 token。

## 验收标准

- [ ] 拦截器职责说明正确
- [ ] 本地代理请求成功
- [ ] 新增/定位一个 API 方法有类型
- [ ] Mock 方案说明清楚
- [ ] 错误提示链路可描述

## 延伸（选做）

- 加响应 mock 切换。
- 封装一个通用 `getPage` 泛型方法。
