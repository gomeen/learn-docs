# 7.3.5 配置管理：动态配置

> 理解 ruoyi 的动态配置中心，无需重启即可修改配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 动态配置的实现
- 理解 `@Value` 注解与动态配置的区别
- 学会使用 `ConfigService` 读写配置
- 能实现自定义的动态配置

## 📚 前置知识

- Spring `@Value` 注解
- Nacos / Apollo 配置中心基础
- 06-common-result.md

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

## 3. ruoyi 仓库源码解读

### 3.1 ConfigController 核心代码

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/config/ConfigController.java`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 配置中心")
@RestController
@RequestMapping("/infra/config")
@Validated
public class ConfigController {

    @Resource
    private ConfigService configService;

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('infra:config:create')")
    public CommonResult<Long> createConfig(@Valid @RequestBody ConfigSaveReqVO createReqVO) {
        return success(configService.createConfig(createReqVO));
    }

    @GetMapping("/page")
    @PreAuthorize("@ss.hasPermission('infra:config:query')")
    public CommonResult<PageResult<ConfigRespVO>> getConfigPage(@Valid ConfigPageReqVO pageVO) {
        PageResult<ConfigDO> pageResult = configService.getConfigPage(pageVO);
        return success(BeanUtils.toBean(pageResult, ConfigRespVO.class));
    }

    @PutMapping("/update-value-by-key")
    @Operation(summary = "通过 key 更新配置 value")
    public CommonResult<Boolean> updateConfigValueByKey(@RequestParam("key") String key,
                                                        @RequestParam("value") String value) {
        configService.updateConfigValueByKey(key, value);
        return success(true);
    }
}
```

### 3.2 ConfigService 实现

```java
@Service
public class ConfigServiceImpl implements ConfigService {

    @Override
    public String getConfigValueByKey(String key) {
        return configMapper.selectByKey(key).getValue();
    }

    @Override
    public void updateConfigValueByKey(String key, String value) {
        ConfigDO config = validateConfigExists(key);
        config.setValue(value);
        configMapper.updateById(config);
    }
}
```

### 3.3 与 Nacos 的对比

ruoyi 的配置中心是**简化版**的 Nacos：

| 特性 | ruoyi Config | Nacos |
|------|--------------|-------|
| 持久化 | MySQL | MySQL |
| 实时推送 | 否（拉模式） | 是（推模式） |
| 配置分组 | 简单 | 命名空间+分组 |
| 灰度发布 | 否 | 是 |
| 监听器 | 无 | 支持 |

## 4. 关键要点总结

- ruoyi 配置中心用数据库 + 缓存实现
- 支持 CRUD、按 key 查询
- 修改后**需要业务方主动重读**（不主动推送）
- 适合**业务开关、白名单**等场景
- 复杂场景建议使用 Nacos / Apollo

## 5. 练习题

### 练习 1：基础（必做）

打开 `ConfigDO.java`，列出所有字段，理解每个字段的用途。

### 练习 2：进阶

阅读 `ConfigServiceImpl.java`，理解配置唯一性校验（key 唯一）。

### 练习 3：挑战（选做）

思考：如果要支持"配置修改后自动推送给业务方"，需要做哪些扩展？给出思路（提示：消息队列 + 监听器）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/config/ConfigController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/config/ConfigServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/config/ConfigDO.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
