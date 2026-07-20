# 7.4.3 积分系统

> 理解 ruoyi 会员积分（Point）系统的设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 积分系统的设计
- 理解积分获取和消耗的流水记录
- 学会积分签到、积分商城等场景
- 能扩展自定义积分业务

## 📚 前置知识

- 会员认证 / 等级（详见 [会员认证](./24-member-auth.md)、[会员等级](./25-member-level.md)）
- Redis 基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- 事务（详见 [事务](../02-spring-boot/04-transaction.md)）

## 1. 核心概念

### 1.1 积分系统模型

```
[用户] → [积分变动] → [流水记录] → [积分总账]
         (业务触发)   (member_point_record)  (member_user.point)
```

**关键设计**：
- **总账**：用户表的 `point` 字段
- **流水**：每次变动都记录，支持追溯
- **事务**：积分变动 + 流水写入必须在同一事务

### 1.2 积分业务类型

```java
public enum PointBizTypeEnum {
    SIGN_IN(1, "签到"),
    ORDER_GIVE(2, "订单消费"),
    ADMIN_ADD(3, "管理员调整"),
    EXCHANGE(4, "积分兑换"),
    REGISTER(5, "注册赠送");
}
```

### 1.3 积分流水表

```sql
CREATE TABLE member_point_record (
    id BIGINT PRIMARY KEY,
    user_id BIGINT,
    biz_type INT,            -- 业务类型
    biz_id VARCHAR(64),      -- 业务 ID（订单号等）
    point INT,               -- 变动积分（正为获取，负为消耗）
    description VARCHAR(255), -- 描述
    create_time DATETIME
);
```

## 2. 代码示例

### 2.1 积分变动核心方法

```java
@Override
@Transactional(rollbackFor = Exception.class)
public void updatePoint(Long userId, Integer point, PointBizTypeEnum bizType, String bizId) {
    // 1. 校验积分合法性
    if (point == 0) return;
    // 2. 查询当前积分
    MemberUserDO user = userMapper.selectById(userId);
    if (user == null) throw exception(USER_NOT_EXISTS);
    // 3. 扣减时校验余额
    if (user.getPoint() + point < 0) {
        throw exception(POINT_NOT_ENOUGH);
    }
    // 4. 更新总账
    userMapper.updatePoint(userId, point);
    // 5. 写入流水
    PointRecordDO record = new PointRecordDO();
    record.setUserId(userId);
    record.setBizType(bizType.getType());
    record.setBizId(bizId);
    record.setPoint(point);
    record.setDescription(bizType.getDescription());
    pointRecordMapper.insert(record);
}
```

### 2.2 签到获取积分

```java
@Override
public void signIn(Long userId) {
    // 1. 校验今日是否已签到
    LocalDate today = LocalDate.now();
    if (signInRecordMapper.existsByUserIdAndDate(userId, today)) {
        throw exception(SIGN_IN_REPEAT);
    }
    // 2. 增加积分
    updatePoint(userId, 10, PointBizTypeEnum.SIGN_IN, today.toString());
    // 3. 记录签到
    SignInRecordDO record = new SignInRecordDO();
    record.setUserId(userId);
    record.setSignDate(today);
    signInRecordMapper.insert(record);
}
```

### 2.3 查询积分流水

```java
@GetMapping("/record/page")
public CommonResult<PageResult<PointRecordRespVO>> getPointRecordPage(@Valid PointRecordPageReqVO pageVO) {
    PageResult<PointRecordDO> pageResult = pointRecordService.getPointRecordPage(pageVO);
    return success(BeanUtils.toBean(pageResult, PointRecordRespVO.class));
}
```

## 3. 关键要点总结

- 积分系统采用"总账 + 流水"模式
- 所有变动必须写入流水（可追溯）
- 消耗积分时校验余额
- 积分业务类型通过枚举管理
- 流水表通常按月分表

---

**文档版本**：v1.0
**最后更新**：2026-07-13
