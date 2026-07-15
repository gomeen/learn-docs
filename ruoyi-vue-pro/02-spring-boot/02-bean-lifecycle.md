# 02 Bean 生命周期与作用域

> 理解 Spring Bean 从创建到销毁的完整生命周期，以及 singleton / prototype / request 等作用域的差异。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Bean 生命周期的 5 个阶段：实例化 → 属性注入 → 初始化 → 使用 → 销毁
- 掌握 `@PostConstruct` / `@PreDestroy` / `InitializingBean` / `DisposableBean` 的使用场景
- 区分 singleton、prototype、request、session、application 作用域
- 能理解 ruoyi-vue-pro 中 Bean 的注册和销毁顺序

## 📚 前置知识

- [01-ioc.md](./01-ioc.md)（IoC 容器基础）
- Java 注解与反射（详见 [04-annotation](../01-java-fundamentals/04-annotation.md) / [05-reflection](../01-java-fundamentals/05-reflection.md)）

## 1. 核心概念

### 1.1 Bean 生命周期

一个 Bean 在 Spring 容器中经历以下阶段：

```
实例化（new） → 属性注入（@Autowired） → Aware 接口回调
→ BeanPostProcessor 前置处理 → @PostConstruct / InitializingBean
→ BeanPostProcessor 后置处理 → 使用阶段 → @PreDestroy / DisposableBean
```

### 1.2 初始化 / 销毁回调

| 方式 | 注解 / 接口 | 适用场景 |
|------|-----------|---------|
| JSR-250 | `@PostConstruct` / `@PreDestroy` | **推荐**，不依赖 Spring 接口 |
| Spring 接口 | `InitializingBean` / `DisposableBean` | 侵入式，但可读性高 |
| XML / `@Bean` | `init-method` / `destroy-method` | 第三方类无法改源码时使用 |
| BeanPostProcessor | `postProcessBeforeInitialization` / `postProcessAfterInitialization` | AOP 代理生成在这里（AOP 详见 [03-aop](./03-aop.md)） |

### 1.3 Bean 作用域

| 作用域 | 说明 | 使用场景 |
|--------|------|---------|
| **singleton**（默认） | 容器中只存在一个实例（单例模式详见 [单例](../../_fundamentals/06-design-patterns/01-singleton.md)） | 无状态 Service、DAO、Config |
| **prototype** | 每次获取都创建新实例 | 有状态对象、线程不安全 |
| **request** | 每个 HTTP 请求一个实例 | Web 请求上下文 |
| **session** | 每个 HTTP Session 一个实例 | 用户登录信息 |
| **application** | 每个 ServletContext 一个实例 | 全局配置 |
| **websocket** | 每个 WebSocket 一个实例 | 实时通信 |

## 2. 代码示例

### 2.1 完整生命周期示例

```java
@Component
public class LifecycleDemoBean implements InitializingBean, DisposableBean {

    public LifecycleDemoBean() {
        System.out.println("1. 构造器执行");
    }

    @Autowired
    public void setDependency(SomeService service) {
        System.out.println("2. 属性注入");
    }

    @PostConstruct
    public void postConstruct() {
        System.out.println("3. @PostConstruct");
    }

    @Override
    public void afterPropertiesSet() {
        System.out.println("4. afterPropertiesSet (InitializingBean)");
    }

    @PreDestroy
    public void preDestroy() {
        System.out.println("5. @PreDestroy");
    }

    @Override
    public void destroy() {
        System.out.println("6. destroy (DisposableBean)");
    }
}
```

### 2.2 作用域示例

```java
@Service
@Scope("prototype")  // 每次注入都创建新实例
public class CounterService {
    private int count = 0;
    public int increment() { return ++count; }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 启动 Banner 的初始化

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/banner/core/BannerApplicationRunner.java`
**核心代码**（行 1-30）：

```java
package cn.iocoder.yudao.framework.banner.core;

import cn.iocoder.yudao.framework.common.util.json.JsonUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * 项目启动 Banner
 *
 * @author 芋道源码
 */
@Slf4j
@Order(0)  // 越小越靠前
public class BannerApplicationRunner implements ApplicationRunner {
```

**解读**：
- 第 21 行：`implements ApplicationRunner` —— Spring Boot 提供的初始化接口
- 第 22 行：`@Order(0)` —— 多个 Runner 时优先执行
- **应用场景**：项目启动后打印 Banner（项目名、版本、Git Commit 等）
- **生命周期阶段**：ApplicationRunner#run 在所有 Bean 初始化完成后、应用就绪前执行

### 3.2 Web 工具类的初始化

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/util/WebFrameworkUtils.java`
**核心代码**（行 1-40）：

```java
package cn.iocoder.yudao.framework.web.core.util;

import cn.iocoder.yudao.framework.common.enums.WebFilterOrderEnum;
import cn.iocoder.yudao.framework.web.config.WebProperties;
import org.springframework.web.servlet.config.annotation.PathMatchConfigurer;
import javax.annotation.PostConstruct;

/**
 * 专属于 web 包下的工具类
 * 在 yudao-web 模块的 YudaoWebAutoConfiguration 中被注册为 Bean
 */
public class WebFrameworkUtils {

    private static WebProperties WEB_PROPERTIES;

    private final WebProperties webProperties;

    public WebFrameworkUtils(WebProperties webProperties) {
        this.webProperties = webProperties;
    }
```

**解读**：
- 第 19 行：通过构造器注入 `WebProperties` 配置类
- 第 24 行：`WEB_PROPERTIES` 静态字段保存配置，便于静态方法访问
- **设计意图**：把 Spring 管理的 Bean 属性复制到静态变量，让工具类的静态方法能直接读取（避免到处传 `WebProperties` 参数）
- **生命周期阶段**：构造器是 Bean 生命周期的"实例化"阶段

## 4. 关键要点总结

- **生命周期 5 阶段**：实例化 → 属性注入 → 初始化 → 使用 → 销毁
- **初始化推荐用 `@PostConstruct`**（JSR-250 标准，不依赖 Spring）
- **默认作用域是 singleton**（单例），无状态 Bean 优先使用
- **有状态 Bean 用 prototype**，但要注意不会调用 `@PreDestroy`
- ruoyi 中常用 `ApplicationRunner` 在启动后执行初始化逻辑

## 5. 练习题

### 练习 1：基础（必做）

编写一个 `CacheWarmupRunner` 实现 `ApplicationRunner`，在项目启动时预热 Redis 缓存（输出"缓存预热完成"日志即可）。

### 练习 2：进阶

阅读 `BannerApplicationRunner`，解释为什么用 `ApplicationRunner` 而不是 `@PostConstruct`？两者的执行时机有何区别？

### 练习 3：挑战（选做）

在 ruoyi-vue-pro 中搜索 `@Scope`，看是否有使用 prototype / request 作用域的地方。如果有，分析为什么不能用 singleton。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/banner/core/BannerApplicationRunner.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/util/WebFrameworkUtils.java`
- Spring 官方文档：https://docs.spring.io/spring-framework/reference/core/beans/factory-nature.html
- Bean 生命周期详解：https://www.cnblogs.com/zrtqsk/p/3735273.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
