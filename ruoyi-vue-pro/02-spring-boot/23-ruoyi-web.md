# 20 ruoyi 的 Web 配置分析

> 综合分析 ruoyi-vue-pro 的 Web 配置：路径前缀、Filter 链、统一异常处理、统一返回结果。

## 🎯 学习目标

完成本文档后，你将能够：
- 综合理解 ruoyi-vue-pro 的 Web 架构
- 掌握 WebProperties + YudaoWebAutoConfiguration 的设计
- 能快速定位 Web 相关的配置和扩展点
- 理解 `/admin-api` 和 `/app-api` 的双前端架构

## 📚 前置知识

- [13-controller](./15-controller.md) ~ [19-filter](./22-filter.md) 全部文档

## 1. 核心概念

### 1.1 ruoyi Web 架构总览

> 📌 **Sighting**：Filter 链细节见 [19-filter](./22-filter.md)；CORS 原理见 [CORS](../../_common/05-web-security/05-cors.md)；异常处理见 [17-exception-handler](./20-exception-handler.md)。

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

## 3. 关键要点总结

- **ruoyi Web 架构**：Filter 链 + Interceptor + AOP 三层切面
- **双前端架构**：`/admin-api`（后台）、`/app-api`（前台）
- **路径前缀机制**：`YudaoWebAutoConfiguration.webMvcRegistrations` + `WebProperties`
- **统一异常处理**：`GlobalExceptionHandler` 处理 20+ 种异常
- **统一返回**：`CommonResult<T>` + `GlobalResponseBodyHandler`
- **统一配置**：`WebProperties` + `@EnableConfigurationProperties`
- **应用名注入**：`@Value("${spring.application.name}")` 用于日志、监控

---

**文档版本**：v1.0
**最后更新**：2026-07-13
