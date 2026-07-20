# 1.2.5 MapStruct 对象映射

> 掌握 MapStruct 这一编译期对象映射工具，能优雅地替换 BeanUtils.copyProperties 这种"反射式"映射。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 MapStruct 与 BeanUtils 的本质差别（编译期 vs 运行期）
- 使用 `@Mapper` 注解编写一个 `UserConverter`
- 解决常见映射问题（字段名不一致、嵌套映射、自定义逻辑）
- 看懂 ruoyi 中的 `convert()` 方法调用方式

## 📚 前置知识

- Lombok 注解（详见 [14-lombok](./17-lombok.md)）
- Maven 编译期插件
- 17-lombok.md

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

## 3. 关键要点总结

- MapStruct 在编译期生成映射代码，比 BeanUtils 快很多
- `@Mapper` 标注接口，编译期生成 impl 类
- 配合 `lombok-mapstruct-binding` 才能与 Lombok 一起工作
- ruoyi 的三个关键注解处理器：spring-boot-configuration-processor + Lombok + lombok-mapstruct-binding

---

**文档版本**：v1.0
**最后更新**：2026-07-13
