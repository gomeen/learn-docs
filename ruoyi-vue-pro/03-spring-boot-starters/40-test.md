# 6.9 单测增强：SpringBootTestContext

> 掌握 yudao 的单元测试增强，能高效编写集成测试。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解 yudao 单测增强组件
- 掌握 `BaseDbUnitTest` 的使用
- 掌握 `BaseDbAndRedisUnitTest` 的使用
- 能在 yudao 中编写高质量单测

## 📚 前置知识

- JUnit 5
- Mockito
- Spring Boot Test
- H2 内存数据库

## 1. 核心概念

### 1.1 yudao 单测增强组件

| 组件 | 作用 |
|------|------|
| `BaseDbUnitTest` | DB 集成测试基类（自动加载 H2 + MyBatis） |
| `BaseDbAndRedisUnitTest` | DB + Redis 集成测试基类 |
| `BaseRedisUnitTest` | Redis 集成测试基类 |
| `RedisTestConfiguration` | 嵌入式 Redis（`it.ozimov:embedded-redis`） |
| `SqlInitializationTestConfiguration` | SQL 初始化配置 |

### 1.2 单测分层

| 层级 | 工具 | 速度 |
|------|------|------|
| 纯单元测试 | Mockito | 快 |
| DB 集成测试 | H2 + MyBatis | 中 |
| Redis 集成测试 | embedded-redis | 中 |
| Controller 测试 | @WebMvcTest | 中 |
| E2E 测试 | Selenium | 慢 |

## 2. 代码示例

### 2.1 DB 集成测试

```java
public class UserServiceImplTest extends BaseDbUnitTest {

    @Resource
    private UserService userService;

    @Test
    public void testCreateUser() {
        // 准备数据
        UserDO user = new UserDO();
        user.setUsername("test");
        // 调用
        Long id = userService.createUser(user);
        // 断言
        assertNotNull(id);
        UserDO dbUser = userMapper.selectById(id);
        assertEquals("test", dbUser.getUsername());
    }
}
```

### 2.2 Redis 集成测试

```java
public class RedisUtilsTest extends BaseDbAndRedisUnitTest {

    @Test
    public void testSetAndGet() {
        redisUtils.set("test:1", "hello", Duration.ofMinutes(1));
        String value = redisUtils.get("test:1", String.class);
        assertEquals("hello", value);
    }
}
```

### 2.3 Controller 测试

```java
@WebMvcTest(UserController.class)
public class UserControllerTest {
    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private UserService userService;

    @Test
    public void testGetUser() throws Exception {
        when(userService.getUser(1L)).thenReturn(new UserRespVO());

        mockMvc.perform(get("/admin-api/system/user/get").param("id", "1"))
                .andExpect(status().isOk());
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 BaseDbUnitTest

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-test/src/main/java/cn/iocoder/yudao/framework/test/core/ut/BaseDbUnitTest.java`
**核心代码**（节选）：

```java
public class BaseDbUnitTest {
    @Autowired
    protected DataSource dataSource;
    @Autowired
    protected SqlSessionFactory sqlSessionFactory;
    @Autowired
    protected DatabaseInitializer databaseInitializer;

    // 提供 Mapper 工具
    protected <T> T mapper(Class<T> clazz) {
        return sqlSessionFactory.openSession().getMapper(clazz);
    }
}
```

### 3.2 BaseDbAndRedisUnitTest

**核心代码**（节选）：

```java
public class BaseDbAndRedisUnitTest extends BaseDbUnitTest {
    @Autowired
    protected StringRedisTemplate stringRedisTemplate;
    @Autowired
    protected RedisTemplate<String, Object> redisTemplate;
    @Autowired
    protected RedissonClient redissonClient;

    @BeforeEach
    public void cleanRedis() {
        // 每个测试前清空 Redis
        redissonClient.getKeys().flushdb();
    }
}
```

**解读**：
- 自动注入 Redis 相关 Bean
- `@BeforeEach` 自动清空 Redis，避免测试间干扰

### 3.3 RedisTestConfiguration

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-test/src/main/java/cn/iocoder/yudao/framework/test/config/RedisTestConfiguration.java`
**核心代码**（节选）：

```java
@TestConfiguration
public class RedisTestConfiguration {
    @Bean
    public RedisServer redisServer() {
        return new RedisServer(6379);  // 启动嵌入式 Redis
    }
}
```

### 3.4 SqlInitializationTestConfiguration

```java
@TestConfiguration
public class SqlInitializationTestConfiguration {
    @Bean
    public DatabaseInitializer databaseInitializer(DataSource dataSource) {
        // 启动时执行 schema.sql + data.sql
    }
}
```

### 3.5 application-test.yml

```yaml
spring:
  datasource:
    url: jdbc:h2:mem:test;MODE=MySQL;DATABASE_TO_LOWER=TRUE
    username: sa
    password:
    driver-class-name: org.h2.Driver
  redis:
    host: 127.0.0.1
    port: 6379

yudao:
  tenant:
    enable: false  # 单测关闭多租户
```

## 4. 关键要点总结

- **`BaseDbUnitTest`** 提供 DB 集成测试基类
- **`BaseDbAndRedisUnitTest`** 提供 DB + Redis 基类
- **embedded-redis** 提供 Redis 单测能力
- **H2 内存数据库** 提供 DB 单测能力
- **单测前清空数据** 保证测试隔离

## 5. 练习题

### 练习 1：基础（必做）

为 `UserServiceImpl` 编写单测：测试 `createUser`、`getUser`、`deleteUser`。

### 练习 2：进阶

为 `OrderServiceImpl` 编写带 Redis 缓存的单测：验证缓存命中/失效逻辑。

### 练习 3：挑战（选做）

用 `@WebMvcTest` 编写 `UserController` 的 Controller 测试，覆盖所有接口。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-test/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-test/src/main/java/cn/iocoder/yudao/framework/test/core/ut/BaseDbUnitTest.java`
- Spring Boot Test 文档：https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.testing
- embedded-redis：https://github.com/ozimov/embedded-redis

---

**文档版本**：v1.0
**最后更新**：2026-07-13
