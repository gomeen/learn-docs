# 02 MySQL 事务与隔离级别

> 事务是数据库的根基，ruoyi 中大量使用 `@Transactional` 保证业务一致性。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ACID 四大特性
- 区分四种隔离级别（READ UNCOMMITTED → SERIALIZABLE）
- 知道脏读、不可重复读、幻读的差异
- 掌握 Spring `@Transactional` 的传播行为和回滚规则

## 📚 前置知识

- [01-mysql-basics.md](./01-mysql-basics.md)
- Spring AOP 基础概念（详见 [03-aop](../02-spring-boot/03-aop.md)）
- Spring 事务声明式管理见 [04-transaction](../02-spring-boot/04-transaction.md)

## 1. 核心概念

### 1.1 ACID 特性

| 特性 | 含义 | 实现机制 |
|------|------|---------|
| Atomicity（原子性） | 事务要么全成功要么全失败 | undo log |
| Consistency（一致性） | 事务前后数据完整性约束成立 | 应用层 + 数据库约束 |
| Isolation（隔离性） | 并发事务互不干扰 | MVCC + 锁 |
| Durability（持久性） | 事务提交后数据永久保存 | redo log |

### 1.2 四种隔离级别

```
READ UNCOMMITTED < READ COMMITTED < REPEATABLE READ < SERIALIZABLE
   隔离性弱          ↑               ↑ MySQL 默认             隔离性强
   并发高                                                并发低
```

| 隔离级别 | 脏读 | 不可重复读 | 幻读 |
|---------|------|----------|------|
| READ UNCOMMITTED | 可能 | 可能 | 可能 |
| READ COMMITTED | 避免 | 可能 | 可能 |
| REPEATABLE READ（MySQL 默认） | 避免 | 避免 | 部分避免 |
| SERIALIZABLE | 避免 | 避免 | 避免 |

### 1.3 三个并发问题

- **脏读**：读到其他事务**未提交**的数据
- **不可重复读**：同一行内，同一查询两次结果不同（其他事务修改了数据）
- **幻读**：范围查询两次返回的行数不同（其他事务插入/删除了行）

## 2. 代码示例

### 2.1 事务的基本使用

```sql
-- MySQL 显式事务
START TRANSACTION;

UPDATE system_role SET status = 1 WHERE id = 1;
UPDATE system_user SET status = 1 WHERE id = 100;

-- 任意一条 SQL 失败都应该 ROLLBACK
COMMIT;  -- 或 ROLLBACK;
```

### 2.2 Spring `@Transactional` 注解

> 📌 **Sighting**：传播行为、失效场景、自调用完整讲解见 [04-transaction](../02-spring-boot/04-transaction.md)。此处配合 MySQL 隔离级别理解。

```java
@Service
public class RoleServiceImpl implements RoleService {

    @Override
    @Transactional(rollbackFor = Exception.class)  // 关键：指定回滚异常类型
    public Long createRole(RoleSaveReqVO createReqVO, Integer type) {
        // 1. 校验角色名重复
        validateRoleDuplicate(createReqVO.getName(), createReqVO.getCode(), null);

        // 2. 插入到数据库
        RoleDO role = BeanUtils.toBean(createReqVO, RoleDO.class)
                .setType(ObjectUtil.defaultIfNull(type, RoleTypeEnum.CUSTOM.getType()))
                .setStatus(ObjUtil.defaultIfNull(createReqVO.getStatus(),
                                                 CommonStatusEnum.ENABLE.getStatus()))
                .setDataScope(DataScopeEnum.ALL.getScope());
        roleMapper.insert(role);

        // 3. 记录操作日志上下文（事务提交后异步写日志）
        LogRecordContext.putVariable("role", role);
        return role.getId();
    }
}
```

**说明**：
- `rollbackFor = Exception.class`：捕获所有 Exception（包括 RuntimeException）都触发回滚
- 默认情况下 Spring 只回滚 RuntimeException，不回滚普通 Exception，因此**显式声明 rollbackFor 是最佳实践**
- 事务方法必须是 public，且必须通过 Spring 代理调用（同类内部调用会失效）

## 3. 关键要点总结

- MySQL 默认隔离级别是 **REPEATABLE READ**
- Spring 中**永远显式声明** `rollbackFor = Exception.class`，避免 Checked Exception 不回滚
- `@Transactional` 必须通过代理对象调用才生效（避免同类内部调用）
- 多数据源场景使用 `@DSTransactional` 代替 `@Transactional`（详见 [20-ds-annotation](./24-ds-annotation.md)）
- ruoyi 中事务 + 缓存清理经常组合使用：事务回滚时缓存也要避免脏读

---

**文档版本**：v1.0
**最后更新**：2026-07-13
