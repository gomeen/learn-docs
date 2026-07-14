# 03 - 自研 Starter 框架

> ruoyi-vue-pro 的核心亮点：15+ 个自研 Spring Boot Starter。这些 Starter 实现了企业开发通用能力。

## 模块 3.1 Starter 基础

- [ ] [1.1 Spring Boot Starter 机制原理](./01-starter-mechanism.md)
- [ ] [1.2 AutoConfiguration 自动装配](./02-auto-configuration.md)
- [ ] [1.3 SPI 机制：META-INF/spring.factories 与 AutoConfiguration.imports](./03-spi.md)
- [ ] [1.4 @Conditional 条件装配](./04-conditional.md)
- [ ] [1.5 自研 Starter 实战：完整案例](./05-custom-starter-practice.md)

## 模块 3.2 MyBatis 与数据访问

- [ ] [2.1 yudao-spring-boot-starter-mybatis 架构](./06-mybatis-starter.md)
- [ ] [2.2 MyBatis Plus 核心功能](./07-mybatis-plus.md)
- [ ] [2.3 BaseMapper 与 ServiceImpl](./08-base-mapper.md)
- [ ] [2.4 分页插件：PaginationInnerInterceptor](./09-pagination.md)
- [ ] [2.5 数据权限（data-permission）实现](./10-data-permission.md)
- [ ] [2.6 多租户（tenant）SQL 拦截器](./11-tenant-interceptor.md)
- [ ] [2.7 慢 SQL 监控与打印](./12-slow-sql.md)
- [ ] [2.8 ruoyi 的 MyBatis 配置分析](./13-ruoyi-mybatis.md)

## 模块 3.3 Redis 与缓存

- [ ] [3.1 yudao-spring-boot-starter-redis 架构](./14-redis-starter.md)
- [ ] [3.2 Redisson 客户端](./15-redisson.md)
- [ ] [3.3 Redis 工具类：RedisUtils / RedisLockUtils](./16-redis-utils.md)
- [ ] [3.4 分布式锁：RLock](./17-distributed-lock.md)
- [ ] [3.5 限流：RRateLimiter](./18-rate-limiter.md)

## 模块 3.4 安全与权限

- [ ] [4.1 yudao-spring-boot-starter-security 架构](./19-security-starter.md)
- [ ] [4.2 Spring Security 核心概念](./20-spring-security.md)
- [ ] [4.3 Token 认证：JWT + Redis](./21-token-auth.md)
- [ ] [4.4 RBAC 数据模型设计](./22-rbac-model.md)
- [ ] [4.5 Spring Security 配置：SecurityFilterChain](./23-security-config.md)
- [ ] [4.6 注解权限控制：@PreAuthorize](./24-preauthorize.md)
- [ ] [4.7 数据权限：@DataPermission](./25-data-permission-annotation.md)

## 模块 3.5 消息队列

- [ ] [5.1 yudao-spring-boot-starter-mq 架构](./26-mq-starter.md)
- [ ] [5.2 统一消息抽象：Message](./27-message.md)
- [ ] [5.3 Redis Stream 实现](./28-redis-stream.md)
- [ ] [5.4 RabbitMQ 实现](./29-rabbitmq-impl.md)
- [ ] [5.5 Kafka 实现](./30-kafka-impl.md)
- [ ] [5.6 RocketMQ 实现](./31-rocketmq-impl.md)

## 模块 3.6 其他核心 Starter

- [ ] [6.1 Web 增强：CORS、参数、异常](./32-web-starter.md)
- [ ] [6.2 多租户：TenantContext / @TenantIgnore](./33-tenant.md)
- [ ] [6.3 定时任务：XXL-Job 集成](./34-xxl-job.md)
- [ ] [6.4 监控：Spring Boot Admin / Prometheus](./35-monitor.md)
- [ ] [6.5 接口保护：Sentinel 限流](./36-sentinel.md)
- [ ] [6.6 Excel 导入导出：EasyExcel](./37-excel.md)
- [ ] [6.7 WebSocket 集群：Redis Pub/Sub](./38-websocket.md)
- [ ] [6.8 IP 解析与地理位置](./39-ip.md)
- [ ] [6.9 单测增强：SpringBootTestContext](./40-test.md)

## 🎯 ruoyi-vue-pro 仓库对应位置

- Starter 目录：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/`
- 公共工具：`yudao-common/`
- 各 Starter：`yudao-spring-boot-starter-*/`
