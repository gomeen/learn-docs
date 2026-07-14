# 20 接口权限：API 级别控制

> 详解 ruoyi 是如何做 API 级别权限控制的：URL 规则 + 注解 + 拦截器。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握三种 API 权限控制方式：URL 规则 / `@PreAuthorize` / 自定义拦截器
- 理解 ruoyi 的"白名单 + 黑名单 + 默认拒绝"模型
- 知道如何为 API 添加细粒度权限
- 能区分"功能权限"和"数据权限"的层级

## 📚 前置知识

- 03-security-config.md
- 06-preauthorize.md
- 19-button-permission.md

## 1. 核心概念

### 1.1 三层 API 权限防护

```
第 1 层：URL 规则（粗粒度）
  SecurityFilterChain.authorizeHttpRequests
  适用：整个 Controller 级别的访问控制

第 2 层：方法注解（中粒度）
  @PreAuthorize
  适用：单个方法的权限控制

第 3 层：业务层判断（细粒度）
  Service.hasPermission()
  适用：数据范围、记录归属、临时授权等
```

### 1.2 ruoyi 的"白名单 + 默认拒绝"

```
白名单（permitAll）：
  ├─ 静态资源（*.html, *.css, *.js）
  ├─ @PermitAll 注解的 URL
  └─ yudao.security.permit-all-urls 配置

默认规则（authenticated）：
  所有未匹配白名单的 URL 必须登录

特殊规则（@PreAuthorize）：
  已登录用户必须有对应权限
```

## 2. 代码示例

### 2.1 三种 API 控制方式

```java
// 文件：OrderController.java
@RestController
@RequestMapping("/admin-api/order")
public class OrderController {

    // 方式 1：URL 规则（在 AuthorizeRequestsCustomizer 中配置）
    // 只有 SUPER_ADMIN 才能访问 /order/**
    // requestMatchers("/order/**").hasRole("SUPER_ADMIN")

    // 方式 2：方法注解
    @GetMapping("/list")
    @PreAuthorize("@ss.hasPermission('order:order:query')")
    public CommonResult<List<OrderVO>> list() { ... }

    // 方式 3：业务层判断
    @PostMapping("/delete")
    @PreAuthorize("@ss.hasPermission('order:order:delete')")
    public CommonResult<Boolean> delete(@RequestParam Long id) {
        OrderDO order = orderService.getOrder(id);
        // 业务层校验：只能删除自己部门的订单
        if (!order.getDeptId().equals(SecurityFrameworkUtils.getLoginUserDeptId())) {
            throw new ServiceException("无权操作其他部门的订单");
        }
        orderService.delete(id);
        return success(true);
    }
}
```

### 2.2 自定义拦截器

```java
// 文件：RateLimitInterceptor.java
@Component
public class RateLimitInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String uri = request.getRequestURI();
        // 只对特定 API 限流
        if (uri.startsWith("/admin-api/sms/send")) {
            String key = "rate_limit:" + ServletUtils.getClientIP();
            Long count = redis.opsForValue().increment(key);
            if (count > 10) {  // 每分钟最多 10 次
                throw new ServiceException("请求过于频繁");
            }
            redis.expire(key, 60);
        }
        return true;
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 AuthorizeRequestsCustomizer 的实际使用

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/AuthorizeRequestsCustomizer.java`
**核心代码**（行 17-36）：

```java
public abstract class AuthorizeRequestsCustomizer
        implements Customizer<AuthorizeHttpRequestsConfigurer<HttpSecurity>.AuthorizationManagerRequestMatcherRegistry>, Ordered {

    @Resource
    private WebProperties webProperties;

    protected String buildAdminApi(String url) {
        return webProperties.getAdminApi().getPrefix() + url;
    }

    protected String buildAppApi(String url) {
        return webProperties.getAppApi().getPrefix() + url;
    }

    @Override
    public int getOrder() {
        return 0;
    }
}
```

**解读**：
- 第 17-18 行：抽象类，每个 Module 可继承来自定义 URL 规则
- 第 23-29 行：提供 `buildAdminApi` / `buildAppApi` 工具方法
- 实际 Module 继承示例（伪代码）：

```java
@Component
public class InfraAuthorizeRequestsCustomizer extends AuthorizeRequestsCustomizer {
    @Override
    public void customize(AuthorizationManagerRequestMatcherRegistry registry) {
        // URL 规则（粗粒度）
        registry.requestMatchers(buildAdminApi("/infra/captcha/**")).permitAll();
        registry.requestMatchers(buildAdminApi("/infra/file/**")).hasRole("ADMIN");
    }
}
```

