# 7.1.1 ruoyi 的业务模块划分

> 理解 ruoyi-vue-pro 中 20+ 业务模块的组织方式，能快速定位任意业务代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解 ruoyi-vue-pro 多模块 Maven 工程的整体结构
- 区分 `yudao-module-*` 业务模块与 `yudao-framework` 基础设施
- 掌握如何在 yudao-server 中激活/禁用业务模块
- 能根据业务关键词快速定位到对应模块

## 📚 前置知识

- Java 基础语法
- Maven 多模块项目基础
- Spring Boot 基础概念（详见 [IoC](../02-spring-boot/01-ioc.md)、[自动配置](../02-spring-boot/09-auto-config.md)）

## 1. 核心概念

### 1.1 多模块架构设计

ruoyi-vue-pro 采用 **Maven 多模块 + 业务垂直拆分** 的方式组织代码。每个业务都是一个独立的 Maven 子工程（`yudao-module-xxx`），可以独立打包、部署、复用。

**核心设计思想**：
- **业务模块（yudao-module-xxx）**：具体的业务实现（用户、订单、商品）
- **框架层（yudao-framework）**：通用能力（日志、安全、Redis、Web；Starter 机制详见 [03-spring-boot-starters](../03-spring-boot-starters/)）
- **启动模块（yudao-server）**：把所有模块打包成一个 Spring Boot 应用

```
ruoyi-vue-pro/
├── yudao-framework/          # 框架层：通用能力
│   ├── yudao-spring-boot-starter-web/        # Web 相关
│   ├── yudao-spring-boot-starter-security/   # 安全（详见 [06-security](../06-security/)）
│   ├── yudao-spring-boot-starter-redis/      # Redis（详见 [05-cache-and-mq](../05-cache-and-mq/)）
│   ├── yudao-spring-boot-starter-mybatis/    # MyBatis
│   └── ...
├── yudao-module-*/           # 业务模块层
│   ├── yudao-module-system/      # 系统管理
│   ├── yudao-module-infra/       # 基础设施
│   ├── yudao-module-mall/        # 商城（包含 4 个子模块）
│   ├── yudao-module-member/      # 会员中心
│   ├── yudao-module-bpm/         # 工作流
│   ├── yudao-module-crm/         # 客户管理
│   └── ...
└── yudao-server/             # 启动模块：打包入口
```

### 1.2 业务模块内部结构

每个业务模块内部都遵循统一的目录结构：

```
yudao-module-system/
├── pom.xml                            # Maven 配置
└── src/main/java/cn/iocoder/yudao/module/system/
    ├── controller/                    # Controller 层（HTTP 接口）
    │   └── admin/                     # 管理后台接口
    │       └── user/
    │           ├── UserController.java
    │           └── vo/                # VO（视图对象）
    ├── service/                       # Service 层（业务逻辑）
    │   └── user/
    │       └── AdminUserService.java
    ├── dal/                           # DAL 层（数据访问）
    │   ├── dataobject/                # DO（数据库实体）
    │   │   └── user/
    │   │       └── AdminUserDO.java
    │   └── mysql/                     # MyBatis Mapper
    │       └── user/
    │           └── AdminUserMapper.java
    ├── convert/                       # DTO/VO/DO 转换
    │   └── user/
    │       └── UserConvert.java
    ├── enums/                         # 业务枚举
    ├── framework/                     # 模块内部框架扩展
    └── package-info.java              # 包注释
```

**核心约定**：
- `controller/admin/`：管理后台接口（对应 vue-element-admin）
- `controller/app/`：用户端接口（对应 uni-app 商城）
- `controller/`：公共接口（OAuth2 等）
- `dal/dataobject/`：DO 对象，**与数据库表一一对应**
- `dal/mysql/`：MyBatis Mapper 接口和 XML

## 2. 代码示例

### 2.1 一个最简单的业务模块结构

```
yudao-module-demo/                    # 一个最小化的业务模块
├── pom.xml
└── src/main/java/cn/iocoder/yudao/module/demo/
    ├── controller/admin/
    │   └── DemoController.java
    ├── service/
    │   └── DemoService.java
    └── dal/
        ├── dataobject/
        │   └── DemoDO.java
        └── mysql/
            └── DemoMapper.java
```

```xml
<!-- yudao-module-demo/pom.xml -->
<parent>
    <groupId>cn.iocoder.yudao</groupId>
    <artifactId>yudao</artifactId>
    <version>${revision}</version>
</parent>
<artifactId>yudao-module-demo</artifactId>
```

### 2.2 yudao-server 启动模块如何聚合业务模块

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/pom.xml`

```xml
<dependencies>
    <!-- 系统模块 -->
    <dependency>
        <groupId>cn.iocoder.yudao</groupId>
        <artifactId>yudao-module-system</artifactId>
    </dependency>
    <!-- 基础设施 -->
    <dependency>
        <groupId>cn.iocoder.yudao</groupId>
        <artifactId>yudao-module-infra</artifactId>
    </dependency>
    <!-- 商城 -->
    <dependency>
        <groupId>cn.iocoder.yudao</groupId>
        <artifactId>yudao-module-mall</artifactId>
    </dependency>
    <!-- ... 其他模块 -->
</dependencies>
```

## 3. 关键要点总结

- ruoyi-vue-pro 使用 Maven 多模块架构，业务模块独立打包
- 业务模块（`yudao-module-*`）与框架（`yudao-framework`）解耦
- 每个业务模块都遵循 `controller/service/dal` 三层架构
- 通过 `yudao-server` 启动模块统一聚合所有业务
- `package-info.java` 写明每个模块的命名规范

---

**文档版本**：v1.0
**最后更新**：2026-07-13
