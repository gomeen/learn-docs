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
- MyBatis-Plus 基础（BaseMapper、LambdaQueryWrapper）
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

## 3. ruoyi 仓库源码解读

### 3.1 主 AutoConfiguration

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
**核心代码**（行 34-95）：

```java
@AutoConfiguration(before = MybatisPlusAutoConfiguration.class)
@MapperScan(value = "${yudao.info.base-package}", annotationClass = Mapper.class,
        lazyInitialization = "${mybatis.lazy-initialization:false}")
public class YudaoMybatisAutoConfiguration {

    static {
        // 动态 SQL 智能优化支持本地缓存加速解析
        JsqlParserGlobal.setJsqlParseCache(new JdkSerialCaffeineJsqlParseCache(
                (cache) -> cache.maximumSize(1024)
                        .expireAfterWrite(5, TimeUnit.SECONDS))
        );
    }

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor mybatisPlusInterceptor = new MybatisPlusInterceptor();
        mybatisPlusInterceptor.addInnerInterceptor(new PaginationInnerInterceptor());
        return mybatisPlusInterceptor;
    }

    @Bean
    public MetaObjectHandler defaultMetaObjectHandler() {
        return new DefaultDBFieldHandler();
    }

    @Bean
    @ConditionalOnProperty(prefix = "mybatis-plus.global-config.db-config", name = "id-type", havingValue = "INPUT")
    public IKeyGenerator keyGenerator(ConfigurableEnvironment environment) {
        DbType dbType = IdTypeEnvironmentPostProcessor.getDbType(environment);
        switch (dbType) {
            case POSTGRE_SQL: return new PostgreKeyGenerator();
            case ORACLE:
            case ORACLE_12C:  return new OracleKeyGenerator();
            case H2:          return new H2KeyGenerator();
            // ...
        }
    }
}
```

**解读**：
- **第 35 行**：`before = MybatisPlusAutoConfiguration.class` 让 `@MapperScan` 先于 MP
- **第 39-44 行**：JsqlParser 全局缓存（5 秒 TTL，最大 1024 条），加速动态 SQL 解析
- **第 48-54 行**：注册分页拦截器（必须）
- **第 57-59 行**：注册字段填充处理器（自动写 createTime、creator 等）
- **第 62-82 行**：根据数据库类型选择雪花 ID 生成器

### 3.2 BaseMapperX 是 Starter 的"门面"

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/mapper/BaseMapperX.java`
**核心代码**（行 32-55）：

```java
public interface BaseMapperX<T> extends MPJBaseMapper<T> {

    default PageResult<T> selectPage(SortablePageParam pageParam, @Param("ew") Wrapper<T> queryWrapper) {
        return selectPage(pageParam, pageParam.getSortingFields(), queryWrapper);
    }

    default PageResult<T> selectPage(PageParam pageParam, @Param("ew") Wrapper<T> queryWrapper) {
        return selectPage(pageParam, null, queryWrapper);
    }

    default PageResult<T> selectPage(PageParam pageParam, Collection<SortingField> sortingFields,
                                     @Param("ew") Wrapper<T> queryWrapper) {
        // 特殊：不分页，直接查询全部
        if (PageParam.PAGE_SIZE_NONE.equals(pageParam.getPageSize())) {
            MyBatisUtils.addOrder(queryWrapper, sortingFields);
            List<T> list = selectList(queryWrapper);
            return new PageResult<>(list, (long) list.size());
        }
        // MyBatis Plus 查询
        IPage<T> mpPage = MyBatisUtils.buildPage(pageParam, sortingFields);
        selectPage(mpPage, queryWrapper);
        return new PageResult<>(mpPage.getRecords(), mpPage.getTotal());
    }
}
```

**解读**：
- `BaseMapperX<T> extends MPJBaseMapper<T>` 整合 MyBatis Plus + MyBatis Plus Join
- 所有方法用 `default` 实现，**业务方无感**
- `PageResult` 是 ruoyi 自定义的分页结果（统一 `total` + `list`）

## 4. 关键要点总结

- **yudao MyBatis Starter = MyBatis Plus + MyBatis Plus Join + 大量增强**
- **三大核心组件**：`BaseDO`（实体基类）、`BaseMapperX`（Mapper 基类）、`LambdaQueryWrapperX`（查询条件）
- **`@MapperScan` 用 `${yudao.info.base-package}`** 统一扫描
- **JsqlParser 缓存**通过 static 块在类加载时配置
- **支持多数据库**：通过 `IdTypeEnvironmentPostProcessor` 识别数据库类型

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到一个继承 `BaseMapperX` 的 Mapper，调用 `selectPage` 方法，理解完整调用链。

### 练习 2：进阶

阅读 `MyBatisUtils.buildPage` 源码，理解分页如何构建 `IPage`。

### 练习 3：挑战（选做）

在 yudao 中新加一个 `UserMapper` 自定义方法（如 `selectByIdsWithJoin`），使用 `MPJLambdaWrapperX` 关联 `dept` 表。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/mapper/BaseMapperX.java`
- MyBatis-Plus 文档：https://baomidou.com/
- MyBatis-Plus-Join 文档：https://gitee.com/best_handsome/mybatis-plus-join

---

**文档版本**：v1.0
**最后更新**：2026-07-13
