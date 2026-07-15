# 20 ruoyi 的 Web 配置分析

> 综合分析 ruoyi-vue-pro 的 Web 配置：路径前缀、Filter 链、统一异常处理、统一返回结果。

## 🎯 学习目标

完成本文档后，你将能够：
- 综合理解 ruoyi-vue-pro 的 Web 架构
- 掌握 WebProperties + YudaoWebAutoConfiguration 的设计
- 能快速定位 Web 相关的配置和扩展点
- 理解 `/admin-api` 和 `/app-api` 的双前端架构

## 📚 前置知识

- [13-controller](./13-controller.md) ~ [19-filter](./19-filter.md) 全部文档

## 1. 核心概念

### 1.1 ruoyi Web 架构总览

> 📌 **Sighting**：Filter 链细节见 [19-filter](./19-filter.md)；CORS 原理见 [CORS](../../_common/05-web-security/05-cors.md)；异常处理见 [17-exception-handler](./17-exception-handler.md)。

```
HTTP 请求
  ↓
[1] CORS Filter（跨域）
  ↓
[2] RequestBodyCache Filter（请求体缓存）
  ↓
[3] Demo Filter（演示模式）
  ↓
[4] ApiAccessLog Filter（API 日志）
  ↓
[5] ApiEncrypt Filter（API 加密）
  ↓
DispatcherServlet
  ↓
Interceptor（权限校验等）
  ↓
RequestMappingHandlerMapping（路径前缀：/admin-api /app-api）
  ↓
@Valid 参数校验
  ↓
Controller 方法
  ↓
Service → DAO
  ↓
GlobalExceptionHandler 统一异常处理
  ↓
GlobalResponseBodyHandler 统一返回包装
  ↓
HTTP 响应
```

### 1.2 双前端架构

- **`/admin-api/**`**：后台管理 API（admin 包下的 Controller）
  - 用户：运营人员、平台管理员
  - 鉴权：基于 RBAC（角色权限）
- **`/app-api/**`**：前台用户 API（app 包下的 Controller）
  - 用户：C 端用户（商城、CRM 客户）
  - 鉴权：基于 Token（OAuth2 / JWT）

## 2. ruoyi-vue-pro 仓库源码解读

### 2.1 YudaoWebAutoConfiguration 完整解读

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 35-100）：

```java
@AutoConfiguration
@EnableConfigurationProperties(WebProperties.class)
public class YudaoWebAutoConfiguration {

    /**
     * 应用名
     */
    @Value("${spring.application.name}")
    private String applicationName;

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

            /**
             * 设置 API 前缀，仅仅匹配 controller 包下的
             */
            private void putPathPrefix(Map<String, Predicate<Class<?>>> pathPrefixes, WebProperties.Api api, AntPathMatcher matcher) {
                if (api == null || StrUtil.isEmpty(api.getPrefix())) {
                    return;
                }
                pathPrefixes.put(api.getPrefix(), // api 前缀
                        clazz -> clazz.isAnnotationPresent(RestController.class)
                                && matcher.match(api.getController(), clazz.getPackage().getName()));
            }

        };
    }

    @Bean
    @SuppressWarnings("SpringJavaInjectionPointsAutowiringInspection")
    public GlobalExceptionHandler globalExceptionHandler(ApiErrorLogCommonApi apiErrorLogApi) {
        return new GlobalExceptionHandler(applicationName, apiErrorLogApi);
    }

    @Bean
    public GlobalResponseBodyHandler globalResponseBodyHandler() {
        return new GlobalResponseBodyHandler();
    }
```

**解读**：
- 第 1 行：`@AutoConfiguration` Spring Boot 3.x 自动配置
- 第 2 行：`@EnableConfigurationProperties(WebProperties.class)` 启用配置类
- 第 7 行：`@Value("${spring.application.name}")` 注入应用名
- 第 10-42 行：`webMvcRegistrations` 自定义 `RequestMappingHandlerMapping`：
  - 第 11-16 行：用 `setPathPrefixes` 给所有匹配的 Controller 加路径前缀
  - 第 22-28 行：分别为 `adminApi` 和 `appApi` 构建前缀映射
  - 第 35-42 行：`putPathPrefix` 把包名（`**.controller.admin.**`）和前缀（`/admin-api`）绑定
- 第 45-48 行：注册 `GlobalExceptionHandler`，注入 `applicationName` 和 `ApiErrorLogCommonApi`
- 第 50-52 行：注册 `GlobalResponseBodyHandler`（统一返回包装器）

