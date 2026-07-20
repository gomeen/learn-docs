# 01 IoC 容器与依赖注入

> 理解 Spring IoC（控制反转）与 DI（依赖注入）的核心原理，能看懂 ruoyi-vue-pro 中所有 `@Autowired` / `@Resource` 注入逻辑。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 IoC 容器的本质：对象的创建、装配、生命周期都由容器管理
- 区分构造器注入、Setter 注入、字段注入的优缺点
- 掌握 `@Autowired` / `@Resource` / `@Inject` 的差异
- 能看懂 ruoyi-vue-pro 中 Controller / Service / Manager / DAO 之间的注入关系

## 📚 前置知识

- Java 基础语法（注解详见 [04-annotation](../01-java-fundamentals/04-annotation.md)，反射详见 [05-reflection](../01-java-fundamentals/05-reflection.md)，泛型详见 [03-generics](../01-java-fundamentals/03-generics.md)）
- Maven 多模块项目结构（详见 [11-maven-modules](../01-java-fundamentals/13-maven-modules.md)）

## 1. 核心概念

### 1.1 什么是 IoC？

IoC（Inversion of Control，控制反转）是一种**设计思想**——把对象的创建、依赖关系的管理从代码中"反转"给外部容器。

**对比**：

```java
// ❌ 传统方式：自己 new，自己管理依赖
public class UserService {
    private UserDao userDao = new UserDaoImpl();  // 强耦合
}

// ✅ IoC 方式：容器创建并注入
@Service
public class UserService {
    private final UserDao userDao;
    public UserService(UserDao userDao) {  // 容器注入
        this.userDao = userDao;
    }
}
```

### 1.2 DI：依赖注入的三种方式

| 方式 | 写法 | 优点 | 缺点 |
|------|------|------|------|
| **构造器注入** | `public XxxService(XxxDao dao) {...}` | 不可变、易测试、强制依赖 | 参数多时构造器臃肿 |
| **Setter 注入** | `@Autowired void setXxx(Xxx xxx) {...}` | 灵活、可选依赖 | 容易忘记注入导致 NPE |
| **字段注入** | `@Autowired private Xxx xxx;` | 简洁 | 不易测试、隐藏依赖、不可变对象无法用 |

**最佳实践**：强制依赖用构造器注入，可选依赖用 Setter，**避免字段注入**（ruoyi-vue-pro 大量使用 Lombok `@RequiredArgsConstructor` 实现构造器注入，详见 [14-lombok](../01-java-fundamentals/17-lombok.md)）。

### 1.3 常用注入注解

- `@Autowired`：Spring 原生，按**类型**匹配
- `@Resource`：JSR-250 标准，按**名称**匹配（更精确）
- `@Inject`：JSR-330 标准，需引入 `javax.inject`

## 2. 代码示例

### 2.1 构造器注入 + Lombok（推荐）

```java
// 文件：UserService.java
@Service
@RequiredArgsConstructor  // Lombok 自动生成包含 final 字段的构造器
public class UserService {

    private final UserDao userDao;        // 必须注入
    private final EmailService emailService;

    public UserDTO getUser(Long id) {
        UserDO user = userDao.selectById(id);
        emailService.sendWelcome(user.getEmail());
        return UserDTO.from(user);
    }
}
```

**说明**：
- `@RequiredArgsConstructor` 生成的构造器对所有 `final` 字段是隐式 `@Autowired` 的
- 字段被 `final` 修饰，保证不可变性
- 没有 Lombok 时，需手写构造器

### 2.2 常见错误：循环依赖

```java
// ❌ A 依赖 B，B 依赖 A → 启动失败
@Service
public class A {
    private final B b;
    public A(B b) { this.b = b; }
}

@Service
public class B {
    private final A a;
    public B(A a) { this.a = a; }
}
```

**解决**：抽取公共依赖到 C，或使用 `@Lazy` 延迟注入，或改用 Setter 注入。

## 3. 关键要点总结

- **IoC 本质**：对象生命周期由 Spring 容器管理，开发者只声明"需要什么"
- **推荐使用构造器注入**（配合 Lombok `@RequiredArgsConstructor`）
- `@Autowired` 按类型匹配，`@Resource` 按名称匹配
- ruoyi-vue-pro 大量使用 `@Bean` + Java Config 实现自动装配（`YudaoXxxAutoConfiguration`）
- ruoyi 通过 `@RestControllerAdvice` / `@Service` / `@Component` / `@Configuration` 标注 Bean

---

**文档版本**：v1.0
**最后更新**：2026-07-13
