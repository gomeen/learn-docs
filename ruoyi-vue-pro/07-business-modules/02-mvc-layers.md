# 7.1.2 单模块的 MVC 分层

> 深入理解 ruoyi 单个业务模块内的 Controller / Service / DAO 三层架构。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 单模块内的 MVC 三层架构
- 理解每层职责边界（Controller 不写业务、Service 不操作 HTTP）
- 学会在三层之间传递数据（DO / VO / DTO）
- 能看懂任意 ruoyi 业务模块的完整调用链

## 📚 前置知识

- Spring Boot Web（详见 [Controller](../02-spring-boot/15-controller.md)、[参数绑定](../02-spring-boot/17-param-binding.md)）
- 事务（详见 [事务](../02-spring-boot/04-transaction.md)）
- MyBatis 基础（详见 [MyBatis Starter](../03-spring-boot-starters/07-mybatis-starter.md)）
- 模块划分（详见 [模块结构](./01-module-structure.md)）

## 1. 核心概念

### 1.1 ruoyi 的 MVC 三层架构

```
HTTP Request
    ↓
[Controller 层]  ← 接收请求、参数校验、调用 Service
    ↓
[Service 层]     ← 业务逻辑、事务控制、跨表操作
    ↓
[DAL/DAO 层]     ← 数据访问（MyBatis Mapper）
    ↓
MySQL Database
```

| 层级 | 包路径 | 职责 | 命名规范 |
|------|--------|------|----------|
| Controller | `controller/admin/xxx/` | HTTP 接口、参数校验 | `XxxController.java` |
| Service | `service/xxx/` | 业务逻辑、事务 | `XxxService.java` + `Impl/` |
| DAO | `dal/mysql/xxx/` | 数据访问 | `XxxMapper.java` + `XxxMapper.xml` |

### 1.2 为什么需要分层？

**没有分层的痛苦**：
```java
// ❌ 所有逻辑堆在一个方法里
@PostMapping("/create")
public void createUser(UserDTO dto) {
    // 1. 校验参数
    if (dto.getName() == null) throw ...;
    // 2. 业务逻辑（计算密码、关联角色）
    String pwd = encrypt(dto.getPassword());
    // 3. 写数据库（拼接 SQL）
    jdbc.update("INSERT INTO ...");
    // 4. 发送 MQ 消息（详见 [MQ 概念](../../_common/02-mq/01-concepts.md)）
    rabbitTemplate.send(...);
}
```

**分层后**：
```java
// Controller 只做参数校验和路由
@PostMapping("/create")
public CommonResult<Long> createUser(@Valid @RequestBody UserSaveReqVO reqVO) {
    return success(userService.createUser(reqVO));
}

// Service 负责业务逻辑
@Service
public class AdminUserServiceImpl implements AdminUserService {
    public Long createUser(UserSaveReqVO reqVO) {
        // 1. 业务校验
        // 2. 转换 DTO -> DO
        // 3. 调用 Mapper
        // 4. 处理后续逻辑（发 MQ、记日志）
    }
}
```

**好处**：
- Controller 可复用：未来加 GraphQL/RPC 接口，Service 不变
- Service 可测试：脱离 Spring MVC，单元测试更简单
- 业务集中：所有"用户创建"逻辑都在 Service 里，新人快速理解

### 1.3 三层的依赖方向

**严格单向依赖**：
```
Controller → Service → Mapper → Database
     ↑          ↑        ↑
     |          |        |
   只依赖    只依赖    只依赖
  Service   Mapper   MyBatis
```

**禁止反向调用**：
- Mapper 不能调用 Service
- Service 不能调用 Controller
- 避免循环依赖

## 2. 代码示例

### 2.1 完整的三层调用示例（用户创建）

```java
// ===== 1. Controller 层 =====
@PostMapping("/create")
@PreAuthorize("@ss.hasPermission('system:user:create')")
public CommonResult<Long> createUser(@Valid @RequestBody UserSaveReqVO reqVO) {
    Long id = userService.createUser(reqVO);
    return success(id);
}

// ===== 2. Service 层 =====
@Service
@Validated
public class AdminUserServiceImpl implements AdminUserService {

    @Resource
    private AdminUserMapper userMapper;

    @Resource
    private DeptService deptService;

    @Transactional(rollbackFor = Exception.class)
    @Override
    public Long createUser(UserSaveReqVO reqVO) {
        // 1. 校验部门
        deptService.validateDeptList(reqVO.getDeptIds());
        // 2. 转换 VO -> DO
        AdminUserDO user = UserConvert.INSTANCE.convert(reqVO);
        user.setPassword(encodePassword(reqVO.getPassword()));
        // 3. 插入数据库
        userMapper.insert(user);
        return user.getId();
    }
}

// ===== 3. Mapper 层 =====
@Mapper
public interface AdminUserMapper extends BaseMapperX<AdminUserDO> {
    default PageResult<AdminUserDO> selectPage(UserPageReqVO reqVO) {
        return selectPage(reqVO, this::buildQuery);
    }

    private MPJLambdaWrapper<AdminUserDO> buildQuery(UserPageReqVO reqVO) {
        return new LambdaQueryWrapperX<AdminUserDO>()
                .likeIfPresent(AdminUserDO::getUsername, reqVO.getUsername())
                .eqIfPresent(AdminUserDO::getStatus, reqVO.getStatus());
    }
}
```

### 2.2 错误示范：业务逻辑写在 Controller

```java
// ❌ 错误：Controller 写业务
@PostMapping("/create")
public CommonResult<Long> createUser(@RequestBody UserDTO dto) {
    // 业务校验放在 Controller
    if (dto.getAge() < 18) {
        return CommonResult.error(400, "年龄不能小于18");
    }
    // 加密密码放在 Controller
    String pwd = BCrypt.hashpw(dto.getPassword(), BCrypt.gensalt());
    // 直接调用 Mapper
    userMapper.insert(new User(dto.getName(), pwd));
    return success();
}
```

**问题**：
1. 业务散落在多个 Controller
2. 加密逻辑无法在 RPC 接口中复用
3. 单元测试必须启动 Spring MVC

```java
// ✅ 正确：业务下沉到 Service
@PostMapping("/create")
public CommonResult<Long> createUser(@Valid @RequestBody UserSaveReqVO reqVO) {
    return success(userService.createUser(reqVO));  // 业务都在 Service
}
```

## 3. 关键要点总结

- ruoyi 严格遵循 Controller / Service / Mapper 三层架构
- **Controller**：只做 HTTP 路由、参数校验、权限校验
- **Service**：业务逻辑、事务控制、跨表操作、对象转换
- **Mapper**：纯数据访问，封装 SQL
- 三层单向依赖：Controller → Service → Mapper
- 业务逻辑必须下沉到 Service，便于复用和测试

---

**文档版本**：v1.0
**最后更新**：2026-07-13
