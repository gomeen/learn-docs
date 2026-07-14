# 8 CSRF 与 CORS 配置

> 理解 CSRF（跨站请求伪造）和 CORS（跨域资源共享）的区别，以及 ruoyi 的实践。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 CSRF 攻击的原理和防御方法
- 理解 CORS 的 preflight 机制
- 知道 ruoyi 为什么要禁用 CSRF、但开启 CORS
- 能根据业务场景正确配置 Spring Security

## 📚 前置知识

- HTTP 协议基础
- 浏览器同源策略
- Spring MVC @CrossOrigin

## 1. 核心概念

### 1.1 CSRF（Cross-Site Request Forgery，跨站请求伪造）

**攻击场景**：
1. 用户登录了 `bank.com`，浏览器保存了 Cookie
2. 用户访问了恶意网站 `evil.com`
3. `evil.com` 发送请求到 `bank.com/transfer?to=hacker&amount=10000`
4. 浏览器自动带上 `bank.com` 的 Cookie
5. **银行认为是用户本人操作**

**防御**：
- **Token 机制**：每次请求带随机 Token（Spring Security 默认方案）
- **SameSite Cookie**：禁止跨站发送 Cookie（现代浏览器默认）
- **Referer/Origin 校验**：检查请求来源

### 1.2 CORS（Cross-Origin Resource Sharing，跨域资源共享）

**同源策略**：
- 浏览器限制：协议、域名、端口 任意一个不同就是跨域
- 跨域 AJAX 默认会被拦截

**CORS 解决**：
- 服务器在响应 Header 中加 `Access-Control-Allow-Origin: https://frontend.com`
- 浏览器检查这个 Header，决定是否放行

**Preflight 预检**：
- 浏览器对"非简单请求"（如 `application/json` 的 POST）先发 OPTIONS 请求
- 服务器返回 `Access-Control-Allow-Methods` / `Access-Control-Allow-Headers`
- 浏览器再发真正的请求

### 1.3 ruoyi 的取舍

| 攻击类型 | ruoyi 选择 | 原因 |
|---------|-----------|------|
| CSRF | **禁用** | 用 Token（不是 Cookie）鉴权，不存在 CSRF |
| CORS | **开启** | 前后端分离，前端域名 ≠ 后端域名 |

## 2. 代码示例

### 2.1 传统 CSRF 防御（不适用 Token 场景）

```java
// 错误：禁用 CSRF + Cookie 鉴权 = 不安全
http.csrf(csrf -> csrf.disable())
    .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED));  // 仍用 Cookie

// 正确：禁用 CSRF + Token 鉴权（ruoyi 方案）
http.csrf(csrf -> csrf.disable())
    .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS));
```

### 2.2 CORS 配置

```java
// 简单 CORS：允许所有来源（开发环境）
@Bean
public CorsConfigurationSource corsConfigurationSource() {
    CorsConfiguration config = new CorsConfiguration();
    config.addAllowedOriginPattern("*");     // 允许所有来源
    config.addAllowedHeader("*");            // 允许所有 Header
    config.addAllowedMethod("*");            // 允许所有方法
    config.setAllowCredentials(true);        // 允许带 Cookie
    config.setMaxAge(3600L);                 // 预检结果缓存 1 小时

    UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
    source.registerCorsConfiguration("/**", config);
    return source;
}
```

## 3. ruoyi 仓库源码解读

### 3.1 YudaoWebSecurityConfigurerAdapter 中的配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
**核心代码**（行 110-123）：

```java
@Bean
protected SecurityFilterChain filterChain(HttpSecurity httpSecurity) throws Exception {
    httpSecurity
            // ① 开启跨域
            .cors(Customizer.withDefaults())
            // ② CSRF 禁用，因为不使用 Session
            .csrf(AbstractHttpConfigurer::disable)
            // ③ 基于 token 机制，所以不需要 Session
            .sessionManagement(c -> c.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            // ④ 允许 iframe 嵌套（用于文档预览）
            .headers(c -> c.frameOptions(HeadersConfigurer.FrameOptionsConfig::disable))
            .exceptionHandling(c -> c.authenticationEntryPoint(authenticationEntryPoint)
                    .accessDeniedHandler(accessDeniedHandler));
    // ...
}
```

**解读**：
- 第 114 行 `.cors(Customizer.withDefaults())`：使用默认 CORS 配置（由其他 Bean 提供）
- 第 116 行 `.csrf(AbstractHttpConfigurer::disable)`：**禁用 CSRF**，因为 ruoyi 用 Token 鉴权，攻击者拿不到 Token
- 第 118 行 `STATELESS`：**无状态 Session**，不创建 HttpSession
- 第 119 行 `frameOptions.disable()`：允许 iframe 嵌入（用于 PDF 预览、文档管理等场景）

### 3.2 禁用 CSRF 的原因

CSRF 的本质是：**浏览器自动带上 Cookie**。ruoyi 的鉴权完全基于 Token（`Authorization: Bearer xxx`），Token 存在前端代码中（localStorage / cookie 模式），攻击者无法让受害者的浏览器**自动带上** Token。

**对比传统 Cookie 鉴权**：
```
传统 Cookie（易受 CSRF）：
  浏览器每次请求自动带上 Cookie → 攻击者利用
Token 鉴权（不受 CSRF）：
  浏览器不会自动带上 Token → 攻击者拿不到
```

### 3.3 开启 CORS 的原因

ruoyi 是**前后端分离**架构：
- 前端：`https://admin.example.com`（Vue 部署在 Nginx）
- 后端：`https://api.example.com`（Spring Boot）

这两个域名不同，浏览器会拦截跨域请求。后端需要返回 CORS Header：
```
Access-Control-Allow-Origin: https://admin.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type
Access-Control-Allow-Credentials: true
```

## 4. 关键要点总结

- **CSRF**：跨站请求伪造，攻击者利用浏览器自动带 Cookie。**Token 鉴权天然免疫**
- **CORS**：跨域资源共享，前后端分离必备
- ruoyi **禁用 CSRF**（用 Token）、**开启 CORS**（前后端分离）
- `STATELESS` Session：不创建 HttpSession，纯粹靠 Token
- `frameOptions.disable()`：允许 iframe 嵌入（注意 XSS 风险）

## 5. 练习题

### 练习 1：基础（必做）

解释为什么用 Token 鉴权可以天然防御 CSRF 攻击？写一个简单的 CSRF 攻击场景描述。

### 练习 2：进阶

为 ruoyi 配置生产级 CORS：只允许 `https://admin.yourdomain.com` 跨域访问，允许带 `Authorization` Header，过期时间 1 小时。

### 练习 3：挑战（选做）

如果一定要用 Cookie 鉴权，Spring Security 默认会开启 CSRF 防御。请说明 CSRF Token 的工作原理（提示：HTTP 同步令牌模式）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
- MDN CORS：https://developer.mozilla.org/zh-CN/docs/Web/HTTP/CORS
- OWASP CSRF：https://owasp.org/www-community/attacks/csrf
- Spring Security CSRF：https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
