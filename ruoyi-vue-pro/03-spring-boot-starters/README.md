# 03 - 自研 Starter 框架

> ruoyi-vue-pro 的核心亮点：15+ 个自研 Spring Boot Starter。这些 Starter 实现了企业开发通用能力。

> **学习顺序**：按下方清单**从上到下**进行——读完一组文档后立刻做紧随其后的「✅ 小验证」，再继续下一组。练习已穿插在路径中间，不要把文档全部读完再回头找练习。

## 模块 3.1 Starter 基础

- [ ] [1.1 Spring Boot Starter 机制原理](./01-starter-mechanism.md)
- [ ] [1.2 AutoConfiguration 自动装配](./02-auto-configuration.md)
- [ ] [1.3 SPI 机制：META-INF/spring.factories 与 AutoConfiguration.imports](./03-spi.md)
- [ ] [1.4 @Conditional 条件装配](./04-conditional.md)
- [ ] [1.5 自研 Starter 实战：完整案例](./05-custom-starter-practice.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [06-*-starter-basics: Starter 机制与自研骨架](./06-*-starter-basics.md)
  - 覆盖：01-starter-mechanism.md, 02-auto-configuration.md, 03-spi.md, 04-conditional.md, 05-custom-starter-practice.md


## 模块 3.2 MyBatis 与数据访问

- [ ] [2.1 yudao-spring-boot-starter-mybatis 架构](./07-mybatis-starter.md)
- [ ] [2.2 MyBatis Plus 核心功能](./08-mybatis-plus.md)
- [ ] [2.3 BaseMapper 与 ServiceImpl](./09-base-mapper.md)
- [ ] [2.4 分页插件：PaginationInnerInterceptor](./10-pagination.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [11-*-mybatis-starter: MyBatis Starter / BaseMapper / 分页](./11-*-mybatis-starter.md)
  - 覆盖：07-mybatis-starter.md, 08-mybatis-plus.md, 09-base-mapper.md, 10-pagination.md

- [ ] [2.5 数据权限（data-permission）实现](./12-data-permission.md)
- [ ] [2.6 多租户（tenant）SQL 拦截器](./13-tenant-interceptor.md)
- [ ] [2.7 慢 SQL 监控与打印](./14-slow-sql.md)
- [ ] [2.8 ruoyi 的 MyBatis 配置分析](./15-ruoyi-mybatis.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [16-*-mybatis-tenant: 数据权限 / 租户拦截器 / 慢 SQL / ruoyi MyBatis](./16-*-mybatis-tenant.md)
  - 覆盖：12-data-permission.md, 13-tenant-interceptor.md, 14-slow-sql.md, 15-ruoyi-mybatis.md


## 模块 3.3 Redis 与缓存

- [ ] [3.1 yudao-spring-boot-starter-redis 架构](./17-redis-starter.md)
- [ ] [3.2 Redisson 客户端](./18-redisson.md)
- [ ] [3.3 Redis 工具类：RedisUtils / RedisLockUtils](./19-redis-utils.md)
- [ ] [3.4 分布式锁：RLock](./20-distributed-lock.md)
- [ ] [3.5 限流：RRateLimiter](./21-rate-limiter.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [22-*-redis-starter: Redis Starter / Redisson / 分布式锁 / 限流](./22-*-redis-starter.md)
  - 覆盖：17-redis-starter.md, 18-redisson.md, 19-redis-utils.md, 20-distributed-lock.md, 21-rate-limiter.md


## 模块 3.4 安全与权限

- [ ] [4.1 yudao-spring-boot-starter-security 架构](./23-security-starter.md)
- [ ] [4.2 Spring Security 核心概念](./24-spring-security.md)
- [ ] [4.3 Token 认证：JWT + Redis](./25-token-auth.md)
- [ ] [4.4 RBAC 数据模型设计](./26-rbac-model.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [27-*-security-starter: Security Starter / Token / RBAC 基础](./27-*-security-starter.md)
  - 覆盖：23-security-starter.md, 24-spring-security.md, 25-token-auth.md, 26-rbac-model.md

- [ ] [4.5 Spring Security 配置：SecurityFilterChain](./28-security-config.md)
- [ ] [4.6 注解权限控制：@PreAuthorize](./29-preauthorize.md)
- [ ] [4.7 数据权限：@DataPermission](./30-data-permission-annotation.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [31-*-security-annotate: Security 配置 / @PreAuthorize / 数据权限注解](./31-*-security-annotate.md)
  - 覆盖：28-security-config.md, 29-preauthorize.md, 30-data-permission-annotation.md


## 模块 3.5 消息队列

- [ ] [5.1 yudao-spring-boot-starter-mq 架构](./32-mq-starter.md)
- [ ] [5.2 统一消息抽象：Message](./33-message.md)
- [ ] [5.3 Redis Stream 实现](./34-redis-stream.md)
- [ ] [5.4 RabbitMQ 实现](./35-rabbitmq-impl.md)
- [ ] [5.5 Kafka 实现](./36-kafka-impl.md)
- [ ] [5.6 RocketMQ 实现](./37-rocketmq-impl.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [38-*-mq-starter: MQ 抽象与多实现](./38-*-mq-starter.md)
  - 覆盖：32-mq-starter.md, 33-message.md, 34-redis-stream.md, 35-rabbitmq-impl.md, 36-kafka-impl.md, 37-rocketmq-impl.md


## 模块 3.6 其他核心 Starter

- [ ] [6.1 Web 增强：CORS、参数、异常](./39-web-starter.md)
- [ ] [6.2 多租户：TenantContext / @TenantIgnore](./40-tenant.md)
- [ ] [6.3 定时任务：XXL-Job 集成](./41-xxl-job.md)
- [ ] [6.4 监控：Spring Boot Admin / Prometheus](./42-monitor.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [43-*-other-starters: Web / 多租户 / Job / 监控 Starter](./43-*-other-starters.md)
  - 覆盖：39-web-starter.md, 40-tenant.md, 41-xxl-job.md, 42-monitor.md

- [ ] [6.5 接口保护：Sentinel 限流](./44-sentinel.md)
- [ ] [6.6 Excel 导入导出：EasyExcel](./45-excel.md)
- [ ] [6.7 WebSocket 集群：Redis Pub/Sub](./46-websocket.md)
- [ ] [6.8 IP 解析与地理位置](./47-ip.md)
- [ ] [6.9 单测增强：SpringBootTestContext](./48-test.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [49-*-sentinel-excel: Sentinel / Excel / WebSocket / IP / 测试](./49-*-sentinel-excel.md)
  - 覆盖：44-sentinel.md, 45-excel.md, 46-websocket.md, 47-ip.md, 48-test.md


## 🎯 ruoyi-vue-pro 仓库对应位置

- Starter 目录：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/`
- 公共工具：`yudao-common/`
- 各 Starter：`yudao-spring-boot-starter-*/`
