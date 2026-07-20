# 4.3 生成主子表

> 实战演练：使用 ruoyi 代码生成器为主子表（如订单 + 订单明细）生成完整模块。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 NORMAL / ERP / INNER 三种主子表模式
- 配置主子表的 `masterTableId` / `subJoinColumnId` / `subJoinMany`
- 理解主子表的级联保存（创建/更新/删除）
- 理解主子表与外键引用的本质区别

## 📚 前置知识

- 模板分组 / 关联配置 / 单表生成（详见 [模板分组](./06-template-group.md)、[关联配置](./10-relation-config.md)、[单表生成](./18-gen-single.md)）

## 1. 核心概念

### 1.1 三种主子表模式对比

| 模式 | 子表存哪 | 子表接口 | 典型场景 |
|------|---------|---------|---------|
| **NORMAL (10)** | 主表 SaveReqVO 里嵌套 List<Sub> | 仅主表接口 | 订单 + 商品列表 |
| **ERP (11)** | 独立子表 | 子表独立 CRUD | 销售订单 + 销售明细 |
| **INNER (12)** | 主表字段为 JSON | 仅主表接口 | 用户 + 偏好设置 |

### 1.2 实战场景：销售订单（主）+ 销售明细（子）

```
erp_sales_order  (主表)               erp_sales_order_item  (子表)
├── id                                   ├── id
├── order_no                             ├── order_id   (关联主表)
├── customer_id                          ├── product_id
├── total_amount                         ├── quantity
└── ...                                  └── unit_price
```

## 2. 代码示例

### 2.1 NORMAL 模式 - 创建主+子

```java
@Override
@Transactional(rollbackFor = Exception.class)
public Long createSalesOrder(SalesOrderSaveReqVO createReqVO) {
    // 1. 保存主表
    SalesOrderDO order = BeanUtils.toBean(createReqVO, SalesOrderDO.class);
    salesOrderMapper.insert(order);

    // 2. 批量保存子表（子表随主表一起提交）
    List<SalesOrderItemDO> items = createReqVO.getItems().stream()
        .map(item -> {
            SalesOrderItemDO itemDO = BeanUtils.toBean(item, SalesOrderItemDO.class);
            itemDO.setOrderId(order.getId()); // 设置外键
            return itemDO;
        }).toList();
    salesOrderItemMapper.insertBatch(items);

    return order.getId();
}
```

### 2.2 ERP 模式 - 子表独立 CRUD

```java
// 子表独立 create
public Long createSalesOrderItem(SalesOrderItemDO item) {
    salesOrderItemMapper.insert(item);
    return item.getId();
}

// 子表独立 get
public SalesOrderItemDO getSalesOrderItem(Long id) {
    return salesOrderItemMapper.selectById(id);
}

// 子表独立 update
public void updateSalesOrderItem(SalesOrderItemDO item) {
    salesOrderItemMapper.updateById(item);
}

// 子表独立 delete
public void deleteSalesOrderItem(Long id) {
    salesOrderItemMapper.deleteById(id);
}
```

### 2.3 1:1 主子表（INNER 模式 + subJoinMany=false）

```java
public Long createUser(UserSaveReqVO createReqVO) {
    // 1. 保存主表
    UserDO user = BeanUtils.toBean(createReqVO, UserDO.class);
    userMapper.insert(user);

    // 2. 保存子表（1:1，仅一条记录）
    UserConfigDO config = BeanUtils.toBean(createReqVO.getConfig(), UserConfigDO.class);
    config.setUserId(user.getId());
    userConfigMapper.insertOrUpdate(config); // 1:1 用 insertOrUpdate 保留 ID

    return user.getId();
}
```

## 3. 关键要点总结

- 三种主子表模式：**NORMAL**（子表随主表提交）、**ERP**（子表独立 CRUD）、**INNER**（紧凑嵌套）
- 配置三件套：`masterTableId` + `subJoinColumnId` + `subJoinMany`
- 1:N 更新策略：**先删后插**（简单但 ID 会变）
- 1:1 更新策略：`insertOrUpdate`（保留 ID）
- 子表 API 路径：`/父路径/${subSimpleClassName_strikeCase}/...`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
