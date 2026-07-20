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

## 3. 关键要点总结

- **`BaseDbUnitTest`** 提供 DB 集成测试基类
- **`BaseDbAndRedisUnitTest`** 提供 DB + Redis 基类
- **embedded-redis** 提供 Redis 单测能力
- **H2 内存数据库** 提供 DB 单测能力
- **单测前清空数据** 保证测试隔离

---

**文档版本**：v1.0
**最后更新**：2026-07-13
