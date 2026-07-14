# 7.5.7 分销

> 理解 ruoyi 的分销（Distribution）系统设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 分销模式的设计
- 理解多级分销关系链
- 学会佣金计算和结算
- 能扩展分销业务

## 📚 前置知识

- 29-order.md（订单）
- 21-member-auth.md（会员）

## 1. 核心概念

### 1.1 分销模型

```
[会员 A] → 推荐 [会员 B] → 推荐 [会员 C]
   ↑一级返佣          ↑一级返佣
   ↑二级返佣（来自 C 的订单）
```

**关键概念**：
- **分销关系**：上下级关系
- **佣金比例**：一级 X%、二级 Y%
- **结算规则**：订单完成后 T+1 或 T+N

### 1.2 ruoyi 分销核心表

```sql
-- 分销配置
CREATE TABLE trade_brokerage_config (
    id INT,
    level1_rate DECIMAL,    -- 一级佣金比例
    level2_rate DECIMAL,    -- 二级佣金比例
    withdraw_min DECIMAL,   -- 提现最低金额
    status TINYINT
);

-- 分销关系
CREATE TABLE trade_brokerage_user (
    id BIGINT,
    user_id BIGINT,
    bind_user_id BIGINT,    -- 上级用户
    bind_user_type INT
);

-- 佣金记录
CREATE TABLE trade_brokerage_record (
    id BIGINT,
    user_id BIGINT,         -- 受益人
    source_user_id BIGINT,  -- 触发用户
    order_id BIGINT,        -- 来源订单
    brokerage DECIMAL,      -- 佣金金额
    status INT,             -- 状态：待结算/已结算/已提现
    unfreeze_time DATETIME  -- 解冻时间
);
```

### 1.3 佣金状态

```
待结算（订单已支付） ──订单完成──> 可提现 ──提现申请──> 已提现
       │
       │ 退款
       ↓
    已取消
```

## 2. 代码示例

### 2.1 绑定上下级

```java
@PostMapping("/bind")
public CommonResult<Boolean> bindDistribution(@RequestParam Long parentUserId) {
    distributionService.bind(getLoginUserId(), parentUserId);
    return success(true);
}

@Transactional
@Override
public void bind(Long userId, Long parentUserId) {
    // 1. 校验不能绑定自己
    if (userId.equals(parentUserId)) throw exception(CANNOT_BIND_SELF);
    // 2. 校验不能绑定已有上级
    BrokerageUserDO existing = brokerageUserMapper.selectByUserId(userId);
    if (existing != null) throw exception(ALREADY_BOUND);
    // 3. 绑定
    BrokerageUserDO record = new BrokerageUserDO();
    record.setUserId(userId);
    record.setBindUserId(parentUserId);
    brokerageUserMapper.insert(record);
}
```

### 2.2 订单完成后计算佣金

```java
public void onOrderPaid(OrderDO order) {
    // 1. 查询分销关系
    BrokerageUserDO brokerageUser = brokerageUserMapper.selectByUserId(order.getUserId());
    if (brokerageUser == null) return;
    // 2. 计算佣金
    BrokerageConfigDO config = configService.getConfig();
    BigDecimal amount = order.getPayPrice();
    // 3. 一级佣金
    BigDecimal level1Amount = amount.multiply(config.getLevel1Rate());
    brokerageService.addRecord(order.getUserId(), brokerageUser.getBindUserId(),
            order.getId(), level1Amount);
    // 4. 二级佣金（如果有）
    BrokerageUserDO level2 = brokerageUserMapper.selectByUserId(brokerageUser.getBindUserId());
    if (level2 != null) {
        BigDecimal level2Amount = amount.multiply(config.getLevel2Rate());
        brokerageService.addRecord(level2.getBindUserId(), order.getUserId(),
                order.getId(), level2Amount);
    }
}
```

### 2.3 提现申请

```java
@PostMapping("/withdraw")
public CommonResult<Long> withdraw(@Valid @RequestBody WithdrawReqVO reqVO) {
    return success(withdrawService.applyWithdraw(getLoginUserId(), reqVO));
}

public Long applyWithdraw(Long userId, WithdrawReqVO reqVO) {
    // 1. 校验可提现余额
    BigDecimal balance = brokerageService.getAvailableBalance(userId);
    if (balance.compareTo(reqVO.getAmount()) < 0) {
        throw exception(BROKERAGE_NOT_ENOUGH);
    }
    // 2. 创建提现申请
    WithdrawDO withdraw = new WithdrawDO();
    withdraw.setUserId(userId);
    withdraw.setAmount(reqVO.getAmount());
    withdraw.setType(reqVO.getType());  // 微信/支付宝
    withdraw.setStatus(WithdrawStatusEnum.PENDING.getStatus());
    withdrawMapper.insert(withdraw);
    return withdraw.getId();
}
```

## 3. ruoyi 仓库源码解读

### 3.1 BrokerageController

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-trade/src/main/java/cn/iocoder/yudao/module/trade/controller/admin/brokerage/`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 分销")
@RestController
@RequestMapping("/trade/brokerage")
@Validated
public class BrokerageController {

    @Resource
    private BrokerageService brokerageService;

    @GetMapping("/config")
    @PreAuthorize("@ss.hasPermission('trade:brokerage:config')")
    public CommonResult<BrokerageConfigRespVO> getBrokerageConfig() {
        return success(brokerageService.getBrokerageConfig());
    }

    @PutMapping("/config")
    @PreAuthorize("@ss.hasPermission('trade:brokerage:config')")
    public CommonResult<Boolean> updateBrokerageConfig(@Valid @RequestBody BrokerageConfigSaveReqVO reqVO) {
        brokerageService.updateBrokerageConfig(reqVO);
        return success(true);
    }

    @GetMapping("/record/page")
    public CommonResult<PageResult<BrokerageRecordRespVO>> getBrokerageRecordPage(
            @Valid BrokerageRecordPageReqVO pageVO) {
        return success(brokerageService.getBrokerageRecordPage(pageVO));
    }
}
```

### 3.2 提现申请

```java
public class BrokerageWithdrawServiceImpl implements BrokerageWithdrawService {

    @Override
    @Transactional
    public Long applyWithdraw(Long userId, AppBrokerageWithdrawReqVO reqVO) {
        // 1. 冻结佣金记录
        int rows = brokerageRecordMapper.freezeAmount(userId, reqVO.getAmount());
        if (rows == 0) throw exception(BROKERAGE_NOT_ENOUGH);
        // 2. 创建提现申请
        BrokerageWithdrawDO withdraw = new BrokerageWithdrawDO();
        withdraw.setUserId(userId);
        withdraw.setAmount(reqVO.getAmount());
        withdraw.setStatus(WithdrawStatusEnum.AUDITING.getStatus());
        withdrawMapper.insert(withdraw);
        return withdraw.getId();
    }
}
```

## 4. 关键要点总结

- 分销是多级返佣关系链
- 通过 `brokerage_user` 表存上下级
- 佣金记录有"待结算/可提现/已提现"状态
- 提现有最低金额限制
- 提现需要审核流程

## 5. 练习题

### 练习 1：基础（必做）

阅读 `BrokerageUserDO.java` 字段。

### 练习 2：进阶

阅读 `BrokerageRecordServiceImpl.java`，理解佣金冻结和解冻的实现。

### 练习 3：挑战（选做）

设计"分销员等级"功能：根据销售额划分等级（普通/银牌/金牌），不同等级有不同佣金比例。列出实现方案。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-trade/src/main/java/cn/iocoder/yudao/module/trade/controller/admin/brokerage/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
