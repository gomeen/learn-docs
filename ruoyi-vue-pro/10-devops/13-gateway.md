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
- `12-load-balance.md`

## 1. 核心概念

### 1.1 Spring Cloud Gateway 是什么？

Spring Cloud Gateway 是 **Spring Cloud 官方网关**，基于 **WebFlux（响应式）** + **Netty** 实现。

**核心定位**：
- 统一入口（所有请求先到 Gateway）
- 路由转发（按规则转发到后端微服务）
- 鉴权 / 限流 / 监控（Filter 链）

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

## 3. ruoyi 仓库源码解读

**注**：当前 ruoyi 仓库主要是**单体版**（yudao-server 单 jar），**yudao-cloud 是另一个仓库**。

### 3.1 yudao-server 的网关定位

ruoyi 单体版**没有 Spring Cloud Gateway**，`yudao-server` 直接对外提供 API（通过 Nginx 反代）。

### 3.2 yudao-cloud 架构（基于官方文档）

```
用户 → Nginx (HTTPS) → Spring Cloud Gateway
                              ↓
                ┌─────────────┼─────────────┐
                ↓             ↓             ↓
        yudao-system    yudao-infra   yudao-member ...
                ↓             ↓             ↓
              MySQL         Redis         Nacos
```

**典型 yudao-cloud gateway 配置**（基于芋道文档）：

```yaml
spring:
  application:
    name: yudao-gateway
  cloud:
    nacos:
      discovery:
        server-addr: 127.0.0.1:8848

    gateway:
      discovery:
        locator:
          enabled: true  # 自动从 Nacos 发现服务
      routes:
        # 动态路由：访问 /admin-api/system/** → yudao-system 服务
        - id: yudao-system
          uri: lb://yudao-system
          predicates:
            - Path=/admin-api/system/**
        - id: yudao-infra
          uri: lb://yudao-infra
          predicates:
            - Path=/admin-api/infra/**
```

**配套 application 配置**（节选）：

```yaml
server:
  port: 48090  # Gateway 端口

# Spring Cloud Gateway + Nacos 动态路由
nacos:
  data-id: gateway-router  # Nacos 配置 ID
  group: DEFAULT_GROUP
  auto-refresh: true
```

### 3.3 Nacos 动态路由配置

在 Nacos 控制台创建配置 `gateway-router.yaml`：

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: yudao-system
          uri: lb://yudao-system
          predicates:
            - Path=/admin-api/system/**
        - id: yudao-infra
          uri: lb://yudao-infra
          predicates:
            - Path=/admin-api/infra/**
```

**优势**：修改 Nacos 配置即可动态调整路由，**无需重启 Gateway**。

## 4. 关键要点总结

- Spring Cloud Gateway = Route + Predicate + Filter
- `lb://service-name` 是关键：从注册中心拉取实例 + 负载均衡
- 配合 Nacos 可实现**动态路由**（修改配置无需重启）
- Gateway 通常配合 Nginx 使用：Nginx 做 HTTPS 终止，Gateway 做内部路由
- yudao 单体版没有 Gateway；yudao-cloud 版本才有
- 限流、熔断等高级功能通过 Filter 实现

## 5. 练习题

### 练习 1：基础（必做）

创建独立的 `gateway-demo` Spring Boot 项目，加入 `spring-cloud-starter-gateway` 依赖，配置一个静态路由：`/test/**` → `http://httpbin.org/**`。

### 练习 2：进阶

为 gateway-demo 添加 Nacos 注册中心，启动 2 个 yudao-server 注册到 Nacos，配置 `lb://yudao-server` 路由，观察 2 个实例轮流响应。

### 练习 3：挑战（选做）

为 gateway-demo 添加**全局限流 Filter**（基于 Redis 令牌桶），限制每个 IP 每秒最多 10 个请求，用 `wrk` 压测验证。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/pom.xml`
- [Spring Cloud Gateway 官方文档](https://docs.spring.io/spring-cloud-gateway/docs/current/reference/html/)
- [Spring Cloud Alibaba 官方文档](https://github.com/alibaba/spring-cloud-alibaba/blob/master/README.md)
- ruoyi-cloud 文档：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
