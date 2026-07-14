# 14 请求映射：@RequestMapping / @GetMapping

> 掌握 Spring MVC 的请求映射注解，能在 ruoyi-vue-pro 中正确编写 RESTful URL。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 `@RequestMapping`、`@GetMapping`、`@PostMapping`、`@PutMapping`、`@DeleteMapping`
- 掌握路径变量、Ant 风格通配符、参数条件
- 能在 ruoyi-vue-pro 中读懂 URL 路径前缀机制
- 理解 HTTP 方法的语义（GET 幂等、POST 非幂等）

## 📚 前置知识

- 13-controller.md

## 1. 核心概念

### 1.1 请求映射注解的层级关系

```
@RequestMapping
    ├── @GetMapping    (method = GET)
    ├── @PostMapping   (method = POST)
    ├── @PutMapping    (method = PUT)
    ├── @DeleteMapping (method = DELETE)
    └── @PatchMapping  (method = PATCH)
```

### 1.2 HTTP 方法语义

| 方法 | 语义 | 幂等 | 安全 |
|------|------|------|------|
| GET | 查询资源 | ✅ | ✅ |
| POST | 创建资源 | ❌ | ❌ |
| PUT | 全量更新 | ✅ | ❌ |
| PATCH | 部分更新 | ❌ | ❌ |
| DELETE | 删除资源 | ✅ | ❌ |

- **幂等**：多次执行结果相同（如 `GET /user/1` 永远返回用户 1）
- **安全**：不修改服务端状态

### 1.3 路径匹配模式

| 模式 | 匹配 | 例子 |
|------|------|------|
| `/user` | 精确路径 | `/user` |
| `/user/*` | 单层通配 | `/user/123` ✅，`/user/123/orders` ❌ |
| `/user/**` | 多层通配 | `/user`、`/user/123`、`/user/123/orders` ✅ |
| `/user/{id}` | 路径变量 | `/user/123` |
| `/user/{id:\\d+}` | 正则约束 | `/user/123` ✅，`/user/abc` ❌ |

## 2. 代码示例

### 2.1 基础映射

```java
// 文件：OrderController.java
@RestController
@RequestMapping("/admin-api/order")
public class OrderController {

    @GetMapping("/list")
    public CommonResult<List<OrderVO>> list() { ... }

    @GetMapping("/{id}")
    public CommonResult<OrderVO> get(@PathVariable Long id) { ... }

    @PostMapping("/create")
    public CommonResult<Long> create(@RequestBody OrderCreateReqVO req) { ... }

    @PutMapping("/update")
    public CommonResult<Boolean> update(@RequestBody OrderUpdateReqVO req) { ... }

    @DeleteMapping("/{id}")
    public CommonResult<Boolean> delete(@PathVariable Long id) { ... }
}
```

### 2.2 条件映射（headers / params / produces）

```java
@GetMapping(value = "/get", params = "type=vip")
public CommonResult<UserVO> getVipUser(@RequestParam Long id) { ... }

@PostMapping(value = "/create",
             consumes = MediaType.APPLICATION_JSON_VALUE,
             produces = MediaType.APPLICATION_JSON_VALUE)
public CommonResult<Long> create(@RequestBody UserCreateReqVO req) { ... }
```

### 2.3 路径变量 + 正则

```java
@GetMapping("/user/{id:\\d+}")
public CommonResult<UserVO> getUser(@PathVariable Long id) { ... }

@GetMapping("/files/{name:.+}")
public void download(@PathVariable String name, HttpServletResponse response) { ... }
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 DefaultController 的通配符映射

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/controller/DefaultController.java`
**核心代码**（行 24-50）：

```java
@RequestMapping("/admin-api/bpm/**")
public CommonResult<Boolean> bpm404() {
    return CommonResult.error(NOT_IMPLEMENTED.getCode(),
            "[工作流模块 yudao-module-bpm - 已禁用][参考 https://doc.iocoder.cn/bpm/ 开启]");
}

@RequestMapping("/admin-api/mp/**")
public CommonResult<Boolean> mp404() {
    return CommonResult.error(NOT_IMPLEMENTED.getCode(),
            "[微信公众号 yudao-module-mp - 已禁用][参考 https://doc.iocoder.cn/mp/build/ 开启]");
}

@RequestMapping(value = { "/admin-api/product/**", // 商品中心
        "/admin-api/trade/**", // 交易中心
        "/admin-api/promotion/**" }) // 营销中心
public CommonResult<Boolean> mall404() {
```

