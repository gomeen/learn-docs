# 24 ruoyi 的 Druid 配置

> 实战最后一篇：完整解读 ruoyi 的 Druid 配置，理解每行配置的作用和最佳实践。

## 🎯 学习目标

完成本文档后，你将能够：
- 完整阅读 ruoyi 的 Druid 配置
- 区分「监控配置」与「连接池配置」
- 知道生产环境的 Druid 安全配置
- 掌握 Druid 监控页面的使用方法

## 📚 前置知识

- [26-druid.md](./26-druid.md)
- [23-dynamic-datasource.md](./23-dynamic-datasource.md)
- [24-ds-annotation.md](./24-ds-annotation.md)

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

## 3. 关键要点总结

- ruoyi 的 Druid 配置 = 监控 + 连接池 + 多数据源三层
- 慢 SQL 阈值 `100ms` 是 ruoyi 的调优点
- 生产环境必须设置 Druid 监控的账号密码 + IP 白名单
- `multi-statement-allow` 是双刃剑：开发方便，生产危险
- `lazy: true` 让从库挂掉不影响启动

---

**文档版本**：v1.0
**最后更新**：2026-07-13
