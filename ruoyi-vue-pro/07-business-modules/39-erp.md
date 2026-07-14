# 7.7.2 ERP 采购/销售/库存

> 理解 ruoyi ERP 模块的采购、销售、库存管理。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi ERP 模块的整体设计
- 理解采购、销售、库存的关系
- 学会 ERP 的核心业务单据
- 能扩展自定义 ERP 业务

## 📚 前置知识

- 29-order.md（订单）
- 数据库事务基础
- 02-mvc-layers.md

## 1. 核心概念

### 1.1 ERP 业务全景

```
采购：供应商 → 采购订单 → 采购入库 → 应付账款
                                ↓
                            库存增加
                                ↓
销售：客户 → 销售订单 → 销售出库 → 应收账款
                                ↓
                            库存减少
                                ↓
                            财务收款
```

### 1.2 ruoyi ERP 子模块

| 模块 | 说明 |
|------|------|
| finance | 财务（应收/应付） |
| product | ERP 产品 |
| purchase | 采购（订单/入库） |
| sale | 销售（订单/出库） |
| stock | 库存（出入库/盘点） |
| statistics | 统计报表 |

### 1.3 核心单据

- **采购订单**（Purchase Order）
- **采购入库单**（Purchase In）
- **销售订单**（Sale Order）
- **销售出库单**（Sale Out）
- **库存调拨单**（Stock Transfer）
- **库存盘点单**（Stock Check）

## 2. 代码示例

### 2.1 采购订单

```java
@PostMapping("/create")
public CommonResult<Long> createPurchaseOrder(@Valid @RequestBody ErpPurchaseOrderSaveReqVO createReqVO) {
    return success(purchaseOrderService.createPurchaseOrder(createReqVO));
}

@Transactional
@Override
public Long createPurchaseOrder(ErpPurchaseOrderSaveReqVO createReqVO) {
    // 1. 校验供应商
    validateSupplier(createReqVO.getSupplierId());
    // 2. 保存订单
    ErpPurchaseOrderDO order = BeanUtils.toBean(createReqVO, ErpPurchaseOrderDO.class);
    order.setStatus(PurchaseOrderStatusEnum.DRAFT.getStatus());
    purchaseOrderMapper.insert(order);
    // 3. 保存订单项
    for (ErpPurchaseOrderItemDO item : createReqVO.getItems()) {
        item.setOrderId(order.getId());
        purchaseOrderItemMapper.insert(item);
    }
    return order.getId();
}
```

### 2.2 采购入库

```java
@Transactional
@Override
public void purchaseIn(Long orderId) {
    // 1. 查询订单
    ErpPurchaseOrderDO order = purchaseOrderMapper.selectById(orderId);
    // 2. 校验状态
    if (!PurchaseOrderStatusEnum.APPROVED.getStatus().equals(order.getStatus())) {
        throw exception(ORDER_NOT_APPROVED);
    }
    // 3. 写入入库单
    ErpPurchaseInDO inOrder = new ErpPurchaseInDO();
    BeanUtils.copyProperties(order, inOrder);
    inOrder.setSourceOrderId(orderId);
    purchaseInMapper.insert(inOrder);
    // 4. 增加库存
    for (ErpPurchaseOrderItemDO item : order.getItems()) {
        stockService.addStock(item.getWarehouseId(), item.getProductId(), item.getCount());
    }
    // 5. 更新订单状态
    order.setStatus(PurchaseOrderStatusEnum.IN.getStatus());
    purchaseOrderMapper.updateById(order);
}
```

### 2.3 库存管理

```java
public BigDecimal getStock(Long warehouseId, Long productId) {
    return stockMapper.selectStock(warehouseId, productId);
}

@Transactional
public void addStock(Long warehouseId, Long productId, Integer count) {
    StockDO stock = stockMapper.selectByWarehouseAndProduct(warehouseId, productId);
    if (stock == null) {
        // 初始化
        stock = new StockDO();
        stock.setWarehouseId(warehouseId);
        stock.setProductId(productId);
        stock.setCount(count);
        stockMapper.insert(stock);
    } else {
        // 增加
        stock.setCount(stock.getCount() + count);
        stockMapper.updateById(stock);
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 ERP 模块结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-erp/src/main/java/cn/iocoder/yudao/module/erp/`

```
yudao-module-erp/
├── controller/admin/
│   ├── finance/      # 财务
│   ├── product/      # ERP 产品
│   ├── purchase/     # 采购
│   ├── sale/         # 销售
│   ├── stock/        # 库存
│   └── statistics/   # 统计
├── convert/
├── dal/
├── enums/
└── service/
```

### 3.2 采购订单 Controller

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-erp/src/main/java/cn/iocoder/yudao/module/erp/controller/admin/purchase/`

```java
@Tag(name = "管理后台 - ERP 采购订单")
@RestController
@RequestMapping("/erp/purchase-order")
@Validated
public class ErpPurchaseOrderController {

    @Resource
    private ErpPurchaseOrderService purchaseOrderService;

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('erp:purchase-order:create')")
    public CommonResult<Long> createPurchaseOrder(@Valid @RequestBody ErpPurchaseOrderSaveReqVO createReqVO) {
        return success(purchaseOrderService.createPurchaseOrder(createReqVO));
    }

    @PutMapping("/update")
    public CommonResult<Boolean> updatePurchaseOrder(@Valid @RequestBody ErpPurchaseOrderSaveReqVO updateReqVO) {
        purchaseOrderService.updatePurchaseOrder(updateReqVO);
        return success(true);
    }

    @GetMapping("/page")
    public CommonResult<PageResult<ErpPurchaseOrderRespVO>> getPurchaseOrderPage(
            @Valid ErpPurchaseOrderPageReqVO pageVO) {
        return success(purchaseOrderService.getPurchaseOrderPage(pageVO));
    }
}
```

## 4. 关键要点总结

- ruoyi ERP 是独立业务模块
- 采购、销售、库存是核心三流（物流、资金流、信息流）
- 库存变动通过事务保证一致性
- 单据有"草稿/审批/执行/完成"等状态
- ERP 与财务模块联动（应收应付）

## 5. 练习题

### 练习 1：基础（必做）

阅读 `ErpPurchaseOrderDO.java` 字段。

### 练习 2：进阶

阅读 `ErpStockServiceImpl.java`，理解库存的增加、减少、锁定、释放。

### 练习 3：挑战（选做）

设计"库存预警"功能：当库存低于阈值时，自动发送通知。列出实现方案。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-erp/src/main/java/cn/iocoder/yudao/module/erp/controller/admin/purchase/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