### 2.2 WebProperties 配置详解

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/WebProperties.java`
**核心代码**（行 18-30）：

```java
@NotNull(message = "APP API 不能为空")
private Api appApi = new Api("/app-api", "**.controller.app.**");
@NotNull(message = "Admin API 不能为空")
private Api adminApi = new Api("/admin-api", "**.controller.admin.**");

@NotNull(message = "Admin UI 不能为空")
private Ui adminUi;

@Data
@AllArgsConstructor
@NoArgsConstructor
@Valid
public static class Api {

    /**
     * API 前缀
     */
    @NotEmpty(message = "API 前缀不能为空")
    private String prefix;

    /**
     * Controller 所在包的 Ant 路径规则
     */
    @NotEmpty(message = "Controller 所在包不能为空")
    private String controller;

}
```

**解读**：
- 第 1-2 行：`appApi` 默认前缀 `/app-api`，匹配 `**.controller.app.**` 包下的 Controller
- 第 3-4 行：`adminApi` 默认前缀 `/admin-api`，匹配 `**.controller.admin.**` 包下的 Controller
- **第 2 行 `**` 含义**：所有以 `.controller.app.` 结尾的包
- 第 18 行：`@AllArgsConstructor` 生成 `(prefix, controller)` 双参构造器
- **用户配置覆盖**：

```yaml
yudao:
  web:
    admin-api:
      prefix: /admin-api
      controller: "**.controller.admin.**"
    app-api:
      prefix: /app-api
      controller: "**.controller.app.**"
```

### 2.3 GlobalExceptionHandler 注册

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（行 54-68）：

```java
@RestControllerAdvice
@AllArgsConstructor
@Slf4j
public class GlobalExceptionHandler {

    /**
     * 忽略的 ServiceException 错误提示，避免打印过多 logger
     */
    public static final Set<String> IGNORE_ERROR_MESSAGES = SetUtils.asSet("无效的刷新令牌");

    @SuppressWarnings("SpringJavaInjectionPointsAutowiringInspection")
    private final String applicationName;

    private final ApiErrorLogCommonApi apiErrorLogApi;
```

**解读**：
- 第 1 行：`@RestControllerAdvice` 全局异常处理
- 第 2 行：`@AllArgsConstructor` 注入 `applicationName` 和 `apiErrorLogApi`
- 第 8 行：常量定义要忽略的错误消息
- 第 12 行：`apiErrorLogApi` 用于异步记录异常日志（RPC + MQ）

### 2.4 YudaoServerApplication 启动类

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/YudaoServerApplication.java`
**核心代码**（行 16-24）：

```java
@SuppressWarnings("SpringComponentScan") // 忽略 IDEA 无法识别 ${yudao.info.base-package}
@SpringBootApplication(scanBasePackages = {"${yudao.info.base-package}.server", "${yudao.info.base-package}.module"})
public class YudaoServerApplication {

    public static void main(String[] args) {
        // 如果你碰到启动的问题，请认真阅读 https://doc.iocoder.cn/quick-start/ 文章
        SpringApplication.run(YudaoServerApplication.class, args);
    }
}
```

**解读**：
- 第 2 行：`scanBasePackages` 同时扫描 `cn.iocoder.yudao.server`（启动模块）和 `cn.iocoder.yudao.module`（所有业务模块）
- **作用**：通过占位符 `${yudao.info.base-package}` 支持多租户（不同租户不同包名）

## 3. 关键要点总结

- **ruoyi Web 架构**：Filter 链 + Interceptor + AOP 三层切面
- **双前端架构**：`/admin-api`（后台）、`/app-api`（前台）
- **路径前缀机制**：`YudaoWebAutoConfiguration.webMvcRegistrations` + `WebProperties`
- **统一异常处理**：`GlobalExceptionHandler` 处理 20+ 种异常
- **统一返回**：`CommonResult<T>` + `GlobalResponseBodyHandler`
- **统一配置**：`WebProperties` + `@EnableConfigurationProperties`
- **应用名注入**：`@Value("${spring.application.name}")` 用于日志、监控

## 4. 练习题

### 练习 1：基础（必做）

阅读 `YudaoWebAutoConfiguration` 完整代码，列出该类中所有 `@Bean` 方法及其作用。

### 练习 2：进阶

画出 ruoyi-vue-pro 的 HTTP 请求处理完整时序图（从 Filter 到 Controller 到 Response）。

### 练习 3：挑战（选做）

实现一个自定义的 `WebFilterOrderEnum`（参考 ruoyi 的实现），定义 5 个 Filter 的顺序常量（CORS、RequestBodyCache、ApiAccessLog、ApiEncrypt、RateLimit），并说明每个 Filter 应该在什么位置。

## 5. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/WebProperties.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/YudaoServerApplication.java`
- ruoyi Web 架构：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
