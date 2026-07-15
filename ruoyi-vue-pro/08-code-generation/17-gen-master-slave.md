# 4.3 生成主子表

> 实战演练：使用 ruoyi 代码生成器为主子表（如订单 + 订单明细）生成完整模块。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 NORMAL / ERP / INNER 三种主子表模式
- 配置主子表的 `masterTableId` / `subJoinColumnId` / `subJoinMany`
- 理解主子表的级联保存（创建/更新/删除）
- 理解主子表与外键引用的本质区别

## 📚 前置知识

- 模板分组 / 关联配置 / 单表生成（详见 [模板分组](./05-template-group.md)、[关联配置](./09-relation-config.md)、[单表生成](./15-gen-single.md)）

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

## 3. ruoyi 仓库源码解读

### 3.1 NORMAL 模式 - 子表批量保存

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/service/serviceImpl.vm`

```velocity
## 1:N 主子表（更新策略：先删后插）
private void create${subSimpleClassName}List(Long ${classNameVar}Id, List<${subTable.className}DO> list) {
    if (CollUtil.isEmpty(list)) return;
    list.forEach(o -> o.${subJoinColumn.javaField} = ${classNameVar}Id);
    ${subClassNameVar}Mapper.insertBatch(list);
}

private void update${subSimpleClassName}List(Long ${classNameVar}Id, List<${subTable.className}DO> list) {
    delete${subSimpleClassName}List(${classNameVar}Id);
    create${subSimpleClassName}List(${classNameVar}Id, list);
}

private void delete${subSimpleClassName}List(Long ${classNameVar}Id) {
    ${subClassNameVar}Mapper.deleteBy${SubJoinColumnName}(${classNameVar}Id);
}
```

**关键占位符**：
- `${subSimpleClassName}` → `OrderItem`
- `${subJoinColumn.javaField}` → `orderId`
- `${SubJoinColumnName}` → `OrderId`（首字母大写）
- `${subClassNameVar}` → `orderItem`

### 3.2 ERP 模式 - 子表独立 CRUD 接口

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/controller/controller.vm` 行 200-296

```velocity
## 情况一：MASTER_ERP 时，子表有独立的 CRUD
#if ( $table.templateType == 11 )
    @GetMapping("/${subSimpleClassName_strikeCase}/page")
    public CommonResult<PageResult<${subTable.className}DO>> get${subSimpleClassName}Page(
        PageParam pageReqVO,
        @RequestParam("${subJoinColumn.javaField}") ${subJoinColumn.javaType} ${subJoinColumn.javaField}) {
        return success(${classNameVar}Service.get${subSimpleClassName}Page(pageReqVO, ${subJoinColumn.javaField}));
    }

    @PostMapping("/${subSimpleClassName_strikeCase}/create")
    public CommonResult<${subPrimaryColumn.javaType}> create${subSimpleClassName}(
        @Valid @RequestBody ${subTable.className}DO ${subClassNameVar}) {
        return success(${classNameVar}Service.create${subSimpleClassName}(${subClassNameVar}));
    }
    // ... update / delete / get / delete-list
#end
```

**解读**：
- ERP 模式（11）子表的 API 路径是 `/父路径/{子表短横线}/create`
- 用 `${subJoinColumn.javaField}` 作查询参数（如 `orderId`）
- 子表用 `subPrimaryColumn.javaType`（如 `Long`）

### 3.3 NORMAL/INNER 模式 - 列表/详情接口

```velocity
## 情况二：非 ERP 时，根据 subJoinMany 决定 list-by / get-by
#else
    #if ($subTable.subJoinMany)
    @GetMapping("/${subSimpleClassName_strikeCase}/list-by-${subJoinColumn_strikeCase}")
    public CommonResult<List<${subTable.className}DO>> get${subSimpleClassName}ListBy${SubJoinColumnName}(
        @RequestParam("${subJoinColumn.javaField}") ${subJoinColumn.javaType} ${subJoinColumn.javaField}) {
        return success(${classNameVar}Service.get${subSimpleClassName}ListBy${SubJoinColumnName}(${subJoinColumn.javaField}));
    }
    #else
    @GetMapping("/${subSimpleClassName_strikeCase}/get-by-${subJoinColumn_strikeCase}")
    public CommonResult<${subTable.className}DO> get${subSimpleClassName}By${SubJoinColumnName}(...) { ... }
    #end
#end
```

**解读**：
- 1:N 模式用 `list-by-xxx`（返回 List）
- 1:1 模式用 `get-by-xxx`（返回单个）
- 两种模式的 Service 方法名也对应（`getXxxListByYyy` / `getXxxByYyy`）

### 3.4 INDO_SUB（INNER 模式）DO 字段

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/dal/do.vm`（在主子表逻辑段）

```velocity
#if ($table.subTables && $voType == 20)
#foreach($subTable in $table.subTables)
#if ($subTable.subJoinMany)
    /** 子表：${subTable.classComment} */
    @TableField(exist = false)
    private List<${subTable.className}DO> ${subSimpleClassName}s;

#else
    /** 子表：${subTable.classComment} */
    @TableField(exist = false)
    private ${subTable.className}DO ${subSimpleClassName};
#end
#end
#end
```

**解读**：
- DO 中**额外**加 `@TableField(exist = false)` 字段引用子表
- 1:N → `List<SubDO>`
- 1:1 → `SubDO`
- `exist = false` 表示该字段不映射到 DB 列

## 4. 关键要点总结

- 三种主子表模式：**NORMAL**（子表随主表提交）、**ERP**（子表独立 CRUD）、**INNER**（紧凑嵌套）
- 配置三件套：`masterTableId` + `subJoinColumnId` + `subJoinMany`
- 1:N 更新策略：**先删后插**（简单但 ID 会变）
- 1:1 更新策略：`insertOrUpdate`（保留 ID）
- 子表 API 路径：`/父路径/${subSimpleClassName_strikeCase}/...`

## 5. 练习题

### 练习 1：基础（必做）

为 `mall_order` + `mall_order_item` 两张表配置主子表（1:N 模式），写出 `CodegenTableDO` 的 `masterTableId` / `subJoinColumnId` / `subJoinMany` 值。

### 练习 2：进阶

阅读 `serviceImpl.vm` 中 NORMAL 模式 `updateXxx` 方法的实现，分析它对子表 ID 的影响（提示：先删后插）。

### 练习 3：挑战（选做）

扩展生成器：让主子表支持"多对多"（学生 ↔ 课程），需要哪些模板改动？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/service/serviceImpl.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/controller/controller.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/codegen/CodegenTableDO.java`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
