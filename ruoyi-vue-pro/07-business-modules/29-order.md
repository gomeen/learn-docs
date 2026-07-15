# 7.5.4 订单流程：创建/支付/发货/收货/退款

> 理解 ruoyi 商城订单的完整生命周期。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 订单的状态机
- 理解订单创建、支付、发货、收货、退款完整流程
- 学会订单金额计算和优惠处理
- 能扩展订单业务

## 📚 前置知识

- 商品 / 购物车（详见 [SPU/SKU](./26-spu-sku.md)、[购物车](./28-cart.md)）
- 状态机模式（详见 [状态模式](../../_fundamentals/06-design-patterns/19-state.md)）
- 事务 / 分布式事务基础（详见 [事务](../02-spring-boot/04-transaction.md)）
- 支付集成（详见 [支付](./30-payment.md)）

## 1. 核心概念

### 1.1 订单状态机

```
待支付 ──支付──> 待发货 ──发货──> 待收货 ──收货──> 已完成
  │              │              │              │
  │取消          │退款          │退货          │评价
  ↓              ↓              ↓
 已取消         退款中         退款中
                  ↓
                已退款
```

### 1.2 订单表设计

```sql
-- 订单主表
CREATE TABLE trade_order (
    id BIGINT,
    order_no VARCHAR(64),     -- 订单号
    user_id BIGINT,
    type INT,                 -- 类型：普通/秒杀/拼团
    status INT,               -- 状态
    total_price DECIMAL,      -- 总金额
    pay_price DECIMAL,        -- 实际支付
    freight_price DECIMAL,    -- 运费
    discount_price DECIMAL,   -- 优惠金额
    address_id BIGINT,
    pay_time DATETIME,
    delivery_time DATETIME,
    receive_time DATETIME,
    finish_time DATETIME
);

-- 订单项
CREATE TABLE trade_order_item (
    id BIGINT,
    order_id BIGINT,
    spu_id BIGINT,
    sku_id BIGINT,
    count INT,
    price DECIMAL,
    properties VARCHAR(500)
);
```

### 1.3 核心字段

```java
public class OrderDO {
    private Long id;
    private String orderNo;          // 订单号
    private Long userId;
    private Integer type;            // 类型
    private Integer status;          // 状态
    private BigDecimal totalPrice;   // 商品总金额
    private BigDecimal discountPrice;// 优惠金额
    private BigDecimal freightPrice; // 运费
    private BigDecimal payPrice;     // 应付金额
    private Long addressId;
    private LocalDateTime payTime;
    private LocalDateTime deliveryTime;
    private LocalDateTime receiveTime;
}
```

## 2. 代码示例

### 2.1 订单状态枚举

```java
public enum OrderStatusEnum {
    UNPAID(0, "待支付"),
    PAID(10, "已支付"),
    DELIVERED(20, "已发货"),
    FINISHED(30, "已完成"),
    CANCELLED(40, "已取消"),
    REFUNDING(50, "退款中"),
    REFUNDED(60, "已退款");

    public static boolean isUnpaid(Integer status) {
        return UNPAID.getStatus().equals(status);
    }
}
```

### 2.2 创建订单核心逻辑

```java
@Override
@Transactional(rollbackFor = Exception.class)
public Long createOrder(Long userId, AppOrderCreateReqVO createReqVO) {
    // 1. 校验购物车
    List<CartDO> carts = cartService.getCartList(userId, createReqVO.getCartIds());
    if (carts.isEmpty()) throw exception(ORDER_CART_EMPTY);
    // 2. 校验库存
    validateStock(carts);
    // 3. 锁定库存
    lockStock(carts);
    // 4. 计算价格
    OrderPriceBO priceBO = calculatePrice(userId, carts, createReqVO.getCouponId());
    // 5. 保存订单
    OrderDO order = new OrderDO();
    order.setOrderNo(generateOrderNo());
    order.setUserId(userId);
    order.setStatus(OrderStatusEnum.UNPAID.getStatus());
    order.setTotalPrice(priceBO.getTotalPrice());
    order.setPayPrice(priceBO.getPayPrice());
    orderMapper.insert(order);
    // 6. 保存订单项
    for (CartDO cart : carts) {
        OrderItemDO item = new OrderItemDO();
        item.setOrderId(order.getId());
        item.setSpuId(cart.getSpuId());
        item.setSkuId(cart.getSkuId());
        item.setCount(cart.getCount());
        item.setPrice(getSkuPrice(cart.getSkuId()));
        orderItemMapper.insert(item);
    }
    // 7. 清理购物车
    cartService.deleteCart(userId, createReqVO.getCartIds());
    return order.getId();
}
```

