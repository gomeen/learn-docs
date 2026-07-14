# 11 IService 与 ServiceImpl

> IService 是 MyBatis Plus 的 Service 层抽象。ruoyi 自定义 `ServiceImplX`，强化业务能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 IService 与 BaseMapper 的职责差异
- 掌握 ServiceImpl 的常见写法
- 知道 ruoyi 的 ServiceImplX 做了什么增强
- 能正确区分 Controller / Service / Mapper 三层职责

## 📚 前置知识

- 09-mybatis-vs-mp.md
- 10-base-mapper.md
- Spring 依赖注入

## 1. 核心概念

### 1.1 为什么需要 Service 层？

```
BaseMapper：数据库原子操作（CRUD）
Service   ：业务逻辑（事务控制、跨表操作、缓存、权限）
Controller：HTTP 接口
```

### 1.2 IService 接口能力

```java
public interface IService<T> {
    boolean save(T entity);                          // 插入
    boolean removeById(Serializable id);             // 删除
    boolean updateById(T entity);                    // 更新
    T getById(Serializable id);                      // 查询
    List<T> listByIds(Collection<? extends Serializable> idList);
    long count();
    // ...
}
```

### 1.3 ruoyi 的 ServiceImplX 增强

ruoyi 的 `ServiceImplX<M, T>` 继承自 MP 的 `ServiceImpl`，**没有覆盖任何方法**，仅作为未来扩展点存在。ruoyi 实际更常用的 Service 写法是：

```java
public interface RoleService {  // ruoyi 习惯：自定义接口
    Long createRole(RoleSaveReqVO reqVO, Integer type);
    void updateRole(RoleSaveReqVO reqVO);
    PageResult<RoleDO> getRolePage(RolePageReqVO reqVO);
}

@Service
public class RoleServiceImpl implements RoleService {  // 手写实现，不继承 ServiceImplX
    @Resource
    private RoleMapper roleMapper;
    // 业务方法
}
```

## 2. 代码示例

### 2.1 MP 默认 Service 写法

```java
// Service 接口
public interface UserService extends IService<User> {}

// Service 实现（继承 MP 的 ServiceImpl）
@Service
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {
    // 自动拥有 save/removeById/updateById/getById 等方法
}

// 使用
userService.save(user);
userService.getById(1L);
```

### 2.2 ruoyi 推荐写法

```java
// Service 接口（业务方法，无 IService 痕迹）
public interface RoleService {
    Long createRole(RoleSaveReqVO reqVO, Integer type);
    void updateRole(RoleSaveReqVO reqVO);
}

// Service 实现
@Service
@Slf4j
public class RoleServiceImpl implements RoleService {
    @Resource
    private RoleMapper roleMapper;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long createRole(RoleSaveReqVO reqVO, Integer type) {
        validateRoleDuplicate(reqVO.getName(), reqVO.getCode(), null);
        RoleDO role = BeanUtils.toBean(reqVO, RoleDO.class)
                .setType(ObjectUtil.defaultIfNull(type, RoleTypeEnum.CUSTOM.getType()));
        roleMapper.insert(role);
        return role.getId();
    }
}
```

### 2.3 对比：MP 风格 vs ruoyi 风格

```java
// MP 风格：自动拥有所有 CRUD
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {
    public void createUser(User user) {
        save(user);  // 直接用父类方法
    }
}

// ruoyi 风格：手动注入 Mapper，更灵活
public class UserServiceImpl implements UserService {
    @Resource
    private UserMapper userMapper;

    public void createUser(User user) {
        userMapper.insert(user);  // 显式调用
    }
}
```

**为什么 ruoyi 不直接继承 ServiceImpl？**
1. **接口纯净**：Service 接口只暴露业务方法，不暴露通用 CRUD（避免 Controller 滥用）
2. **依赖明确**：显式 `@Resource` 让依赖关系清晰
3. **定制灵活**：需要时可注入多个 Mapper

## 3. ruoyi 仓库源码解读

### 3.1 RoleServiceImpl：典型 ruoyi Service 实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/RoleServiceImpl.java`
**核心代码**（行 44-72）：

