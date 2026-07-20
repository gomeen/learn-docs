# 03 AOP 面向切面编程

> 理解 AOP 的核心思想（切面、连接点、通知、切入点），掌握 Spring AOP 在 ruoyi-vue-pro 中的应用（日志、权限、事务、API 加密）。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 AOP 的核心术语：Aspect、JoinPoint、Advice、Pointcut
- 区分 5 种通知类型：@Before、@After、@AfterReturning、@AfterThrowing、@Around
- 掌握 Spring AOP 底层原理（JDK 动态代理 vs CGLIB）
- 能看懂 ruoyi-vue-pro 中操作日志、访问日志、防重放等 AOP 切面

## 📚 前置知识

- [01-ioc.md](./01-ioc.md)（IoC 容器）
- Java 反射、动态代理（反射详见 [05-reflection](../01-java-fundamentals/05-reflection.md)；代理模式详见 [代理](../../_fundamentals/06-design-patterns/08-proxy.md)）

## 1. 核心概念

### 1.1 什么是 AOP？

AOP（Aspect-Oriented Programming，面向切面编程）把**横跨多个模块的重复逻辑**（日志、权限、事务）抽取成"切面"，集中管理（事务管理详见 [04-transaction](./04-transaction.md)）。

**OOP vs AOP**：
- OOP：按"业务维度"纵向切分（User、Order、Product）
- AOP：按"技术维度"横向切分（日志、权限、事务对所有业务都适用）

### 1.2 AOP 核心术语

| 术语 | 解释 |
|------|------|
| **Aspect（切面）** | 横切关注点的模块化（类 + 通知 + 切入点） |
| **JoinPoint（连接点）** | 程序执行过程中的某个点（方法调用、异常处理） |
| **Pointcut（切入点）** | 匹配连接点的表达式（哪些方法需要被拦截） |
| **Advice（通知）** | 在切入点执行的代码（@Before、@After、@Around） |
| **Introduction（引入）** | 为已有类型添加额外方法或字段 |
| **Target（目标对象）** | 被一个或多个切面通知的对象 |
| **AOP Proxy（AOP 代理）** | 由 AOP 框架创建的对象，用于实现切面契约 |
| **Weaving（织入）** | 把切面与其他应用对象连接以创建被通知对象的过程 |

### 1.3 5 种通知类型

```java
@Aspect
@Component
public class LogAspect {

    @Before("execution(* cn.iocoder..service..*(..))")
    public void before(JoinPoint jp) { /* 前置 */ }

    @After("execution(* cn.iocoder..service..*(..))")
    public void after(JoinPoint jp) { /* 后置（无论成功失败） */ }

    @AfterReturning(value = "execution(..)", returning = "result")
    public void afterReturning(JoinPoint jp, Object result) { /* 成功返回 */ }

    @AfterThrowing(value = "execution(..)", throwing = "ex")
    public void afterThrowing(JoinPoint jp, Throwable ex) { /* 抛异常 */ }

    @Around("execution(* cn.iocoder..service..*(..))")
    public Object around(ProceedingJoinPoint pjp) throws Throwable {
        // 前置逻辑
        Object result = pjp.proceed();  // 执行目标方法
        // 后置逻辑
        return result;
    }
}
```

### 1.4 Spring AOP 底层实现

- **JDK 动态代理**：目标类实现了接口，使用 `java.lang.reflect.Proxy`
- **CGLIB 代理**：目标类没有接口，生成子类继承目标类
- Spring Boot 2.x+ 默认使用 CGLIB（即使有接口也用 CGLIB）

## 2. 代码示例

### 2.1 自定义日志切面

```java
// 文件：OperationLogAspect.java
@Aspect
@Component
public class OperationLogAspect {

    private static final Logger log = LoggerFactory.getLogger(OperationLogAspect.class);

    @Around("@annotation(operationLog)")
    public Object around(ProceedingJoinPoint pjp, OperationLog operationLog) throws Throwable {
        long start = System.currentTimeMillis();
        try {
            Object result = pjp.proceed();
            long cost = System.currentTimeMillis() - start;
            log.info("[{}] 执行成功，耗时 {}ms", operationLog.value(), cost);
            return result;
        } catch (Throwable e) {
            log.error("[{}] 执行失败", operationLog.value(), e);
            throw e;
        }
    }
}
```

### 2.2 自定义注解

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface OperationLog {
    String value();
}

// 使用
@OperationLog("创建用户")
public void createUser(UserDTO dto) { ... }
```

## 3. 关键要点总结

- **AOP 解决横切关注点**（日志、权限、事务、加密）重复代码的问题
- **5 种通知**：@Before、@After、@AfterReturning、@AfterThrowing、@Around
- **Spring AOP 用动态代理**实现（JDK 代理 or CGLIB）
- ruoyi-vue-pro 通过 **Filter + Interceptor + AOP** 三层实现切面
- ruoyi 中操作日志、访问日志、API 加密、权限校验都是 AOP/拦截器的典型应用

---

**文档版本**：v1.0
**最后更新**：2026-07-13