### 2.3 订单支付

```java
@Override
public void payOrder(Long userId, AppOrderPayReqVO payReqVO) {
    // 1. 校验订单
    OrderDO order = orderMapper.selectById(payReqVO.getOrderId());
    if (!order.getUserId().equals(userId)) throw exception(ORDER_NOT_EXISTS);
    if (!OrderStatusEnum.UNPAID.getStatus().equals(order.getStatus())) {
        throw exception(ORDER_STATUS_NOT_UNPAID);
    }
    // 2. 调用支付
    PayOrderRespDTO payResp = payApi.createPayOrder(order);
    // 3. 更新订单支付单号
    orderMapper.updatePayOrderId(order.getId(), payResp.getId());
}
```

### 2.4 支付回调（订单流转）

```java
@Transactional
public void onPaySuccess(String payOrderId) {
    // 1. 查询订单
    OrderDO order = orderMapper.selectByPayOrderId(payOrderId);
    if (order == null) return;
    // 2. 更新状态
    order.setStatus(OrderStatusEnum.PAID.getStatus());
    order.setPayTime(LocalDateTime.now());
    orderMapper.updateById(order);
    // 3. 扣减真实库存
    deductStock(order);
    // 4. 发送通知
    notifyService.sendPaidSuccess(order);
}
```

### 2.5 发货

```java
@Override
public void deliveryOrder(Long orderId, String logisticsNo) {
    OrderDO order = orderMapper.selectById(orderId);
    if (!OrderStatusEnum.PAID.getStatus().equals(order.getStatus())) {
        throw exception(ORDER_STATUS_NOT_PAID);
    }
    order.setStatus(OrderStatusEnum.DELIVERED.getStatus());
    order.setDeliveryTime(LocalDateTime.now());
    orderMapper.updateById(order);
    // 记录物流
    deliveryService.createDelivery(order, logisticsNo);
}
```

## 3. ruoyi 仓库源码解读

### 3.1 OrderController

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-trade/src/main/java/cn/iocoder/yudao/module/trade/controller/admin/order/OrderController.java`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 订单")
@RestController
@RequestMapping("/trade/order")
@Validated
public class OrderController {

    @Resource
    private OrderService orderService;

    @GetMapping("/page")
    @PreAuthorize("@ss.hasPermission('trade:order:query')")
    public CommonResult<PageResult<OrderRespVO>> getOrderPage(@Valid OrderPageReqVO pageVO) {
        return success(orderService.getOrderPage(pageVO));
    }

    @PutMapping("/delivery")
    @PreAuthorize("@ss.hasPermission('trade:order:delivery')")
    public CommonResult<Boolean> deliveryOrder(@RequestParam("id") Long id,
                                                 @RequestParam("logisticsNo") String logisticsNo) {
        orderService.deliveryOrder(id, logisticsNo);
        return success(true);
    }

    @PutMapping("/cancel")
    public CommonResult<Boolean> cancelOrder(@RequestParam("id") Long id) {
        orderService.cancelOrder(id);
        return success(true);
    }
}
```

### 3.2 订单状态变更

订单状态变更统一在 Service 中处理，确保：
- 状态合法性校验
- 关联数据更新（库存、支付）
- 触发领域事件（消息队列）

## 4. 关键要点总结

- 订单是电商核心，状态机管理生命周期
- 订单号生成规则：业务前缀 + 时间戳 + 随机数
- 创建订单涉及：库存锁定、价格计算、订单写入、购物车清理
- 支付成功后通过回调更新状态
- 发货、收货、退款都有独立状态

## 5. 练习题

### 练习 1：基础（必做）

打开 `OrderDO.java`，列出所有字段，理解每个字段含义。

### 练习 2：进阶

阅读 `OrderServiceImpl.java`，理解订单创建的价格计算逻辑（运费、优惠、实付）。

### 练习 3：挑战（选做）

设计"超时不发货自动退款"功能：24 小时未发货自动退款，列出实现方案（提示：定时任务 + 状态机）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-trade/src/main/java/cn/iocoder/yudao/module/trade/controller/admin/order/OrderController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-trade/src/main/java/cn/iocoder/yudao/module/trade/service/order/OrderServiceImpl.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
