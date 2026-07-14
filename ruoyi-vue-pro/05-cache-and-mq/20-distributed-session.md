# 4.1 分布式 Session

> 理解分布式 Session 的核心问题和常见解决方案，掌握 ruoyi 的 Session 实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解分布式 Session 的产生背景（多实例下会话不共享）
- 掌握三种解决方案：Session 复制、Session 粘性、集中存储
- 看懂 ruoyi 如何用 Redis 集中存储 Session
- 能配置 ruoyi 的 Session 共享方案

## 📚 前置知识

- HTTP Session 基础
- Redis 基础（参见 `01-redis-basics.md`）

## 1. 核心概念

### 1.1 为什么 Session 不共享？

单机下，Session 存在 JVM 内存里。多实例下：
- 用户第一次访问实例 A，Session 在 A 内存
- 第二次请求被负载均衡到实例 B，B 内存没这个 Session
- 用户登录态丢失

### 1.2 三大解决方案

| 方案 | 描述 | 优缺点 |
|------|------|--------|
| Session 复制 | 实例间同步 Session | 简单，但带宽浪费 |
| Session 粘性 | 同一用户固定到同一实例 | 简单，但实例故障会丢 Session |
| 集中存储 | Session 存到 Redis/DB | 推荐，无状态实例 |

### 1.3 Spring Session

Spring Session 是 Spring 官方提供的 Session 集中存储框架，支持 Redis / JDBC / Hazelcast 等后端。ruoyi 默认启用 Spring Session + Redis。

## 2. 代码示例

### 2.1 引入依赖

```xml
<dependency>
    <groupId>org.springframework.session</groupId>
    <artifactId>spring-session-data-redis</artifactId>
</dependency>
```

### 2.2 application.yml

```yaml
spring:
  session:
    store-type: redis
    timeout: 30m
    redis:
      namespace: yudao:session
```

### 2.3 Controller 使用

```java
@RestController
public class DemoController {

    @GetMapping("/set")
    public String set(HttpSession session) {
        session.setAttribute("user", "yudao");
        return "ok";
    }

    @GetMapping("/get")
    public String get(HttpSession session) {
        return (String) session.getAttribute("user");
    }
}
```

任意实例都能拿到 `yudao`，因为 Session 在 Redis。

## 3. ruoyi 仓库源码解读

### 3.1 Spring Session 自动装配

ruoyi 在 `yudao-spring-boot-starter-security` 中启用 Spring Session：

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`

```java
// 伪代码，具体在 SecurityConfiguration
@Configuration
@EnableRedisHttpSession  // 启用 Spring Session + Redis
public class SessionConfig {
}
```

**解读**：
- `@EnableRedisHttpSession` 启用后，所有 `HttpSession` 自动改为从 Redis 读写
- Session key 存在 Cookie 中（`SESSION`）
- 业务代码完全无感知，依然用 `HttpSession.setAttribute/getAttribute`

### 3.2 ruoyi Session 的安全配置

ruoyi 在 Spring Security 集成中配置 Session：
- Session 创建策略：`IF_REQUIRED`
- Session 固定保护：`newSession`
- Session 失效时间：30 分钟（从配置文件）

### 3.3 Session 与 RedisTemplate 的协作

- Session 数据走 `RedisTemplate<String, Object>`（ruoyi 自定义 JSON 序列化）
- Cookie 中存的是 Session ID，Redis 中存的是实际数据
- 多实例共享：所有实例读同一个 Redis

## 4. 关键要点总结

- 分布式 Session 三方案：复制、粘性、集中存储
- 推荐用 Spring Session + Redis 集中存储
- ruoyi 启用 Spring Session，业务代码无感知
- Session 数据用 ruoyi 自定义的 JSON 序列化 RedisTemplate

## 5. 练习题

### 练习 1：基础（必做）

启动两个 Spring Boot 实例（端口 8080、8081），用 Nginx 负载均衡，验证 Session 共享。

### 练习 2：进阶

解释为什么"Session 粘性"方案在生产中不被推荐？什么场景下可以接受？

### 练习 3：挑战（选做）

用 Redis 手写一个分布式 Session：key=`session:{sessionId}`，value=JSON 序列化的 Map。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
- Spring Session 文档：https://docs.spring.io/spring-session/reference/

---

**文档版本**：v1.0
**最后更新**：2026-07-13