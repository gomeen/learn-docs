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

## 3. 关键要点总结

- **生命周期 5 阶段**：实例化 → 属性注入 → 初始化 → 使用 → 销毁
- **初始化推荐用 `@PostConstruct`**（JSR-250 标准，不依赖 Spring）
- **默认作用域是 singleton**（单例），无状态 Bean 优先使用
- **有状态 Bean 用 prototype**，但要注意不会调用 `@PreDestroy`
- ruoyi 中常用 `ApplicationRunner` 在启动后执行初始化逻辑

---

**文档版本**：v1.0
**最后更新**：2026-07-13
