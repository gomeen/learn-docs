# 7.4.4 签到

> 理解 ruoyi 会员签到（Sign-In）功能的设计与实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 签到功能的设计
- 理解连续签到的累计奖励机制
- 学会签到防重（每日仅一次）
- 能扩展自定义签到规则

## 📚 前置知识

- 23-points.md（积分联动）
- Redis 基础

## 1. 核心概念

### 1.1 签到模型

```
[用户] → [签到动作] → [签到记录] → [积分奖励]
                      (sign_in_record)  (联动积分)
```

**特点**：
- **每日仅一次**（按日期去重）
- **连续签到**：连续 N 天有额外奖励
- **断签重置**：连续天数归零

### 1.2 签到记录

```sql
CREATE TABLE member_sign_in_record (
    id BIGINT PRIMARY KEY,
    user_id BIGINT,
    sign_date DATE,           -- 签到日期
    continuous_day INT,       -- 连续签到天数
    point INT,                -- 获得积分
    create_time DATETIME,
    UNIQUE KEY uk_user_date (user_id, sign_date)  -- 一天一次
);
```

### 1.3 签到奖励规则

| 连续天数 | 奖励积分 |
|----------|----------|
| 1 天 | 10 |
| 7 天连续 | 50（额外） |
| 30 天连续 | 200（额外） |

## 2. 代码示例

### 2.1 签到接口

```java
@PostMapping("/sign-in")
@Operation(summary = "会员签到")
public CommonResult<MemberSignInRespVO> signIn() {
    Long userId = SecurityFrameworkUtils.getLoginUserId();
    return success(signInService.signIn(userId));
}
```

### 2.2 签到核心逻辑

```java
@Override
@Transactional(rollbackFor = Exception.class)
public MemberSignInRespVO signIn(Long userId) {
    LocalDate today = LocalDate.now();
    // 1. 校验今日是否已签到
    if (signInRecordMapper.existsByUserIdAndDate(userId, today)) {
        throw exception(SIGN_IN_REPEAT);
    }
    // 2. 计算连续天数
    Integer continuousDay = calculateContinuousDay(userId, today);
    // 3. 计算奖励积分
    Integer point = calculatePoint(continuousDay);
    // 4. 写入签到记录
    SignInRecordDO record = new SignInRecordDO();
    record.setUserId(userId);
    record.setSignDate(today);
    record.setContinuousDay(continuousDay);
    record.setPoint(point);
    signInRecordMapper.insert(record);
    // 5. 增加积分
    pointService.updatePoint(userId, point, PointBizTypeEnum.SIGN_IN, today.toString());
    // 6. 返回结果
    return new MemberSignInRespVO(continuousDay, point);
}
```

### 2.3 连续天数计算

```java
private Integer calculateContinuousDay(Long userId, LocalDate today) {
    // 查询最近一次签到记录
    SignInRecordDO lastRecord = signInRecordMapper.selectLastByUserId(userId);
    if (lastRecord == null) {
        return 1;  // 首次签到
    }
    // 如果昨天签到过 +1，否则从 1 开始
    if (lastRecord.getSignDate().equals(today.minusDays(1))) {
        return lastRecord.getContinuousDay() + 1;
    }
    return 1;
}
```

## 3. ruoyi 仓库源码解读

### 3.1 SignInController

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-member/src/main/java/cn/iocoder/yudao/module/member/controller/app/signin/`

**核心代码**（简化）：

```java
@Tag(name = "用户 APP - 签到")
@RestController
@RequestMapping("/member/sign-in")
@Validated
public class AppMemberSignInController {

    @Resource
    private SignInService signInService;

    @PostMapping("/sign-in")
    @Operation(summary = "会员签到")
    public CommonResult<MemberSignInRespVO> signIn() {
        return success(signInService.signIn(SecurityFrameworkUtils.getLoginUserId()));
    }

    @GetMapping("/get")
    @Operation(summary = "获得签到信息")
    public CommonResult<MemberSignInInfoRespVO> getSignInInfo() {
        return success(signInService.getSignInInfo(SecurityFrameworkUtils.getLoginUserId()));
    }
}
```

### 3.2 签到信息

```java
public class MemberSignInInfoRespVO {
    private Integer totalDay;        // 累计签到
    private Integer continuousDay;   // 当前连续
    private Boolean todaySigned;     // 今日是否签到
    private List<Integer> weekPoints; // 本周每日奖励
}
```

## 4. 关键要点总结

- 签到每日一次，通过 `(user_id, sign_date)` 唯一索引防重
- 连续签到天数通过比较 `sign_date` 计算
- 断签后连续天数归零
- 签到奖励通过积分系统实现
- 签到记录是不可变的（append-only）

## 5. 练习题

### 练习 1：基础（必做）

打开 `SignInRecordDO.java`，列出所有字段。

### 练习 2：进阶

阅读 `SignInServiceImpl.java`，理解 `calculatePoint` 的奖励规则。

### 练习 3：挑战（选做）

设计"签到补卡"功能（花 50 积分补昨天的签到），列出实现步骤。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-member/src/main/java/cn/iocoder/yudao/module/member/controller/app/signin/AppMemberSignInController.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
