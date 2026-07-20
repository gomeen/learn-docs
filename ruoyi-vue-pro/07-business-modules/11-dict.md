# 7.2.5 字典管理

> 理解 ruoyi 中数据字典（Dict）的设计和实现，type + data 的两级结构。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 字典的两级结构（DictType + DictData）
- 理解字典在前端下拉框的使用场景
- 学会字典的查询接口设计
- 理解字典的缓存设计

## 📚 前置知识

- 统一响应（详见 [CommonResult](./05-common-result.md)）
- Redis / 本地缓存（详见 [ruoyi 缓存场景](../05-cache-and-mq/11-ruoyi-cache-usage.md)）
- 部门树（详见 [部门](./10-dept.md)）

## 1. 核心概念

### 1.1 字典的两级结构

ruoyi 的字典分两类：

**DictType**（字典类型）：定义一个字典的"分类"
```java
DictTypeDO { id, type, name, status }
例子：{ type: "user_status", name: "用户状态" }
```

**DictData**（字典数据）：字典的具体"项"
```java
DictDataDO { id, dictType, label, value, sort, status }
例子：{ dictType: "user_status", label: "启用", value: "0" }
                     { dictType: "user_status", label: "禁用", value: "1" }
```

### 1.2 字典的使用场景

字典常用于前端**下拉框**的选项数据：

```json
GET /system/dict-data/simple-list
[
  { "label": "启用", "value": "0" },
  { "label": "禁用", "value": "1" }
]
```

**常见字典**：
- `user_status`：用户状态（启用/禁用）
- `common_status`：通用状态
- `sex`：性别
- `menu_type`：菜单类型
- `system_notice_type`：通知类型

### 1.3 字典的缓存设计

字典数据**极少变化**，全部加载到 Redis：

```java
// 启动时全量加载
@PostConstruct
public void init() {
    // 把所有 DictData 按 type 分组缓存到 Redis
}

// 写时清空
@CacheEvict(cacheNames = "dict_data", allEntries = true)
public void updateDictData(...) { ... }
```

## 2. 代码示例

### 2.1 DictType 和 DictData 的关系

```java
// 字典类型
public class DictTypeDO {
    private Long id;
    private String type;    // 类型编码，如 "user_status"
    private String name;    // 类型名称，如 "用户状态"
    private Integer status;
}

// 字典数据
public class DictDataDO {
    private Long id;
    private String dictType;  // 关联到 DictType.type
    private String label;     // 显示文本，如 "启用"
    private String value;     // 实际值，如 "0"
    private Integer sort;
    private String colorType; // 前端标签颜色
    private String cssClass;  // CSS class
    private Integer status;
}
```

### 2.2 字典响应 VO

```java
@Data
public class DictDataSimpleRespVO {
    private String label;   // 显示文本
    private String value;   // 实际值
    private String colorType;  // 颜色
    private String cssClass;
}
```

## 3. 关键要点总结

- 字典分 DictType（类型）和 DictData（数据）两级
- 字典用于前端下拉框
- `/simple-list` 接口免鉴权（前端全局需要）
- 字典数据通常全量缓存到 Redis
- DictData 有 `label`（显示）+ `value`（实际值）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
