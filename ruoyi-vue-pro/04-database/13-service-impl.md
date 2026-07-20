# 11 IService 与 ServiceImpl

> IService 是 MyBatis Plus 的 Service 层抽象。ruoyi 自定义 `ServiceImplX`，强化业务能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 IService 与 BaseMapper 的职责差异
- 掌握 ServiceImpl 的常见写法
- 知道 ruoyi 的 ServiceImplX 做了什么增强
- 能正确区分 Controller / Service / Mapper 三层职责

## 📚 前置知识

- [11-mybatis-vs-mp.md](./11-mybatis-vs-mp.md)
- [12-base-mapper.md](./12-base-mapper.md)
- Spring 依赖注入（详见 [01-ioc](../02-spring-boot/01-ioc.md)）
- 事务见 [04-transaction](../02-spring-boot/04-transaction.md)

## 1. 核心概念

### 1.1 为什么需要 Service 层？

```
BaseMapper：数据库原子操作（CRUD）
Service   ：业务逻辑（事务控制、跨表操作、缓存、权限）
Controller：HTTP 接口
```

> 📌 **Sighting**：事务声明见 [04-transaction](../02-spring-boot/04-transaction.md)；缓存见 [24-cache](../02-spring-boot/28-cache.md)；权限见 [RBAC](../../_common/08-authorization/01-rbac.md)。

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

## 3. 关键要点总结

- MP 提供 `IService` 抽象（CRUD 通用方法）
- ruoyi 倾向自定义 Service 接口 + 手动注入 Mapper（更灵活）
- Service 层职责：业务逻辑、事务、缓存、权限校验、跨表操作
- 复杂业务应拆分为多个 Service 方法，而非全部塞进 Controller
- 注入多个 Mapper/Service 是常见模式（依赖明确）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
