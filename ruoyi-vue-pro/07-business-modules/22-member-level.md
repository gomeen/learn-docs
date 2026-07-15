# 7.4.2 会员等级

> 理解 ruoyi 会员等级（Level）系统的设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 会员等级的设计
- 理解等级升级规则（基于经验值/消费金额）
- 学会会员等级享受的折扣配置
- 能扩展会员等级业务

## 📚 前置知识

- 会员认证（详见 [会员注册/登录](./21-member-auth.md)）
- 积分体系（详见 [积分](./23-points.md)）

## 1. 核心概念

### 1.1 会员等级模型

```
[普通会员] → [白银] → [黄金] → [铂金] → [钻石]
   0        1000     5000     20000    50000
            经验值    经验值    经验值    经验值
```

**核心字段**：

```java
public class MemberLevelDO {
    private Long id;
    private String name;        // 等级名称
    private Integer level;      // 等级值
    private Integer experience; // 升级经验值
    private BigDecimal discount; // 享受折扣（0-100）
    private String icon;        // 等级图标
    private Integer status;
}
```

### 1.2 升级规则

- **消费 1 元 = 1 经验值**
- **消费 100 元 = 1 积分**
- 经验值达到阈值自动升级

## 2. 代码示例

### 2.1 会员等级管理（管理后台）

```java
@PostMapping("/create")
@PreAuthorize("@ss.hasPermission('member:level:create')")
public CommonResult<Long> createLevel(@Valid @RequestBody MemberLevelSaveReqVO createReqVO) {
    return success(levelService.createLevel(createReqVO));
}

@GetMapping("/list")
@Operation(summary = "获得会员等级列表")
public CommonResult<List<MemberLevelRespVO>> getLevelList() {
    List<MemberLevelDO> list = levelService.getLevelList();
    return success(BeanUtils.toBean(list, MemberLevelRespVO.class));
}
```

### 2.2 用户当前等级查询

```java
@GetMapping("/get")
@Operation(summary = "获得当前会员等级")
public CommonResult<MemberLevelRespVO> getMyLevel() {
    Long userId = getLoginUserId();
    MemberLevelDO level = levelService.getLevelByUserId(userId);
    return success(BeanUtils.toBean(level, MemberLevelRespVO.class));
}
```

### 2.3 升级触发逻辑

```java
// 订单完成时触发
public void onOrderPaid(Long userId, BigDecimal amount) {
    // 1. 增加经验值
    experienceService.add(userId, amount.intValue());
    // 2. 检查升级
    Integer newLevel = levelService.checkUpgrade(userId);
    // 3. 升级消息
    if (newLevel != null) {
        notifyMessageService.sendMessage(NotifyTemplateEnum.LEVEL_UP, userId, ...);
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 MemberLevelController 核心代码

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-member/src/main/java/cn/iocoder/yudao/module/member/controller/admin/level/MemberLevelController.java`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 会员等级")
@RestController
@RequestMapping("/member/level")
@Validated
public class MemberLevelController {

    @Resource
    private MemberLevelService levelService;

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('member:level:create')")
    public CommonResult<Long> createLevel(@Valid @RequestBody MemberLevelSaveReqVO createReqVO) {
        return success(levelService.createLevel(createReqVO));
    }

    @PutMapping("/update")
    @PreAuthorize("@ss.hasPermission('member:level:update')")
    public CommonResult<Boolean> updateLevel(@Valid @RequestBody MemberLevelSaveReqVO updateReqVO) {
        levelService.updateLevel(updateReqVO);
        return success(true);
    }

    @DeleteMapping("/delete")
    @PreAuthorize("@ss.hasPermission('member:level:delete')")
    public CommonResult<Boolean> deleteLevel(@RequestParam("id") Long id) {
        levelService.deleteLevel(id);
        return success(true);
    }

    @GetMapping("/list")
    public CommonResult<List<MemberLevelRespVO>> getLevelList() {
        return success(BeanUtils.toBean(levelService.getLevelList(), MemberLevelRespVO.class));
    }
}
```

### 3.2 等级升级检查

```java
public Integer checkLevelUpgrade(Long userId) {
    // 1. 获取当前用户经验值
    Integer exp = experienceService.get(userId);
    // 2. 找到最高可升级到的等级
    List<MemberLevelDO> levels = getLevelList();
    Integer currentLevel = getCurrentLevel(userId);
    for (MemberLevelDO level : levels) {
        if (level.getExperience() <= exp && level.getLevel() > currentLevel) {
            // 3. 更新用户等级
            userMapper.updateLevel(userId, level.getLevel());
            return level.getLevel();
        }
    }
    return null;
}
```

## 4. 关键要点总结

- 会员等级通过经验值触发升级
- 等级享受商品折扣
- 升级后通过站内信通知
- 等级列表是全局共享（无租户）
- 经验值通过订单支付时累加

## 5. 练习题

### 练习 1：基础（必做）

打开 `MemberLevelDO.java`，列出所有字段。

### 练习 2：进阶

阅读 `MemberExperienceServiceImpl.java`，理解经验值的累加逻辑。

### 练习 3：挑战（选做）

设计"等级降级"功能（如一年无消费降一级），说明触发时机和实现方案。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-member/src/main/java/cn/iocoder/yudao/module/member/controller/admin/level/MemberLevelController.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
