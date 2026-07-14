# 1.2.5 MapStruct 对象映射

> 掌握 MapStruct 这一编译期对象映射工具，能优雅地替换 BeanUtils.copyProperties 这种"反射式"映射。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 MapStruct 与 BeanUtils 的本质差别（编译期 vs 运行期）
- 使用 `@Mapper` 注解编写一个 `UserConverter`
- 解决常见映射问题（字段名不一致、嵌套映射、自定义逻辑）
- 看懂 ruoyi 中的 `convert()` 方法调用方式

## 📚 前置知识

- Lombok 注解
- Maven 编译期插件
- 14-lombok.md

## 1. 核心概念

### 1.1 什么是对象映射？

在分层架构中，我们常常需要把 `DO`（数据库）转 `VO`（视图）或 `DTO`（请求）。传统方案：

```java
// Spring 的 BeanUtils - 反射方式
UserVO vo = new UserVO();
BeanUtils.copyProperties(userDO, vo);
```

缺点：
- **运行期反射**，性能差
- **没有编译期类型检查**，字段名写错不会报错
- 嵌套对象、自定义逻辑难以处理

### 1.2 MapStruct 是什么？

MapStruct 是**编译期代码生成器**，根据 `@Mapper` 注解接口在编译时自动生成实现类：

```java
@Mapper
public interface UserConverter {
    UserVO toVo(UserDO user);   // 编译期自动生成实现
}
```

编译产物相当于：

```java
public class UserConverterImpl implements UserConverter {
    public UserVO toVo(UserDO user) {
        if (user == null) return null;
        UserVO vo = new UserVO();
        vo.setId(user.getId());
        vo.setName(user.getName());
        return vo;
    }
}
```

### 1.3 MapStruct vs 反射 vs 手写

| 方案              | 性能     | 类型检查        | 可读性       | 灵活性      |
|-----------------|--------|-------------|-----------|----------|
| `BeanUtils.copy` | 中（反射）  | 弱（运行时才发现）   | 强         | 弱        |
| **MapStruct**   | 高（直接调用） | 强（编译期检查）    | 强         | 中        |
| 手写 mapper     | 最高      | 强           | 中（冗长）    | 强        |

### 1.4 常用注解

| 注解                  | 作用                          |
|---------------------|-----------------------------|
| `@Mapper`           | 标记这是一个 mapper 接口           |
| `@Mapping`          | 字段映射规则（source、target）    |
| `@Mappings`         | 多个 `@Mapping` 容器            |
| `@InheritConfiguration` | 复用上次转换的 mapping          |

## 2. 代码示例

### 2.1 定义 UserConverter

```java
// 文件：UserConverter.java
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

@Mapper
public interface UserConverter {

    UserConverter INSTANCE = Mappers.getMapper(UserConverter.class);

    // DO -> VO
    UserVO toVo(UserDO user);

    // VO List -> DO List（自动支持）
    java.util.List<UserVO> toVoList(java.util.List<UserDO> users);
}
```

```java
// 文件：UserDO.java
import lombok.Data;
@Data
public class UserDO {
    private Long id;
    private String name;
    private Integer age;
}
```

```java
// 文件：UserVO.java
import lombok.Data;
@Data
public class UserVO {
    private Long id;
    private String displayName;   // 名字不一致！
    private Integer age;
}
```

```java
// 文件：UserConverterWithMapping.java
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.factory.Mappers;

@Mapper
public interface UserConverterWithMapping {
    UserConverterWithMapping INSTANCE = Mappers.getMapper(UserConverterWithMapping.class);

    @Mapping(source = "name", target = "displayName")   // name -> displayName
    UserVO toVo(UserDO user);
}
```

```java
// 文件：MainApp.java
public class MainApp {
    public static void main(String[] args) {
        UserDO user = new UserDO();
        user.setId(1L);
        user.setName("Tom");
        user.setAge(25);

        UserVO vo = UserConverter.INSTANCE.toVo(user);
        System.out.println(vo);  // UserVO(id=1, displayName=Tom, age=25)
    }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 MapStruct 与 Lombok 的兼容性配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/pom.xml`
**核心代码**（行 95-100）：

```xml
<path>
    <!-- 确保 Lombok 生成的 getter/setter 方法能被 MapStruct 正确识别，
         避免出现 No property named “xxx" exists 的编译错误 -->
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok-mapstruct-binding</artifactId>
    <version>0.2.0</version>
</path>
```

**解读**：
- 第 2 行：注释说明这个依赖是专门解决"MapStruct 找不到 Lombok 生成的方法"问题的
- 没有 `lombok-mapstruct-binding`，编译时会报：
  ```
  No property named "id" exists in UserDO
  ```
- 这是 Lombok + MapStruct 共用的"必备三件套"之一（另外两个是 Lombok 本体与 spring-boot-configuration-processor）

### 3.2 ruoyi 中 MapStruct 实战

**ruoyi 中无独立 converter 文件的直接示例**（Mapper 写法分散在各 module-service 中）：
- yudao-module-system 业务层用 `convert(...)` 方法直接转换
- 通常这种写法：
  ```java
  AdminUserDO user = ...;
  AdminUserVO vo = BeanMapper.INSTANCE.toVo(user);   // 一行完成
  ```
- **设计思路**：避免在 controller/service 层散落 `BeanUtils.copyProperties`，统一走 MapStruct 生成的接口方法

## 4. 关键要点总结

- MapStruct 在编译期生成映射代码，比 BeanUtils 快很多
- `@Mapper` 标注接口，编译期生成 impl 类
- 配合 `lombok-mapstruct-binding` 才能与 Lombok 一起工作
- ruoyi 的三个关键注解处理器：spring-boot-configuration-processor + Lombok + lombok-mapstruct-binding

## 5. 练习题

### 练习 1：基础（必做）

手写 `OrderConverter`（`OrderDO` 包含 `userId`、`OrderVO` 包含 `userName`），把 `userId` 映射到 `userName`（假设有一个 `userService.getName(id)`）。

### 练习 2：进阶

阅读 `pom.xml` 第 95-100 行，解释为什么 `lombok-mapstruct-binding` 必须放在 `<annotationProcessorPaths>` 而不是 `<dependencies>`。

### 练习 3：挑战（选做）

实现一个"嵌套映射"：`OrderDO` 里嵌套了 `UserDO`，如何用 MapStruct 同时映射两层？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/pom.xml`
- MapStruct 官方文档：https://mapstruct.org/
- Baeldung 教程：https://www.baeldung.com/mapstruct

---

**文档版本**：v1.0
**最后更新**：2026-07-13
