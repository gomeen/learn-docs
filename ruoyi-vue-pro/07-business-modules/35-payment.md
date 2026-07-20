# 7.5.5 支付集成：支付宝/微信

> 理解 ruoyi 的支付集成（Pay）模块。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 支付模块的设计
- 理解支付宝、微信支付的接入流程
- 学会支付回调和订单状态同步
- 能扩展新的支付渠道

## 📚 前置知识

- 订单流程（详见 [订单](./33-order.md)）
- 支付宝/微信支付 API
- 回调通知机制
- 防重放 / 幂等（支付回调，详见 [防重放](../../_common/05-web-security/07-replay-attack.md)）

## 1. 核心概念

### 1.1 ruoyi 支付模块设计

ruoyi 提供了独立的 `yudao-module-pay` 模块（注意：在模块结构中作为独立模块存在）：

```
yudao-module-pay/                  # 支付模块
├── yudao-module-pay-api           # 对外 API（订单模块调用）
├── yudao-module-pay-biz           # 支付业务实现
    ├── framework/
    │   └── pay/
    │       ├── client/            # 支付客户端抽象
    │       │   ├── PayClient      # 接口
    │       │   ├── alipay/        # 支付宝
    │       │   └── wxpay/         # 微信支付
    │       └── notify/            # 回调
    ├── controller/admin/
    └── dal/
```

### 1.2 PayClient 接口

```java
public interface PayClient {
    /**
     * 创建支付单
     */
    PayOrderRespDTO createPayOrder(PayOrderReqDTO reqDTO);

    /**
     * 查询支付状态
     */
    PayOrderRespDTO getPayOrder(String payOrderId);

    /**
     * 退款
     */
    PayRefundRespDTO refund(PayRefundReqDTO reqDTO);
}
```

### 1.3 支付状态机

```
未支付 ──支付回调──> 已支付 ──发货──> 已完成
   │
   │取消
   ↓
 已取消
   ↓
 退款 ──> 已退款
```

## 2. 代码示例

### 2.1 创建支付单

```java
@PostMapping("/create")
public CommonResult<AppPayRespVO> createPayOrder(@Valid @RequestBody AppPayCreateReqVO reqVO) {
    // 1. 校验订单
    OrderDO order = orderService.getOrder(reqVO.getOrderId());
    // 2. 创建支付单
    PayOrderReqDTO payReq = new PayOrderReqDTO();
    payReq.setAppId(payAppService.getAppId());
    payReq.setOrderId(order.getId());
    payReq.setOrderNo(order.getOrderNo());
    payReq.setAmount(order.getPayPrice());
    payReq.setSubject("订单：" + order.getOrderNo());
    // 3. 调用支付客户端
    PayOrderRespDTO payResp = payClient.createPayOrder(payReq);
    // 4. 返回支付参数（前端用于调起支付）
    return success(new AppPayRespVO(payResp.getPayUrl(), payResp.getPayData()));
}
```

### 2.2 支付回调

```java
@PostMapping("/notify/alipay")
public String notifyAlipay(HttpServletRequest request) throws Exception {
    // 1. 解析支付宝回调
    Map<String, String> params = parseAlipayNotify(request);
    // 2. 验证签名
    if (!alipayClient.verifySign(params)) {
        return "fail";
    }
    // 3. 处理支付成功
    String payOrderId = params.get("out_trade_no");
    payOrderService.notifyPaySuccess(payOrderId);
    // 4. 返回成功
    return "success";
}
```

### 2.3 支付成功处理

```java
@Transactional
public void notifyPaySuccess(String payOrderId) {
    // 1. 查询支付单
    PayOrderDO payOrder = payOrderMapper.selectById(payOrderId);
    if (PayOrderStatusEnum.SUCCESS.getStatus().equals(payOrder.getStatus())) {
        return;  // 幂等处理
    }
    // 2. 更新支付单
    payOrder.setStatus(PayOrderStatusEnum.SUCCESS.getStatus());
    payOrder.setPayTime(LocalDateTime.now());
    payOrderMapper.updateById(payOrder);
    // 3. 调用业务回调（订单状态更新）
    notifyService.notifyPayOrderSuccess(payOrder);
}
```

## 3. 关键要点总结

- ruoyi 支付是独立模块（`yudao-module-pay`）
- 通过 `PayClient` 抽象多种支付渠道
- 支付回调是核心，要**幂等**处理
- 支付单和业务订单解耦
- 退款独立流程

---

**文档版本**：v1.0
**最后更新**：2026-07-13
