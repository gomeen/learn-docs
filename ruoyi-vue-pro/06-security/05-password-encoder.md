# 5 PasswordEncoder：BCrypt 加密

> 详解 BCrypt 加密算法的原理、Spring Security 的 `PasswordEncoder`，以及 ruoyi 的密码加密实践。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解为什么不能用 MD5/SHA 加密密码
- 理解 BCrypt 算法的"盐（salt）"机制
- 掌握 `PasswordEncoder.matches()` 的用法
- 看懂 ruoyi 的 `isPasswordMatch` 实现

## 📚 前置知识

- Java 基础
- 04-user-details.md

## 1. 核心概念

### 1.1 为什么需要 PasswordEncoder？

**❌ 错误方案：明文存储**
```java
user.setPassword("123456");  // 灾难！数据库被脱裤后所有密码泄露
```

**❌ 错误方案：MD5/SHA 哈希**
```java
// 看似安全，但两个问题：
// 1. 同样的明文 → 同样的哈希（彩虹表攻击）
// 2. GPU 一秒能算 100 亿次 MD5（暴力破解）
String hash = DigestUtils.md5Hex("123456");  // e10adc3949ba59abbe56e057f20f883e
```

**✅ 正确方案：BCrypt 等自适应哈希**
- **盐（Salt）**：每次加密随机生成盐，结果不同 → 防彩虹表
- **慢哈希**：故意设计成慢，暴力破解成本高
- **成本因子**：可调整计算耗时（默认 10~12）

### 1.2 BCrypt 算法

```
$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy
│  │  │                       │
│  │  │                       └── 22 字符的盐+哈希（Base64）
│  │  └────────────────────────── 盐
│  └──────────────────────────── 成本因子（2^10 = 1024 轮）
└─────────────────────────────── 算法版本
```

### 1.3 Spring Security 的 PasswordEncoder 接口

```java
public interface PasswordEncoder {
    String encode(CharSequence rawPassword);
    boolean matches(CharSequence rawPassword, String encodedPassword);
}
```

## 2. 代码示例

### 2.1 基础用法

```java
// 文件：PasswordConfig.java
@Configuration
public class PasswordConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        // 成本因子 10（默认）
        return new BCryptPasswordEncoder();
        // 或：return new BCryptPasswordEncoder(4);  // 调试时用 4，生产用 10+
    }
}

// 使用
@Service
public class UserService {
    @Resource
    private PasswordEncoder passwordEncoder;

    public void register(String username, String rawPassword) {
        // 1. 加密
        String hashed = passwordEncoder.encode(rawPassword);
        // 同一个 rawPassword 每次结果不同
        System.out.println(hashed);  // $2a$10$abc...
        System.out.println(passwordEncoder.encode(rawPassword));  // $2a$10$xyz...

        // 2. 保存到数据库
        userMapper.insert(new UserDO(username, hashed));
    }

    public boolean login(String username, String rawPassword) {
        UserDO user = userMapper.selectByUsername(username);
        // 3. 校验
        return passwordEncoder.matches(rawPassword, user.getPassword());
    }
}
```

### 2.2 常见错误

```java
// ❌ 错误 1：自己实现加密逻辑
String hash = rawPassword + "salt";
String hash2 = DigestUtils.sha256Hex(rawPassword);  // 没有盐，可被彩虹表

// ❌ 错误 2：自己比较哈希
if (user.getPassword().equals(passwordEncoder.encode(input)))  {
    // encode() 每次结果不同，永远 false
}

// ✅ 正确：用 matches() 方法
if (passwordEncoder.matches(input, user.getPassword())) {
    // 正确
}
```

## 3. ruoyi 仓库源码解读

### 3.1 SecurityProperties 的成本因子配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/SecurityProperties.java`
**核心代码**（行 47-50）：

```java
/**
 * PasswordEncoder 加密复杂度，越高开销越大
 */
private Integer passwordEncoderLength = 4;
```

**解读**：
- 默认值是 `4`（仅用于开发调试）
- 生产环境应该改成 `10` 或更高
- 通过 `yudao.security.password-encoder-length` 配置项调整

### 3.2 isPasswordMatch 实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/auth/AdminAuthServiceImpl.java`
**核心代码**（行 88-91）：

```java
// 2. 校验密码
if (!userService.isPasswordMatch(password, user.getPassword())) {
    createLoginLog(user.getId(), username, logTypeEnum, LoginResultEnum.BAD_CREDENTIALS);
    throw exception(AUTH_LOGIN_BAD_CREDENTIALS);
}
```

**isPasswordMatch 通常实现**（在 `AdminUserServiceImpl` 中）：

```java
public boolean isPasswordMatch(String rawPassword, String encodedPassword) {
    return passwordEncoder.matches(rawPassword, encodedPassword);
}
```

**解读**：
- 调用 `passwordEncoder.matches(rawPassword, encodedPassword)`：BCrypt 会**自动从 `encodedPassword` 中提取盐**，再哈希 `rawPassword` 比较
- 同一个密码每次 `matches()` 都能正确比对（即使两次 `encode` 结果不同）

### 3.3 TokenAuthenticationFilter 中的 token 校验

虽然 Filter 不直接用 `PasswordEncoder`，但展示了**另一种"匹配"思路**：
- **密码场景**：`passwordEncoder.matches(raw, encoded)` — 同密码不同结果也能匹配
- **Token 场景**：`oauth2TokenApi.checkAccessToken(token)` — 从 Redis 查找对应的 access_token

两者都是"无状态校验"的经典实现。

## 4. 关键要点总结

- 永远不要用 MD5/SHA 加密密码（彩虹表 + 暴力破解）
- BCrypt 自带盐、自带慢哈希，是 Spring Security 默认推荐
- `passwordEncoder.matches(raw, encoded)` 内部自动提取盐
- 生产环境密码成本因子建议 ≥ 10
- ruoyi 通过 `yudao.security.password-encoder-length` 配置

## 5. 练习题

### 练习 1：基础（必做）

写一个测试，对同一个字符串调用 `BCryptPasswordEncoder().encode()` 三次，观察结果是否相同。解释为什么。

### 练习 2：进阶

实现一个 `UpgradePasswordService`，把数据库中所有 MD5 加密的旧密码**平滑升级**到 BCrypt。提示：登录时判断密码格式，是 MD5 就升级为 BCrypt。

### 练习 3：挑战（选做）

使用 `BCryptPasswordEncoder(4)` 跑压测，记录每秒能加密多少次密码。改成 `BCryptPasswordEncoder(10)` 后性能如何变化？分析成本因子对安全性和性能的影响。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/SecurityProperties.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/auth/AdminAuthServiceImpl.java`
- Spring Security PasswordEncoder：https://docs.spring.io/spring-security/reference/features/authentication/password-storage.html
- BCrypt 算法原理：https://en.wikipedia.org/wiki/Bcrypt

---

**文档版本**：v1.0
**最后更新**：2026-07-13
