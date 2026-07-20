# 7.3.5 配置管理：动态配置

> 理解 ruoyi 的动态配置中心，无需重启即可修改配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 动态配置的实现
- 理解 `@Value` 注解与动态配置的区别
- 学会使用 `ConfigService` 读写配置
- 能实现自定义的动态配置

## 📚 前置知识

- Spring 配置与 `@Value`（详见 [配置](../02-spring-boot/11-config.md)）
- Nacos / Apollo 配置中心基础
- 统一响应（详见 [CommonResult](./05-common-result.md)）
- 配置缓存（详见 [ruoyi 缓存场景](../05-cache-and-mq/11-ruoyi-cache-usage.md)）

## 1. 核心概念

### 1.1 静态配置 vs 动态配置

| 维度 | 静态配置 | 动态配置 |
|------|----------|----------|
| 修改方式 | 改 `application.yml`，重启 | 改数据库，实时生效 |
| 适用场景 | 不会变的参数 | 业务开关、阈值、白名单 |
| 实现方式 | `@Value` / `@ConfigurationProperties` | 数据库 + 缓存 |

### 1.2 ruoyi 配置中心设计

```
[数据库 infra_config] → [ConfigService 读取] → [Redis 缓存] → [业务代码]
       ↑
       │ 修改
[管理后台 API] ← 实时刷新
```

**特点**：
- 配置存储在 `infra_config` 表
- **不重启生效**（业务代码每次调用都查 Redis）
- 支持按 key 查询

### 1.3 核心字段

```java
public class ConfigDO {
    private Long id;
    private String configKey;    // 配置 key
    private String value;        // 配置 value
    private String name;         // 配置名
    private String category;     // 分类
    private String type;         // 类型（input/textarea/select）
    private String remark;       // 备注
    private LocalDateTime updateTime;
}
```

## 2. 代码示例

### 2.1 ConfigService 使用

```java
@Resource
private ConfigService configService;

// 读取配置
String value = configService.getConfigValueByKey("system.index.banner");

// 带默认值
String value = configService.getConfigValueByKey("user.register.captcha", "true");
```

### 2.2 业务代码使用

```java
@Service
public class SmsServiceImpl {

    @Resource
    private ConfigService configService;

    public void sendSms(String mobile) {
        // 读取短信开关
        Boolean enabled = configService.getConfigValueByKeyBoolean("sms.enabled");
        if (!enabled) {
            log.warn("[sendSms][短信功能已禁用]");
            return;
        }
        // 读取阿里云 AccessKey
        String accessKey = configService.getConfigValueByKey("sms.aliyun.access-key");
        // ... 发送短信
    }
}
```

### 2.3 ConfigController

```java
@PostMapping("/create")
@PreAuthorize("@ss.hasPermission('infra:config:create')")
public CommonResult<Long> createConfig(@Valid @RequestBody ConfigSaveReqVO createReqVO) {
    return success(configService.createConfig(createReqVO));
}

@PutMapping("/update-value-by-key")
@Operation(summary = "通过 key 更新配置 value")
public CommonResult<Boolean> updateConfigValueByKey(@RequestParam("key") String key,
                                                     @RequestParam("value") String value) {
    configService.updateConfigValueByKey(key, value);
    return success(true);
}
```

## 3. 关键要点总结

- ruoyi 配置中心用数据库 + 缓存实现
- 支持 CRUD、按 key 查询
- 修改后**需要业务方主动重读**（不主动推送）
- 适合**业务开关、白名单**等场景
- 复杂场景建议使用 Nacos / Apollo

---

**文档版本**：v1.0
**最后更新**：2026-07-13
