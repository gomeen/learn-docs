# 3.4 Spring Cloud Gateway（yudao-cloud）

> 理解 Spring Cloud Gateway 在微服务中的角色，掌握 yudao-cloud 的路由与负载均衡配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Cloud Gateway 的作用与定位
- 掌握 Route / Predicate / Filter 三大核心概念
- 能在 yudao-cloud 中配置动态路由
- 知道 Gateway 与 Nginx 的区别

## 📚 前置知识

- 微服务基础概念
- Spring Cloud Netflix / Alibaba
- Nginx 基础与反向代理（详见 [Nginx 基础](../../_common/10-network-proxy/01-nginx-basics.md)、[反向代理](../../_common/10-network-proxy/02-reverse-proxy.md)）
- 响应式基础（详见 [Reactive](../01-java-fundamentals/40-reactive.md)）
- 限流（Filter 内常见，详见 [限流算法](../../_common/03-cache-patterns/04-rate-limiting.md)）

## 1. 核心概念

### 1.1 Spring Cloud Gateway 是什么？

Spring Cloud Gateway 是 **Spring Cloud 官方网关**，基于 **WebFlux（响应式）** + **Netty** 实现。

**核心定位**：
- 统一入口（所有请求先到 Gateway）
- 路由转发（按规则转发到后端微服务）
- 鉴权 / 限流 / 监控（Filter 链；鉴权详见 [Spring Security](../03-spring-boot-starters/24-spring-security.md)）

### 1.2 三大核心概念

| 概念 | 作用 | 示例 |
|------|------|------|
| **Route** | 路由（id + uri + predicates + filters） | 路由到 `yudao-system` 服务 |
| **Predicate** | 断言（匹配条件） | `Path=/admin-api/system/**` |
| **Filter** | 过滤器（修改请求/响应） | 加 Header / 限流 / 重试 |

**匹配流程**：

```
请求 → 路由匹配（Predicate） → 过滤器链（前/后） → 目标服务
```

### 1.3 Gateway vs Nginx

| 维度 | Nginx | Spring Cloud Gateway |
|------|-------|---------------------|
| 语言 | C | Java |
| 性能 | 极高 | 较高（Netty 异步） |
| 动态配置 | 需 reload | 配合 Nacos 热更新 |
| Java 生态 | 不友好 | 原生集成 |
| 适用 | 边缘入口 | 内部微服务网关 |

**典型组合**：Nginx（外层 HTTPS 终止）→ Spring Cloud Gateway（内部路由）→ 微服务

## 2. 代码示例

### 2.1 基础路由配置

```yaml
# 文件：gateway-service/src/main/resources/application.yaml
spring:
  cloud:
    gateway:
      routes:
        - id: yudao-system
          uri: lb://yudao-system  # lb: LoadBalancer
          predicates:
            - Path=/admin-api/system/**
          filters:
            - StripPrefix=0  # 不去掉前缀

        - id: yudao-infra
          uri: lb://yudao-infra
          predicates:
            - Path=/admin-api/infra/**
          filters:
            - StripPrefix=0
```

**说明**：
- `lb://yudao-system` — 从注册中心（Nacos）拉取 `yudao-system` 服务列表，自动负载均衡
- `Path=/admin-api/system/**` — 路径匹配
- `StripPrefix=0` — 不剥离前缀

### 2.2 内置 Filter：添加请求头

```yaml
filters:
  - AddRequestHeader=X-Request-Source, gateway
  - AddResponseHeader=X-Response-Source, gateway
```

### 2.3 全局 CORS 配置

```yaml
spring:
  cloud:
    gateway:
      globalcors:
        cors-configurations:
          '[/**]':
            allowedOriginPatterns: "*"
            allowedMethods: "*"
            allowedHeaders: "*"
            allowCredentials: true
```

## 3. 关键要点总结

- Spring Cloud Gateway = Route + Predicate + Filter
- `lb://service-name` 是关键：从注册中心拉取实例 + 负载均衡
- 配合 Nacos 可实现**动态路由**（修改配置无需重启）
- Gateway 通常配合 Nginx 使用：Nginx 做 HTTPS 终止，Gateway 做内部路由
- yudao 单体版没有 Gateway；yudao-cloud 版本才有
- 限流、熔断等高级功能通过 Filter 实现

---

**文档版本**：v1.0
**最后更新**：2026-07-13