**解读**：
- 第 1 行：`/admin-api/bpm/**` 匹配 `/admin-api/bpm/...` 所有路径
- 第 11-13 行：`@RequestMapping(value = {...})` 支持多路径映射（多个 URL 共享一个方法）
- **设计意图**：当模块未启用时（如 `yudao-module-bpm`），所有该模块的请求都返回"已禁用"提示
- **Ant 风格通配符 `**`**：匹配任意层级的路径，包括 `/admin-api/bpm/process/detail/123`

### 3.2 测试接口的路径映射

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/controller/DefaultController.java`
**核心代码**（行 100-112）：

```java
/**
 * 测试接口：打印 query、header、body
 */
@RequestMapping(value = { "/test" })
@PermitAll
public CommonResult<Boolean> test(HttpServletRequest request) {
    // 打印查询参数
    log.info("Query: {}", ServletUtils.getParamMap(request));
    // 打印请求头
    log.info("Header: {}", ServletUtils.getHeaderMap(request));
    // 打印请求体
    log.info("Body: {}", ServletUtils.getBody(request));
    return CommonResult.success(true);
}
```

**解读**：
- 第 4 行：`@RequestMapping(value = { "/test" })` 不指定 method，默认支持所有 HTTP 方法（GET、POST、PUT 等）
- 第 5 行：`@PermitAll` 允许匿名访问（绕过 Spring Security）
- **用法**：开发环境调试用，访问 `http://localhost:8080/admin-api/test` 即可
- **注意**：生产环境应删除此接口

### 3.3 启动类的扫描配置 + WebProperties

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 45-67）：

```java
@Bean
public WebMvcRegistrations webMvcRegistrations(WebProperties webProperties) {
    return new WebMvcRegistrations() {

        @Override
        public RequestMappingHandlerMapping getRequestMappingHandlerMapping() {
            RequestMappingHandlerMapping mapping = new RequestMappingHandlerMapping();
            // 实例化时就带上前缀
            mapping.setPathPrefixes(buildPathPrefixes(webProperties));
            return mapping;
        }

        /**
         * 构建 prefix → 匹配条件的映射
         */
        private Map<String, Predicate<Class<?>>> buildPathPrefixes(WebProperties webProperties) {
            AntPathMatcher antPathMatcher = new AntPathMatcher(".");
            Map<String, Predicate<Class<?>>> pathPrefixes = Maps.newLinkedHashMapWithExpectedSize(2);
            putPathPrefix(pathPrefixes, webProperties.getAdminApi(), antPathMatcher);
            putPathPrefix(pathPrefixes, webProperties.getAppApi(), antPathMatcher);
            return pathPrefixes;
        }
```

**解读**：
- 第 6-10 行：自定义 `RequestMappingHandlerMapping` 给所有 Controller 加路径前缀
- 第 18-19 行：分别给 `adminApi`（`/admin-api`）和 `appApi`（`/app-api`）配置前缀
- **设计意图**：通过 `setPathPrefixes` 让 `cn.iocoder.yudao.module.system.controller.admin.*` 的 Controller 路径自动加 `/admin-api` 前缀
- **对比**：`@RequestMapping("/admin-api/system/user")` 需要在每个 Controller 写前缀，ruoyi 用全局配置更优雅

## 4. 关键要点总结

- **专用注解优先**：`@GetMapping` > `@RequestMapping(method=GET)`
- **HTTP 方法语义**：GET 幂等、POST 非幂等、DELETE 幂等
- **路径变量**：`@PathVariable`，正则约束 `\\d+`
- **Ant 通配符**：`*` 单层、`**` 多层
- **ruoyi 路径前缀**：`/admin-api`（后台）、`/app-api`（前台），通过 `WebProperties` 配置
- **ruoyi 用 `WebMvcRegistrations` 统一设置前缀**，避免在每个 Controller 重复写

## 5. 练习题

### 练习 1：基础（必做）

编写一个 `ProductController`，提供 `/admin-api/product/{id:\\d+}`（GET）、`/admin-api/product`（POST）接口。

### 练习 2：进阶

阅读 `YudaoWebAutoConfiguration` 的 `webMvcRegistrations` 方法，解释 `AntPathMatcher(".")` 中 `"."` 的作用。

### 练习 3：挑战（选做）

实现一个 `ApiVersionController`，根据请求头 `X-Api-Version: v2` 路由到不同方法（如 `/api/get` → `getV1()` 或 `getV2()`），用 `@RequestMapping(headers=...)` 实现。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/controller/DefaultController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
- Spring MVC 请求映射：https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-requestmapping.html
- 芋道 Spring MVC：https://doc.iocoder.cn/spring-boot-springmvc/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