```java
@Service
@Slf4j
public class RoleServiceImpl implements RoleService {

    @Resource
    private PermissionService permissionService;

    @Resource
    private RoleMapper roleMapper;

    @Override
    @Transactional(rollbackFor = Exception.class)
    @LogRecord(type = SYSTEM_ROLE_TYPE, subType = SYSTEM_ROLE_CREATE_SUB_TYPE, bizNo = "{{#role.id}}",
            success = SYSTEM_ROLE_CREATE_SUCCESS)
    public Long createRole(RoleSaveReqVO createReqVO, Integer type) {
        // 1. 校验角色
        validateRoleDuplicate(createReqVO.getName(), createReqVO.getCode(), null);

        // 2. 插入到数据库
        RoleDO role = BeanUtils.toBean(createReqVO, RoleDO.class)
                .setType(ObjectUtil.defaultIfNull(type, RoleTypeEnum.CUSTOM.getType()))
                .setStatus(ObjUtil.defaultIfNull(createReqVO.getStatus(), CommonStatusEnum.ENABLE.getStatus()))
                .setDataScope(DataScopeEnum.ALL.getScope());
        roleMapper.insert(role);

        // 3. 记录操作日志上下文
        LogRecordContext.putVariable("role", role);
        return role.getId();
    }
}
```

**解读**：
- 第 1-2 行：`@Service + @Slf4j`（Lombok 提供日志对象）
- 第 5-6 行：显式注入 `PermissionService`（跨 Service 协作）和 `RoleMapper`（DAO）
- 第 12 行：`@Transactional(rollbackFor = Exception.class)` —— 事务声明（即使只有一条 insert，也保持一致性）
- 第 13-14 行：`@LogRecord` —— 来自 `mzt-log` 库，操作日志注解（用于审计）
- 第 17 行：业务校验（角色名/编码重复）
- 第 20 行：`BeanUtils.toBean(reqVO, RoleDO.class)` —— hutool 的 Bean 拷贝工具
- 第 21-23 行：`setXxx` 链式调用 + `ObjectUtil.defaultIfNull` 给默认值
- 第 24 行：`roleMapper.insert(role)` —— 调用 MP 内置 insert，自动填充 `creator/create_time/updater/update_time`（由 `DefaultDBFieldHandler` 完成）
- **设计意图**：业务方法聚焦业务逻辑（校验、转换），DAO 调用透明、事务安全、操作可审计

### 3.2 AdminUserServiceImpl 复杂业务示例

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserServiceImpl.java`

```java
// Service 中注入多个 Mapper / Service 是常见模式
@Service
@Slf4j
public class AdminUserServiceImpl implements AdminUserService {

    @Resource
    private AdminUserMapper userMapper;

    @Resource
    private DeptService deptService;       // 部门 Service

    @Resource
    private RoleService roleService;       // 角色 Service

    @Override
    public AdminUserDO getUser(Long id) {
        AdminUserDO user = userMapper.selectById(id);
        if (user == null) return null;
        // 延迟加载：按需查询关联数据
        if (user.getDeptId() != null) {
            user.setDept(deptService.getDept(user.getDeptId()));
        }
        return user;
    }
}
```

**解读**：
- **跨 Service 协作**：用户信息需要部门、角色信息
- **延迟加载**：先查主表，按需查关联（避免 N+1 查询）
- **最佳实践**：当关联数据 < 5 个时，可考虑直接 join；当 > 5 个时，分开查询更灵活

## 4. 关键要点总结

- MP 提供 `IService` 抽象（CRUD 通用方法）
- ruoyi 倾向自定义 Service 接口 + 手动注入 Mapper（更灵活）
- Service 层职责：业务逻辑、事务、缓存、权限校验、跨表操作
- 复杂业务应拆分为多个 Service 方法，而非全部塞进 Controller
- 注入多个 Mapper/Service 是常见模式（依赖明确）

## 5. 练习题

### 练习 1：基础（必做）

阅读 `RoleServiceImpl.java`，列出所有业务方法（createRole/updateRole/deleteRole/...），画出每个方法的依赖图（注入哪些 Service / Mapper）。

### 练习 2：进阶

为 `OrderService` 写一个 `createOrder(OrderCreateReqVO reqVO)`：
1. 校验商品存在 + 库存充足
2. 扣减库存
3. 创建订单
4. 记录操作日志
要求：事务、跨表、日志都覆盖。

### 练习 3：挑战（选做）

对比 ruoyi 风格 vs MP 默认 Service 风格（继承 `ServiceImpl`），列出至少 3 个 ruoyi 选择自定义的原因，结合真实业务场景（如：不允许 Controller 直接调用 `removeById`）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/RoleServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserServiceImpl.java`
- MyBatis Plus IService 文档：https://baomidou.com/pages/49cc81/

---

**文档版本**：v1.0
**最后更新**：2026-07-13