### 3.2 getPermitAllUrlsFromAnnotations

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
**核心代码**（行 159-219）：

```java
private Multimap<HttpMethod, String> getPermitAllUrlsFromAnnotations() {
    Multimap<HttpMethod, String> result = HashMultimap.create();
    RequestMappingHandlerMapping requestMappingHandlerMapping = (RequestMappingHandlerMapping)
            applicationContext.getBean("requestMappingHandlerMapping");
    Map<RequestMappingInfo, HandlerMethod> handlerMethodMap = requestMappingHandlerMapping.getHandlerMethods();

    for (Map.Entry<RequestMappingInfo, HandlerMethod> entry : handlerMethodMap.entrySet()) {
        HandlerMethod handlerMethod = entry.getValue();
        // 关键：检查 @PermitAll 注解
        if (!handlerMethod.hasMethodAnnotation(PermitAll.class)
            && !handlerMethod.getBeanType().isAnnotationPresent(PermitAll.class)) {
            continue;
        }
        Set<String> urls = new HashSet<>();
        if (entry.getKey().getPatternsCondition() != null) {
            urls.addAll(entry.getKey().getPatternsCondition().getPatterns());
        }
        if (entry.getKey().getPathPatternsCondition() != null) {
            urls.addAll(convertList(entry.getKey().getPathPatternsCondition().getPatterns(), PathPattern::getPatternString));
        }
        if (urls.isEmpty()) continue;
        // 按 HTTP Method 归类
        Set<RequestMethod> methods = entry.getKey().getMethodsCondition().getMethods();
        if (CollUtil.isEmpty(methods)) {
            result.putAll(HttpMethod.GET, urls);
            result.putAll(HttpMethod.POST, urls);
            // ... 其他方法
            continue;
        }
        methods.forEach(requestMethod -> {
            switch (requestMethod) {
                case GET: result.putAll(HttpMethod.GET, urls); break;
                case POST: result.putAll(HttpMethod.POST, urls); break;
                // ...
            }
        });
    }
    return result;
}
```

**解读**：
- 第 162-164 行：通过 `RequestMappingHandlerMapping` 拿到所有 Controller 方法的映射
- 第 167-170 行：检查方法或类上是否有 `@PermitAll` 注解
- 第 184-192 行：没指定 HTTP Method 时，所有 Method 都免登录
- **关键作用**：开发者只需要在方法上加 `@PermitAll`，白名单自动注册

### 3.3 三层防护的完整示例

以"删除订单"接口为例：

```java
// 第 1 层：URL 规则（AuthorizeRequestsCustomizer）
registry.requestMatchers("/admin-api/order/delete").authenticated();  // 必须登录

// 第 2 层：方法注解
@PreAuthorize("@ss.hasPermission('order:order:delete')")
@DeleteMapping("/delete")
public CommonResult<Boolean> delete(@RequestParam Long id) {
    // 第 3 层：业务校验
    OrderDO order = orderService.getOrder(id);
    if (!order.getDeptId().equals(SecurityFrameworkUtils.getLoginUserDeptId())) {
        throw new ServiceException("无权操作");
    }
    orderService.delete(id);
    return success(true);
}
```

## 4. 关键要点总结

- API 权限三层防护：URL 规则 / `@PreAuthorize` / 业务层判断
- ruoyi 默认采用"白名单 + 默认拒绝"模型
- `@PermitAll` 注解自动扫描注册到白名单
- 业务层判断用于"数据归属"、"临时授权"等复杂场景
- `AuthorizeRequestsCustomizer` 让每个 Module 自由扩展 URL 规则

## 5. 练习题

### 练习 1：基础（必做）

写一个 `@PreAuthorize` 注解，要求"只有订单所属部门的用户才能删除"。

### 练习 2：进阶

实现一个 `RateLimitInterceptor`，对 `/admin-api/sms/send` 接口做每分钟 10 次的限流。

### 练习 3：挑战（选做）

设计"API 版本管理"功能：`/api/v1/**` 和 `/api/v2/**` 是两套不同的接口，需要不同权限。说明 URL 规则和注解的写法。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/AuthorizeRequestsCustomizer.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
- Spring HandlerInterceptor：https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-handlers.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
