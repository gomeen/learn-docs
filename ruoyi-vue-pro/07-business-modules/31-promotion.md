# 7.5.6 营销活动：优惠券/秒杀/拼团

> 理解 ruoyi 的营销活动（Promotion）模块。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 营销活动的设计
- 理解优惠券、秒杀、拼团、满减、积分商城
- 学会优惠金额的计算
- 能扩展自定义营销活动

## 📚 前置知识

- Redis 库存预扣（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)、[分布式锁](../../_common/04-distributed-locks/02-redis-redlock.md)）
- 消息队列异步下单（详见 [MQ 概念](../../_common/02-mq/01-concepts.md)）
- 限流防刷（详见 [限流算法](../../_common/03-cache-patterns/04-rate-limiting.md)）
- 订单 / 购物车（详见 [订单](./29-order.md)、[购物车](./28-cart.md)）

## 1. 核心概念

### 1.1 营销活动分类

| 活动类型 | 简写 | 说明 |
|----------|------|------|
| 优惠券 | Coupon | 满减、折扣券 |
| 秒杀 | Seckill | 限时特价 |
| 拼团 | Combination | N 人成团 |
| 砍价 | Bargain | 用户邀请砍价 |
| 满减送 | Reward | 满 N 元减 M 元 |
| 限时折扣 | Discount | 时间段折扣 |
| 积分商城 | Point | 积分兑换 |

### 1.2 优惠券核心字段

```java
public class CouponDO {
    private Long id;
    private String name;            // 券名
    private Integer type;           // 类型：1-满减 2-折扣
    private BigDecimal discountPrice; // 优惠金额
    private BigDecimal discountRate;  // 折扣率
    private Integer useThreshold;   // 满 X 元可用
    private Integer totalCount;     // 总发行量
    private Integer remainCount;    // 剩余数量
    private LocalDateTime validStartTime;
    private LocalDateTime validEndTime;
    private Integer status;
}
```

### 1.3 优惠计算流程

```
订单总金额
    ↓
[满减] -10
    ↓
[优惠券] -20
    ↓
[折扣] ×0.9
    ↓
应付金额
```

## 2. 代码示例

### 2.1 领取优惠券

```java
@PostMapping("/receive")
public CommonResult<Boolean> receiveCoupon(@RequestParam Long couponId) {
    couponService.receiveCoupon(getLoginUserId(), couponId);
    return success(true);
}

@Transactional
@Override
public void receiveCoupon(Long userId, Long couponId) {
    // 1. 校验优惠券
    CouponDO coupon = couponMapper.selectById(couponId);
    if (coupon.getRemainCount() <= 0) throw exception(COUPON_SOLD_OUT);
    // 2. 扣减库存（CAS 防止超发）
    int rows = couponMapper.decrementRemainCount(couponId);
    if (rows == 0) throw exception(COUPON_SOLD_OUT);
    // 3. 发放给用户
    CouponReceiveDO receive = new CouponReceiveDO();
    receive.setUserId(userId);
    receive.setCouponId(couponId);
    receive.setStatus(CouponStatusEnum.UNUSED.getStatus());
    couponReceiveMapper.insert(receive);
}
```

### 2.2 使用优惠券

```java
public BigDecimal calculateDiscount(Long userId, Long couponId, BigDecimal orderPrice) {
    CouponReceiveDO receive = couponReceiveMapper.selectByUserIdAndCouponId(userId, couponId);
    CouponDO coupon = couponMapper.selectById(receive.getCouponId());
    // 1. 校验有效期
    if (LocalDateTime.now().isAfter(coupon.getValidEndTime())) {
        throw exception(COUPON_EXPIRED);
    }
    // 2. 校验门槛
    if (orderPrice.compareTo(BigDecimal.valueOf(coupon.getUseThreshold())) < 0) {
        throw exception(COUPON_THRESHOLD_NOT_MET);
    }
    // 3. 计算优惠
    if (coupon.getType() == 1) {  // 满减
        return coupon.getDiscountPrice();
    } else {  // 折扣
        return orderPrice.multiply(BigDecimal.ONE.subtract(coupon.getDiscountRate()));
    }
}
```

### 2.3 秒杀活动

```java
@PostMapping("/seckill")
public CommonResult<Long> seckill(@RequestParam Long spuId) {
    return success(seckillService.doSeckill(getLoginUserId(), spuId));
}

public Long doSeckill(Long userId, Long spuId) {
    // 1. Redis 预扣减库存
    String key = "seckill:stock:" + spuId;
    Long stock = redisTemplate.opsForValue().decrement(key);
    if (stock < 0) {
        redisTemplate.opsForValue().increment(key);  // 恢复
        throw exception(SECKILL_SOLD_OUT);
    }
    // 2. 发送 MQ 异步处理下单
    rocketMQTemplate.send("seckill-order", new SeckillMessage(userId, spuId));
    return System.currentTimeMillis();
}
```

## 3. ruoyi 仓库源码解读

### 3.1 CouponController

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-promotion/src/main/java/cn/iocoder/yudao/module/promotion/controller/admin/coupon/CouponController.java`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 优惠券")
@RestController
@RequestMapping("/promotion/coupon")
@Validated
public class CouponController {

    @Resource
    private CouponService couponService;

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('promotion:coupon:create')")
    public CommonResult<Long> createCoupon(@Valid @RequestBody CouponSaveReqVO createReqVO) {
        return success(couponService.createCoupon(createReqVO));
    }

    @GetMapping("/page")
    public CommonResult<PageResult<CouponRespVO>> getCouponPage(@Valid CouponPageReqVO pageVO) {
        return success(couponService.getCouponPage(pageVO));
    }
}
```

### 3.2 秒杀活动

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-promotion/src/main/java/cn/iocoder/yudao/module/promotion/controller/admin/seckill/SeckillController.java`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 秒杀")
@RestController
@RequestMapping("/promotion/seckill")
@Validated
public class SeckillController {

    @Resource
    private SeckillService seckillService;

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('promotion:seckill:create')")
    public CommonResult<Long> createSeckill(@Valid @RequestBody SeckillSaveReqVO createReqVO) {
        return success(seckillService.createSeckill(createReqVO));
    }
}
```

## 4. 关键要点总结

- ruoyi 营销活动是一个独立子模块
- 优惠券需要考虑：领取限制、有效期、门槛、状态
- 秒杀用 Redis + MQ 解决高并发
- 拼团、砍价涉及多人交互
- 优惠金额计算要按顺序处理

## 5. 练习题

### 练习 1：基础（必做）

打开 `CouponDO.java`，列出字段。

### 练习 2：进阶

阅读 `SeckillServiceImpl.java`，理解秒杀预热和库存预扣的 Redis 实现。

### 练习 3：挑战（选做）

设计"拼团"完整流程：发起拼团 → 邀请好友 → 满员成团 → 商家发货。列出数据库表和关键接口。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-promotion/src/main/java/cn/iocoder/yudao/module/promotion/controller/admin/coupon/CouponController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-promotion/src/main/java/cn/iocoder/yudao/module/promotion/controller/admin/seckill/SeckillController.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
