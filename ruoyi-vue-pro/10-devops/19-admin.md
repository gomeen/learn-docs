# 5.2 Spring Boot Admin

> 理解 Spring Boot Admin 的工作原理，掌握 ruoyi 的可视化监控配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Boot Admin Server / Client 架构
- 掌握 ruoyi 的 Spring Boot Admin 配置
- 能查看应用运行指标、线程、内存等
- 知道如何与 Spring Boot Actuator 配合

## 📚 前置知识

- `18-actuator.md`
- Spring Boot 基础

## 1. 核心概念

### 1.1 什么是 Spring Boot Admin？

Spring Boot Admin（SBA）是 **Actuator 的可视化界面**：
- 把所有应用的 Actuator 端点数据**集中展示**在一个 Web UI
- 类似"微服务的 Grafana"
- 实时展示健康状态、JVM 内存、线程、HTTP 请求、Trace 等

### 1.2 架构

```
Spring Boot Admin Server (Web UI)
   ↑
   | 注册到（HTTP）
   |
[Client App 1: yudao-server]   [Client App 2: other-app]   ...
   (暴露 /actuator/**)
```

| 角色 | 作用 |
|------|------|
| **Admin Server** | 收集并展示所有客户端的指标 |
| **Admin Client** | 注册到 Server，暴露 Actuator |

### 1.3 核心功能

- 应用列表（多应用监控）
- 健康状态、JVM 内存、线程栈
- HTTP 请求跟踪、Metrics
- 日志级别动态调整
- 环境变量查看（**生产慎用**）

## 2. 代码示例

### 2.1 Admin Server 端

```xml
<dependency>
    <groupId>de.codecentric</groupId>
    <artifactId>spring-boot-admin-starter-server</artifactId>
    <version>2.7.10</version>
</dependency>
```

```java
@SpringBootApplication
@EnableAdminServer  // 关键注解
public class AdminServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(AdminServerApplication.class, args);
    }
}
```

### 2.2 Admin Client 端

```xml
<dependency>
    <groupId>de.codecentric</groupId>
    <artifactId>spring-boot-admin-starter-client</artifactId>
    <version>2.7.10</version>
</dependency>
```

```yaml
spring:
  boot:
    admin:
      client:
        url: http://localhost:9090  # Admin Server 地址
        username: admin
        password: admin
        instance:
          service-host-type: IP  # 注册时用 IP 而非 hostname

management:
  endpoints:
    web:
      exposure:
        include: '*'
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 Admin 配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
**核心代码**（行 156-170）：

```yaml
# Spring Boot Admin 配置项
spring:
  boot:
    admin:
      # Spring Boot Admin Client 客户端的相关配置
      client:
        url: http://127.0.0.1:${server.port}/${spring.boot.admin.context-path} # 设置 Spring Boot Admin Server 地址
        instance:
          service-host-type: IP # 注册实例时，优先使用 IP [IP, HOST_NAME, CANONICAL_HOST_NAME]
        username: admin
        password: admin
      # Spring Boot Admin Server 服务端的相关配置
      context-path: /admin # 配置 Spring
      # 允许嵌入 iframe 的域名（支持通配符），实际部署时，可以改为 "'self' [你的公网域名]"
      frame-ancestors: "'self' localhost localhost:48080 127.0.0.1 127.0.0.1:48080"
```

**解读**：
- 第 5-12 行：Admin Client 配置
  - 第 6 行：`url` — 指向自己（即 yudao-server 自己就是 Admin Server）
  - 第 8 行：`service-host-type: IP` — 用 IP 而非 hostname（避免 DNS 解析问题）
  - 第 10-11 行：Basic Auth 凭证
- 第 15-16 行：`context-path: /admin` — Admin UI 访问路径
- 第 18 行：`frame-ancestors` — 允许嵌入 iframe 的域名（**生产环境要改为实际域名**）

**关键设计**：
- **ruoyi 把 Admin Server 和 Client 集成在同一个 yudao-server 中**
- 启动后访问 `http://localhost:48080/admin` 即可看到 Admin UI
- 在多实例部署时，可以独立部署一个 Admin Server 收集所有实例

### 3.2 启动器依赖

**注**：Spring Boot Admin 的依赖需要在 `yudao-framework/yudao-spring-boot-starter-monitor/` 中查找或添加。

ruoyi 文档（`yudao-spring-boot-starter-monitor/《芋道 Spring Boot 监控工具 Admin 入门》.md`）说明：
- 需要引入 `spring-boot-admin-starter-server` + `spring-boot-admin-starter-client` 依赖
- 启用 `@EnableAdminServer` 注解

### 3.3 XSS 排除 admin 路径

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yaml`
**核心代码**（行 267-271）：

```yaml
  xss:
    enable: false
    exclude-urls: # 如下两个 url，仅仅是为了演示，去掉配置也没关系
      - ${spring.boot.admin.context-path}/** # 不处理 Spring Boot Admin 的请求
      - ${management.endpoints.web.base-path}/** # 不处理 Actuator 的请求
```

**解读**：
- 第 3-4 行：XSS 过滤器跳过 `/admin/**` 和 `/actuator/**`
- 避免 Admin UI 的 JavaScript 被 XSS 过滤器破坏

## 4. 关键要点总结

- Spring Boot Admin = Actuator + Web UI
- Server 端：引入 `starter-server` + `@EnableAdminServer`
- Client 端：引入 `starter-client` + 配置 `spring.boot.admin.client.url`
- ruoyi 把 Server 和 Client 集成在同一个服务中
- `service-host-type: IP` 用 IP 注册避免 DNS 问题
- `frame-ancestors` 配置生产环境的允许域名
- 访问地址：`http://host:port/admin`（ruoyi 中是 `http://localhost:48080/admin`）

## 5. 练习题

### 练习 1：基础（必做）

启动 yudao-server，访问 `http://localhost:48080/admin`，观察 Admin UI 的应用列表、健康状态、JVM 内存图表。

### 练习 2：进阶

在 Admin UI 的 "Loggers" 标签页，动态调整 `cn.iocoder.yudao.module.system` 的日志级别从 INFO 到 DEBUG，观察日志变化。

### 练习 3：挑战（选做）

部署两个 yudao-server 实例（48080、48081），独立部署一个 Admin Server，把两个实例注册到 Admin Server，观察两个应用的状态对比。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-monitor/《芋道 Spring Boot 监控工具 Admin 入门》.md`
- [Spring Boot Admin 官方文档](https://codecentric.github.io/spring-boot-admin/2.7.10/)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
