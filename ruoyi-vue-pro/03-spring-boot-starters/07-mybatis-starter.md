# 2.1 yudao-spring-boot-starter-mybatis 架构

> 理解 yudao MyBatis Starter 的整体架构，掌握 Starter 内部的分层设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解 yudao MyBatis Starter 的整体目录结构
- 理解 `config`、`core`、`util` 三个包的分层职责
- 掌握 BaseMapperX、QueryWrapperX、BaseDO 三大核心组件的关系
- 能快速定位 MyBatis 相关代码

## 📚 前置知识

- [01-starter-mechanism.md](./01-starter-mechanism.md)
- MyBatis-Plus 基础（BaseMapper、LambdaQueryWrapper；数据库篇见 [09-mybatis-vs-mp](../04-database/11-mybatis-vs-mp.md) / [10-base-mapper](../04-database/12-base-mapper.md)）
- [02-auto-configuration.md](./02-auto-configuration.md)

## 1. 核心概念

### 1.1 MyBatis Starter 的组成

```
yudao-spring-boot-starter-mybatis/
├── src/main/java/cn/iocoder/yudao/framework/
│   ├── datasource/                  # 多数据源
│   │   ├── config/                  # AutoConfiguration
│   │   └── core/                    # 动态数据源、过滤器
│   ├── mybatis/                     # MyBatis 增强（核心）
│   │   ├── config/                  # AutoConfiguration、EnvironmentPostProcessor
│   │   ├── core/
│   │   │   ├── dataobject/          # BaseDO
│   │   │   ├── mapper/              # BaseMapperX
│   │   │   ├── query/               # QueryWrapperX 系列
│   │   │   ├── handler/             # MetaObjectHandler
│   │   │   ├── type/                # TypeHandler
│   │   │   ├── enum/                # DbTypeEnum
│   │   │   └── util/                # JdbcUtils, MyBatisUtils
│   │   └── package-info.java
│   └── translate/                   # 翻译组件
└── src/main/resources/META-INF/spring/...imports
```

### 1.2 分层职责

| 包 | 职责 | 关键类 |
|----|------|--------|
| `config` | 装配（自动配置、Bean 注册） | `YudaoMybatisAutoConfiguration` |
| `core.dataobject` | 实体基类 | `BaseDO`（createTime、creator、deleted） |
| `core.mapper` | Mapper 增强 | `BaseMapperX`（selectPage、selectOne 等） |
| `core.query` | 查询条件包装器 | `LambdaQueryWrapperX`（eqIfPresent 等） |
| `core.handler` | 字段自动填充 | `DefaultDBFieldHandler` |
| `core.type` | 自定义类型转换器 | `EncryptTypeHandler`、`LongListTypeHandler` |
| `core.util` | 工具类 | `JdbcUtils`、`MyBatisUtils` |

## 2. 代码示例

### 2.1 一个使用 ruoyi MyBatis 的 Service

```java
// 文件：UserServiceImpl.java
package com.ruoyi.admin.service;

import cn.iocoder.yudao.framework.mybatis.core.mapper.BaseMapperX;
import cn.iocoder.yudao.framework.mybatis.core.query.LambdaQueryWrapperX;
import com.ruoyi.admin.dal.dataobject.UserDO;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.util.List;

@Service
public class UserServiceImpl implements UserService {

    @Resource
    private UserMapper userMapper;  // 继承 BaseMapperX<UserDO>

    public PageResult<UserDO> getUserPage(UserPageReqVO req) {
        return userMapper.selectPage(req, new LambdaQueryWrapperX<UserDO>()
                .likeIfPresent(UserDO::getName, req.getName())
                .eqIfPresent(UserDO::getStatus, req.getStatus())
                .orderByDesc(UserDO::getId));
    }
}
```

### 2.2 自定义实体继承 BaseDO

```java
// 文件：UserDO.java
package com.ruoyi.admin.dal.dataobject;

import cn.iocoder.yudao.framework.mybatis.core.dataobject.BaseDO;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("sys_user")
public class UserDO extends BaseDO {
    private String username;
    private String email;
    private Integer status;
}
```

### 2.3 Mapper 接口

```java
// 文件：UserMapper.java
package com.ruoyi.admin.dal.mysql;

import cn.iocoder.yudao.framework.mybatis.core.mapper.BaseMapperX;
import com.ruoyi.admin.dal.dataobject.UserDO;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface UserMapper extends BaseMapperX<UserDO> {
    // 继承 BaseMapperX 后自动拥有：
    // - selectPage, selectList, selectOne, insertBatch
    // - selectOneForUpdate
    // - 等等
}
```

## 3. 关键要点总结

- **yudao MyBatis Starter = MyBatis Plus + MyBatis Plus Join + 大量增强**
- **三大核心组件**：`BaseDO`（实体基类）、`BaseMapperX`（Mapper 基类）、`LambdaQueryWrapperX`（查询条件）
- **`@MapperScan` 用 `${yudao.info.base-package}`** 统一扫描
- **JsqlParser 缓存**通过 static 块在类加载时配置
- **支持多数据库**：通过 `IdTypeEnvironmentPostProcessor` 识别数据库类型

---

**文档版本**：v1.0
**最后更新**：2026-07-13
