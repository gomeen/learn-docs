# 2.5 关联字段配置

> 学习 ruoyi 代码生成器如何处理表与表之间的"关联关系"，特别是主子表。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释主子表的"三件套"：`masterTableId` / `subJoinColumnId` / `subJoinMany`
- 解释主子表在 Service 中如何级联保存
- 配置主子表关联（多对一、一对多、一对一）
- 区分主子表与"外键引用"的区别

## 📚 前置知识

- 模板分组（详见 [模板分组](./06-template-group.md)）
- 数据库外键基础
- `CodegenTemplateTypeEnum` 枚举
- 主子表生成（详见 [主子表生成](./20-gen-master-slave.md)）

## 1. 核心概念

### 1.1 关联关系分类

| 关系 | 例子 | ruoyi 处理 |
|------|------|-----------|
| **主子表（1:N）** | 订单 → 订单明细 | `MASTER_NORMAL/ERP/INNER` 模式 |
| **主子表（1:1）** | 用户 → 用户扩展信息 | `MASTER_INNER` + `subJoinMany=false` |
| **外键引用（多对一）** | 文章 → 作者 | 普通字段，不特殊处理 |

### 1.2 三个关键字段

```java
// 在 CodegenTableDO 中
private Long masterTableId;   // 主表 ID（子表才有）
private Long subJoinColumnId; // 子表关联主表的字段（指向 CodegenColumnDO.id）
private Boolean subJoinMany;  // true = 一对多, false = 一对一
```

**配置步骤**：
1. 主表/子表都先**单独导入**到代码生成列表
2. 在子表的"修改生成配置"页，设置：
   - `masterTableId` = 主表的 ID
   - `subJoinColumnId` = 子表中关联字段的 ID（如 `orderId`）
   - `subJoinMany` = true / false

## 2. 代码示例

### 2.1 主子表 - NORMAL 模式 Service

```java
// 销售订单 + 销售订单明细
@Override
@Transactional(rollbackFor = Exception.class)
public Long createOrder(OrderSaveReqVO createReqVO) {
    // 1. 保存主表
    OrderDO order = BeanUtils.toBean(createReqVO, OrderDO.class);
    orderMapper.insert(order);

    // 2. 批量保存子表
    List<OrderItemDO> items = createReqVO.getItems().stream().map(item -> {
        OrderItemDO itemDO = BeanUtils.toBean(item, OrderItemDO.class);
        itemDO.setOrderId(order.getId()); // 关键：设置外键
        return itemDO;
    }).toList();
    orderItemMapper.insertBatch(items);

    return order.getId();
}
```

### 2.2 主子表 - INNER 模式（1:1）

```java
// 用户 + 用户配置（1:1）
public Long createUser(UserSaveReqVO reqVO) {
    UserDO user = BeanUtils.toBean(reqVO, UserDO.class);
    userMapper.insert(user);

    UserConfigDO config = BeanUtils.toBean(reqVO.getConfig(), UserConfigDO.class);
    config.setUserId(user.getId()); // 1:1 关联
    userConfigMapper.insert(config);

    return user.getId();
}
```

## 3. 关键要点总结

- 主子表的核心配置是**三件套**：`masterTableId` + `subJoinColumnId` + `subJoinMany`
- 关联**只支持"主子表"**这种"紧密耦合"关系，不支持任意多表 JOIN
- NORMAL/INNER 模式子表随主表保存
- ERP 模式子表有独立 CRUD 接口
- 子表更新策略：1:N 用"先删后插"，1:1 用"按 ID 更新"

---

**文档版本**：v1.0
**最后更新**：2026-07-13
