# 小验证：Controller / 映射 / 参数 / 统一返回

> 覆盖：
- [Controller](./15-controller.md)
- [请求映射](./16-request-mapping.md)
- [参数绑定](./17-param-binding.md)
- [统一返回](./18-result-wrapper.md)
>
> 预计：30～45 分钟 · 改 ruoyi-vue-pro 仓库

## 背景

ruoyi 的 Web 层有统一的 CommonResult。本验证加一个最小管理端接口并接上既有返回体系。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro` 的 system 或 infra 模块中：

1. 新增 `DemoController`（admin 包路径与现有 Controller 一致），提供：
   - `GET /admin-api/system/demo/ping` → 返回 `CommonResult.success("pong")`
   - `GET /admin-api/system/demo/echo?name=xx` → 绑定 `name` 查询参数
   - `POST /admin-api/system/demo/echo-body` → `@RequestBody` 接收简单 VO，返回其中字段
2. 确认响应被统一包装（对比现有接口 JSON 结构：`code`/`data`/`msg`）。
3. 用 curl 或 Knife4j/Swagger 调用上述接口（需登录则带 Token）。
4. 说明项目中 `@RestController` + 路径前缀（`admin-api`）是如何拼出来的。

## 提示

- 路径前缀以项目实际 `admin-api` 配置为准。
- 权限：可暂时用现有权限注解模式，或在 Security 配置中放行 demo 路径（仅本地）。
- 不要破坏现有 `CommonResult` 字段约定。

## 验收标准

- [ ] ping 返回统一成功结构且 data 为 pong
- [ ] query 与 body 两种绑定均可复现
- [ ] JSON 结构与项目其它接口一致
- [ ] 路径前缀拼接方式有说明
- [ ] 接口可在本地实际调用

## 延伸（选做）

- 给 VO 加校验注解（`@NotBlank`），为下一节异常处理铺垫。
- 补充 `@PathVariable` 版本的 echo。
