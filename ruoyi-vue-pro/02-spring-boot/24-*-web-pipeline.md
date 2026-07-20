# 小验证：异常处理 / 拦截器 / Filter / ruoyi Web

> 覆盖：
- [全局异常](./20-exception-handler.md)
- [拦截器](./21-interceptor.md)
- [过滤器](./22-filter.md)
- [ruoyi Web 配置](./23-ruoyi-web.md)
>
> 预计：30～45 分钟 · 改 ruoyi-vue-pro 仓库

## 背景

统一异常与拦截器链决定了“失败时长什么样、请求前后做了什么”。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro`（可接续 `19-*-web-layer` 的 DemoController）：

1. 在 echo 接口中，空 `name` 时抛业务异常（用项目现有 `ServiceException` / ErrorCode 风格）。
2. 触发一次参数/业务异常，确认走全局异常处理，而不是 Tomcat 默认页；对比成功/失败 JSON。
3. 阅读并记录：项目中 `HandlerInterceptor` / `Filter` 至少各一处的类名与职责（如租户、访问日志、CORS）。
4. 说明 Filter 与 Interceptor 在 ruoyi 中的大致顺序。
5. 定位 Web 配置类（CORS、消息转换、路径前缀等任选），记下路径。

## 提示

- 全局异常处理器一般在 framework 的 web 包。
- 本地放行 demo 路径便于调试。
- 不要提交测试用弱安全配置。

## 验收标准

- [ ] 异常响应格式与项目其它接口一致
- [ ] 成功与失败两种响应均可复现
- [ ] 记录至少 1 个 Filter + 1 个 Interceptor 的职责
- [ ] 说明 Filter 与 Interceptor 的大致顺序
- [ ] Web 配置类路径已定位

## 延伸（选做）

- 给 demo 接口加 `@PreAuthorize` 并验证无权限 403。
- 写一个 `OncePerRequestFilter` 打印 traceId（注意注册位置）。
