# 24 ruoyi 的 Druid 配置

> 实战最后一篇：完整解读 ruoyi 的 Druid 配置，理解每行配置的作用和最佳实践。

## 🎯 学习目标

完成本文档后，你将能够：
- 完整阅读 ruoyi 的 Druid 配置
- 区分「监控配置」与「连接池配置」
- 知道生产环境的 Druid 安全配置
- 掌握 Druid 监控页面的使用方法

## 📚 前置知识

- 22-druid.md
- 19-dynamic-datasource.md
- 20-ds-annotation.md

## 1. 核心概念

### 1.1 ruoyi Druid 配置全景

```
spring.datasource.
├── druid (监控)
│   ├── web-stat-filter       # URI 监控
│   ├── stat-view-servlet     # Web 监控页面
│   ├── filter.stat           # SQL 监控 + 慢 SQL
│   └── filter.wall           # SQL 防火墙
└── dynamic (数据源切换)
    ├── druid (连接池)         # 连接池参数
    ├── primary                # 默认数据源
    └── datasource             # 数据源列表
```

### 1.2 监控 vs 连接池

| 维度 | spring.datasource.druid | spring.datasource.dynamic.druid |
|------|------------------------|---------------------------------|
| 作用 | 监控、慢 SQL、防火墙 | 连接池参数（连接数、超时） |
| 必填 | 否（默认全关） | 是 |

### 1.3 生产环境必备配置

1. `stat-view-servlet.login-username/password` —— 必须设置密码
2. `stat-view-servlet.allow` —— 设置 IP 白名单
3. `wall.config.multi-statement-allow` —— 默认 false，按需开启
4. `filter.stat.slow-sql-millis` —— 根据业务调整阈值

## 2. 代码示例

### 2.1 开发环境 Druid 完整配置

```yaml
spring:
  datasource:
    # ========== Druid 监控配置 ==========
    druid:
      web-stat-filter:
        enabled: true
        exclusions: '*.js,*.gif,*.jpg,*.png,*.css,*.ico,/druid/*'  # 不监控静态资源
      stat-view-servlet:
        enabled: true
        url-pattern: /druid/*
        login-username: admin
        login-password: admin
        allow: 127.0.0.1,192.168.1.*  # IP 白名单
      filter:
        stat:
          enabled: true
          log-slow-sql: true
          slow-sql-millis: 100
          merge-sql: true
        wall:
          config:
            multi-statement-allow: true
            # 禁止的 SQL 类型（生产可更严格）
            noneBaseStatementAllow: false
    # ========== 连接池参数（在 dynamic 下）==========
    dynamic:
      druid:
        initial-size: 1
        min-idle: 1
        max-active: 20
        max-wait: 60000
        validation-query: SELECT 1 FROM DUAL
        test-while-idle: true
        pool-prepared-statements: true
        max-pool-prepared-statement-per-connection-size: 20
      primary: master
      datasource:
        master:
          url: jdbc:mysql://127.0.0.1:3306/ruoyi-vue-pro
          username: root
          password: 123456
        slave:
          lazy: true
          url: jdbc:mysql://127.0.0.1:3306/ruoyi-vue-pro
          username: root
          password: 123456
```

### 2.2 生产环境安全配置

