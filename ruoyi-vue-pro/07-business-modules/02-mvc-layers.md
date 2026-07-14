# 7.1.2 单模块的 MVC 分层

> 深入理解 ruoyi 单个业务模块内的 Controller / Service / DAO 三层架构。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 单模块内的 MVC 三层架构
- 理解每层职责边界（Controller 不写业务、Service 不操作 HTTP）
- 学会在三层之间传递数据（DO / VO / DTO）
- 能看懂任意 ruoyi 业务模块的完整调用链

## 📚 前置知识

- Spring Boot 基础（Controller、Service、Repository）
- MyBatis 基础
- 01-module-structure.md（推荐先看）

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
    // 4. 发送 MQ 消息
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

## 3. ruoyi 仓库源码解读

### 3.1 Controller 层：用户管理

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/user/UserController.java`

**核心代码**（行 52-58）：

```java
@PostMapping("/create")
@Operation(summary = "新增用户")
@PreAuthorize("@ss.hasPermission('system:user:create')")
public CommonResult<Long> createUser(@Valid @RequestBody UserSaveReqVO reqVO) {
    Long id = userService.createUser(reqVO);
    return success(id);
}
```

**解读**：
- 第 1 行：`@PostMapping("/create")` 定义路由
- 第 3 行：`@PreAuthorize` 鉴权，需要 `system:user:create` 权限
- 第 4 行：`@Valid` 自动校验 `UserSaveReqVO` 的字段约束
- 第 5 行：调用 Service，**不做任何业务**

### 3.2 Service 层：用户创建

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserServiceImpl.java`

**核心代码**（行 50-80）：

```java
@Override
@Transactional(rollbackFor = Exception.class)
public Long createUser(UserSaveReqVO reqVO) {
    // 1. 校验用户名唯一
    validateUserUsernameUnique(reqVO.getId(), reqVO.getUsername());
    // 2. 校验手机号唯一
    validateUserMobileUnique(reqVO.getId(), reqVO.getMobile());
    // 3. 校验部门
    deptService.validateDeptList(reqVO.getDeptIds());
    // 4. 转换 VO -> DO
    AdminUserDO user = UserConvert.INSTANCE.convert(reqVO);
    if (reqVO.getPassword() == null) {
        user.setPassword(encodePassword("123456"));  // 默认密码
    } else {
        user.setPassword(encodePassword(reqVO.getPassword()));
    }
    // 5. 插入数据库
    userMapper.insert(user);
    return user.getId();
}
```

**解读**：
- 第 2 行：`@Transactional` 开启事务，任何异常都会回滚
- 第 4-6 行：业务校验（唯一性、关联性）
- 第 10 行：调用 `UserConvert` 进行对象转换
- 第 11-15 行：业务规则（默认密码）
- 第 17 行：调用 Mapper 写入数据库
- **Service 层只关心"业务"，不关心 HTTP**

### 3.3 Mapper 层：MyBatis 操作

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/user/AdminUserMapper.java`

**核心代码**（行 1-30）：

```java
@Mapper
public interface AdminUserMapper extends BaseMapperX<AdminUserDO> {

    default AdminUserDO selectByUsername(String username) {
        return selectOne(AdminUserDO::getUsername, username);
    }

    default PageResult<AdminUserDO> selectPage(UserPageReqVO reqVO) {
        return selectPage(reqVO, this::buildQuery);
    }

    private MPJLambdaWrapper<AdminUserDO> buildQuery(UserPageReqVO reqVO) {
        return new LambdaQueryWrapperX<AdminUserDO>()
                .likeIfPresent(AdminUserDO::getUsername, reqVO.getUsername())
                .eqIfPresent(AdminUserDO::getStatus, reqVO.getStatus())
                .betweenIfPresent(AdminUserDO::getCreateTime, reqVO.getCreateTime());
    }
}
```

**解读**：
- 第 2 行：继承 `BaseMapperX`，自动获得单表 CRUD 能力
- 第 4-6 行：使用 `default` 方法实现单表查询，无需写 XML
- 第 8-10 行：分页查询
- 第 12-17 行：构建动态查询条件（`likeIfPresent` 当字段非空时拼接）
- **Mapper 层只关心"SQL 怎么写"，不关心"业务怎么算"**

## 4. 关键要点总结

- ruoyi 严格遵循 Controller / Service / Mapper 三层架构
- **Controller**：只做 HTTP 路由、参数校验、权限校验
- **Service**：业务逻辑、事务控制、跨表操作、对象转换
- **Mapper**：纯数据访问，封装 SQL
- 三层单向依赖：Controller → Service → Mapper
- 业务逻辑必须下沉到 Service，便于复用和测试

## 5. 练习题

### 练习 1：基础（必做）

打开 `UserController.java`、`AdminUserServiceImpl.java`、`AdminUserMapper.java`，跟踪 `getUserPage` 方法的完整调用链路，画出时序图。

### 练习 2：进阶

阅读 `DeptController.java` 中的 `createDept` 方法，找出对应的 Service 实现和 Mapper 调用，理解部门树形结构是如何处理的。

### 练习 3：挑战（选做）

思考：如果在 Controller 中直接调用 Mapper 而不经过 Service，会有什么坏处？列举 3 个实际场景中的问题。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/user/UserController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/user/AdminUserMapper.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
