# 2.5 关联字段配置

> 学习 ruoyi 代码生成器如何处理表与表之间的"关联关系"，特别是主子表。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释主子表的"三件套"：`masterTableId` / `subJoinColumnId` / `subJoinMany`
- 解释主子表在 Service 中如何级联保存
- 配置主子表关联（多对一、一对多、一对一）
- 区分主子表与"外键引用"的区别

## 📚 前置知识

- 阅读过 `05-template-group.md`
- 数据库外键基础
- `CodegenTemplateTypeEnum` 枚举

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

## 3. ruoyi 仓库源码解读

### 3.1 关联字段在元数据中的位置

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/codegen/CodegenTableDO.java` 行 117-137

```java
// ========== 主子表相关字段 ==========

/**
 * 主表的编号
 * 关联 {@link CodegenTableDO#getId()}
 */
private Long masterTableId;

/**
 * 【自己】子表关联主表的字段编号
 * 关联 {@link CodegenColumnDO#getId()}
 */
private Long subJoinColumnId;

/**
 * 主表与子表是否一对多
 * true：一对多
 * false：一对一
 */
private Boolean subJoinMany;
```

**解读**：
- `masterTableId` 是**指向**主表的 ID（不是名称）
- `subJoinColumnId` 指向**子表中**关联字段的元数据 ID（即 `CodegenColumnDO.id`）
- `subJoinMany` 用 Boolean 表示 1:N / 1:1

### 3.2 主子表 - NORMAL 模式 ServiceImpl 片段

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/service/serviceImpl.vm`
**核心代码**（行 200-260，简化）：

```velocity
## 1. 批量保存子表（一对多场景）
private void createSubList(Long mainId, List<${subSimpleClassName}> list) {
    if (CollUtil.isEmpty(list)) return;
    List<${subTable.className}DO> subList = BeanUtils.toBean(list, ${subTable.className}DO.class);
    subList.forEach(o -> o.${subJoinColumn.javaField} = mainId);
    ${subClassNameVar}Mapper.insertBatch(subList);
}

## 2. 更新子表（先删后插）
private void updateSubList(Long mainId, List<${subSimpleClassName}> list) {
    deleteSubList(mainId);
    createSubList(mainId, list);
}

## 3. 删除子表
private void deleteSubList(Long mainId) {
    ${subClassNameVar}Mapper.deleteBy${SubJoinColumnName}(mainId);
}
```

**解读**：
- 一对多的子表更新策略是**"先全部删，再全部插"**——简单但会改变 ID
- 一对一时改为"按 ID 更新"——保留 ID
- 子表删除支持根据外键批量删

### 3.3 关联字段在 Controller 中的体现

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/controller/controller.vm` 行 200-296
**核心代码**（简化）：

```velocity
## 情况一：MASTER_ERP 时，子表有独立的分页查询
#if ($table.templateType == 11)
    @GetMapping("/${subSimpleClassName_strikeCase}/page")
    public CommonResult<PageResult<...>> get${subSimpleClassName}Page(
        PageParam pageReqVO,
        @RequestParam("${subJoinColumn.javaField}") ${subJoinColumn.javaType} ${subJoinColumn.javaField}) {
        return success(${classNameVar}Service.get${subSimpleClassName}Page(pageReqVO, ${subJoinColumn.javaField}));
    }
## 情况二：非 ERP 时，根据 subJoinMany 决定 list-by / get-by
#else
    #if ($subTable.subJoinMany)
    @GetMapping("/${subSimpleClassName_strikeCase}/list-by-${subJoinColumn_strikeCase}")
    public CommonResult<List<...>> get${subSimpleClassName}ListBy${SubJoinColumnName}(...) { ... }
    #else
    @GetMapping("/${subSimpleClassName_strikeCase}/get-by-${subJoinColumn_strikeCase}")
    public CommonResult<...> get${subSimpleClassName}By${SubJoinColumnName}(...) { ... }
    #end
#end
```

**解读**：
- ERP 模式（11）→ 子表有独立分页
- NORMAL/INNER 模式 → 一对多用 list-by，一对一无 list（用 get-by）

## 4. 关键要点总结

- 主子表的核心配置是**三件套**：`masterTableId` + `subJoinColumnId` + `subJoinMany`
- 关联**只支持"主子表"**这种"紧密耦合"关系，不支持任意多表 JOIN
- NORMAL/INNER 模式子表随主表保存
- ERP 模式子表有独立 CRUD 接口
- 子表更新策略：1:N 用"先删后插"，1:1 用"按 ID 更新"

## 5. 练习题

### 练习 1：基础（必做）

假设有 `mall_order`（主表）和 `mall_order_item`（子表），写出 `subJoinColumnId` 指向哪个字段？为什么？

### 练习 2：进阶

阅读 `serviceImpl.vm` 中"主子表 ERP 模式"的相关代码，画出"创建主表+子表"和"删除主表"的方法调用链。

### 练习 3：挑战（选做）

主子表能否支持"多对多"（如 学生-课程）？需要修改 `CodegenTableDO` 哪些字段？模板需要改哪些 `#if` 块？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/codegen/CodegenTableDO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/service/serviceImpl.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/controller/controller.vm`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