```yaml
spring:
  datasource:
    druid:
      stat-view-servlet:
        enabled: true
        url-pattern: /druid/*          # 可改名为隐蔽路径
        login-username: ${DRUID_USER}  # 从环境变量读取
        login-password: ${DRUID_PASS}  # 不要硬编码！
        allow: 10.0.0.0/8,172.16.0.0/12  # 仅内网 IP
        deny: 0.0.0.0/0                # 默认拒绝所有
        reset-enable: false            # 禁用「重置」功能
      filter:
        wall:
          config:
            multi-statement-allow: false  # 生产禁止多语句
            deleteAllow: false           # 禁止 DELETE（应用层校验代替）
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 完整 Druid 配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
**核心代码**（行 4-50）：

```yaml
--- #################### 数据库相关配置 ####################
spring:
  autoconfigure:
    exclude:
      - com.alibaba.druid.spring.boot.autoconfigure.DruidDataSourceAutoConfigure  # 排除 Druid 自动配置
      - org.springframework.boot.autoconfigure.quartz.QuartzAutoConfiguration
  # 数据源配置项
  datasource:
    druid: # Druid 【监控】相关的全局配置
      web-stat-filter:
        enabled: true
      stat-view-servlet:
        enabled: true
        allow: # 设置白名单，不填则允许所有访问
        url-pattern: /druid/*
        login-username: # 控制台管理用户名和密码
        login-password:
      filter:
        stat:
          enabled: true
          log-slow-sql: true # 慢 SQL 记录
          slow-sql-millis: 100
          merge-sql: true
        wall:
          config:
            multi-statement-allow: true
    dynamic: # 多数据源配置
      druid: # Druid 【连接池】相关的全局配置
        initial-size: 1 # 初始连接数
        min-idle: 1 # 最小连接池数量
        max-active: 20 # 最大连接池数量
        max-wait: 60000 # 配置获取连接等待超时的时间
        time-between-eviction-runs-millis: 60000
        min-evictable-idle-time-millis: 600000
        max-evictable-idle-time-millis: 1800000
        validation-query: SELECT 1 FROM DUAL
        test-while-idle: true
        test-on-borrow: false
        test-on-return: false
        pool-prepared-statements: true
        max-pool-prepared-statement-per-connection-size: 20
      primary: master
      datasource:
        master:
          url: jdbc:mysql://127.0.0.1:3306/ruoyi-vue-pro-jdk8
          username: root
          password: 123456
        slave:
          lazy: true
          url: jdbc:mysql://127.0.0.1:3306/ruoyi-vue-pro-jdk8
          username: root
          password: 123456
```

**完整解读**：

#### A. 自动配置排除（行 5-10）
- **第 8 行**：排除 Druid 自动配置 → 让 dynamic-datasource 接管 Druid 的初始化
- **第 9 行**：排除 Quartz（开发环境不开）

#### B. 监控配置（行 13-32）
- **第 14-15 行**（web-stat-filter）：启用 URI 级别监控
- **第 16-21 行**（stat-view-servlet）：监控页面 `/druid/*`
  - `allow:` 空 → 开发环境允许所有（生产必须配置）
  - `login-username/login-password:` 空 → 无密码（生产必须设置）
- **第 22-28 行**（filter.stat）：慢 SQL 监控
  - `slow-sql-millis: 100` → ruoyi 调优点（100ms）
  - `merge-sql: true` → 合并相似 SQL
- **第 29-32 行**（filter.wall）：SQL 防火墙
  - `multi-statement-allow: true` → 允许多语句（ruoyi 批量更新需要）

#### C. 连接池参数（行 33-48）
- `initial-size: 1` → 启动时建 1 个连接
- `max-active: 20` → 最大 20 个并发
- `max-wait: 60000` → 等待连接超时 60s
- `pool-prepared-statements: true` → 启用 PreparedStatement 缓存

#### D. 数据源列表（行 49-）
- `master` 写库
- `slave` 读库（`lazy: true` 懒加载，避免启动时从库挂掉导致整个应用启动失败）

### 3.2 监控文档说明

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/《芋道 Spring Boot 数据库连接池入门》.md`

**关键章节**：

> **Druid 监控页面使用说明**：
> 1. 启动应用后访问 `http://localhost:48080/druid/`
> 2. 无密码直接进入（开发环境），生产环境需配置账号密码
> 3. 主要功能：
>    - **数据源**：查看所有数据源 + 活跃连接数
>    - **SQL 监控**：每条 SQL 的执行次数、时间分布、最大耗时
>    - **SQL 防火墙**：被拦截的 SQL 记录
>    - **Web 应用**：URI 请求统计
> 4. 慢 SQL 排查流程：进入 SQL 监控 → 按耗时排序 → 找最慢的几条 → 用 EXPLAIN 分析 → 加索引或改写

### 3.3 多环境差异化配置

**位置**：对比 `application-local.yaml`、`application-dev.yaml`、`application.yaml`

```yaml
# application.yaml（生产）
spring:
  datasource:
    druid:
      stat-view-servlet:
        enabled: false  # 生产环境关闭监控页面（通过 Nginx / Gateway 屏蔽）
      filter:
        wall:
          config:
            multi-statement-allow: false  # 生产禁止
```

**解读**：
- ruoyi 通过 `application-{profile}.yaml` 实现多环境配置
- **生产最佳实践**：通过 Nginx 只暴露 8080，禁用 `/druid/*` 路径
- **进一步**：可通过 Spring Profile 控制 Druid 是否启用

## 4. 关键要点总结

- ruoyi 的 Druid 配置 = 监控 + 连接池 + 多数据源三层
- 慢 SQL 阈值 `100ms` 是 ruoyi 的调优点
- 生产环境必须设置 Druid 监控的账号密码 + IP 白名单
- `multi-statement-allow` 是双刃剑：开发方便，生产危险
- `lazy: true` 让从库挂掉不影响启动

## 5. 练习题

### 练习 1：基础（必做）

启动 ruoyi，访问 `/druid/` 页面，进入「SQL 监控」，执行一些业务请求，观察哪些 SQL 出现次数最多、平均耗时多少。

### 练习 2：进阶

修改 `application-local.yaml`，将 `slow-sql-millis` 改为 `50`（更严格），重启应用，触发任意耗时 > 50ms 的 SQL，验证日志中是否打印慢 SQL 警告。

### 练习 3：挑战（选做）

设计一份「ruoyi Druid 生产环境配置清单」，包含：
1. 必改的安全配置（密码、白名单）
2. 推荐的连接池参数（依据业务规模）
3. 监控告警方案（慢 SQL、连接池满的告警阈值）
4. 多环境差异化配置（dev / staging / prod）

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-dev.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/《芋道 Spring Boot 数据库连接池入门》.md`
- Druid 官方文档：https://github.com/alibaba/druid

---

**文档版本**：v1.0
**最后更新**：2026-07-13