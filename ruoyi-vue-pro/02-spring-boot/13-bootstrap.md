# 12 Spring Boot 启动加载器

> 理解 Spring Boot 启动加载机制：`ApplicationContextInitializer`、`ApplicationRunner`、`CommandLineRunner`、监听 `ApplicationReadyEvent`。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Boot 启动过程中的扩展点
- 掌握 `ApplicationContextInitializer`（上下文初始化前）
- 掌握 `ApplicationRunner` / `CommandLineRunner`（启动后）
- 掌握 `ApplicationListener<ApplicationReadyEvent>`（就绪后）
- 能在 ruoyi-vue-pro 中识别和使用这些扩展点

## 📚 前置知识

- [01-ioc.md](./01-ioc.md)
- [08-startup.md](./08-startup.md)
- 事件机制见 [05-event](./05-event.md)

## 1. 核心概念

### 1.1 启动扩展点的 5 个位置

```
1. SpringApplicationRunListener          ← 启动前（监听 run 生命周期）
2. ApplicationContextInitializer         ← 上下文初始化（refresh 前）
3. BeanFactoryPostProcessor             ← Bean 定义加载后，实例化前
4. BeanPostProcessor                    ← Bean 实例化前后
5. ApplicationRunner / CommandLineRunner ← 启动完成
```

### 1.2 5 个 Spring Boot 事件

| 事件 | 触发时机 |
|------|---------|
| `ApplicationStartingEvent` | 启动最开始（环境未准备） |
| `ApplicationEnvironmentPreparedEvent` | 环境准备完成 |
| `ApplicationContextInitializedEvent` | 上下文创建完成 |
| `ApplicationPreparedEvent` | Bean 定义加载完成 |
| `ApplicationStartedEvent` | 上下文刷新完成 |
| `ApplicationReadyEvent` | **应用就绪**（可接收请求） |
| `ApplicationFailedEvent` | 启动失败 |

### 1.3 `ApplicationRunner` vs `CommandLineRunner`

| 特性 | `ApplicationRunner` | `CommandLineRunner` |
|------|--------------------|--------------------|
| 参数 | `ApplicationArguments`（已解析） | `String[]`（原始） |
| 顺序 | `@Order(n)` | `@Order(n)` |
| 触发 | 上下文刷新后 | 上下文刷新后 |

## 2. 代码示例

### 2.1 ApplicationContextInitializer

```java
// 文件：MyContextInitializer.java
@Order(Ordered.HIGHEST_PRECEDENCE)
public class MyContextInitializer implements ApplicationContextInitializer<ConfigurableApplicationContext> {
    @Override
    public void initialize(ConfigurableApplicationContext context) {
        // 在 Bean 实例化前设置属性
        context.getEnvironment().setActiveProfiles("dev");
    }
}
```

注册方式（在 `META-INF/spring.factories`）：

```properties
org.springframework.context.ApplicationContextInitializer=\
cn.iocoder.yudao.framework.config.MyContextInitializer
```

### 2.2 ApplicationRunner

```java
// 文件：CacheWarmupRunner.java
@Component
@Order(1)  // 在 BannerRunner 之后执行
public class CacheWarmupRunner implements ApplicationRunner {
    @Override
    public void run(ApplicationArguments args) throws Exception {
        log.info("[CacheWarmupRunner] 预热用户缓存...");
        userService.preloadCache();
    }
}
```

### 2.3 CommandLineRunner

```java
@Component
@Order(2)
public class StartupRunner implements CommandLineRunner {
    @Override
    public void run(String... args) throws Exception {
        log.info("启动参数: {}", Arrays.toString(args));
    }
}
```

### 2.4 监听 ApplicationReadyEvent

```java
@Component
public class StartupListener {
    @EventListener(ApplicationReadyEvent.class)
    public void onReady() {
        log.info("应用已就绪，监听端口: 8080");
    }
}
```

## 3. 关键要点总结

- **5 个启动扩展点**：`ApplicationContextInitializer` → `BeanFactoryPostProcessor` → `BeanPostProcessor` → `Runner` → 事件监听
- **Runner 是最常用的扩展点**（启动后执行初始化逻辑）
- **`@Order` 控制 Runner 顺序**（数字越小越先）
- **ruoyi 中通过 `BannerApplicationRunner` 输出启动 Banner**
- **ruoyi 中通过 `@EnableCaching` 启用缓存注解**
- **ruoyi 中通过 `@AutoConfiguration` + `@Bean` 集中管理 Bean 注册**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
