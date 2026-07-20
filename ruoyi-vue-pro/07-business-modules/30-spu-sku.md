# 7.5.1 商品 SPU/SKU 设计

> 理解 ruoyi 商城中 SPU（Standard Product Unit）和 SKU（Stock Keeping Unit）的设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 SPU 和 SKU 的概念和区别
- 理解 ruoyi 商品模块的完整表结构
- 学会商品属性、规格的设计
- 能设计自己的 SPU/SKU 数据模型

## 📚 前置知识

- 数据库设计基础
- MVC 分层（详见 [MVC 分层](./02-mvc-layers.md)）

## 1. 核心概念

### 1.1 SPU vs SKU

| 概念 | 全称 | 含义 | 例子 |
|------|------|------|------|
| **SPU** | Standard Product Unit | 标准化产品单元 | iPhone 15 |
| **SKU** | Stock Keeping Unit | 库存单元 | iPhone 15 128G 黑色 |

**关系**：
```
SPU（iPhone 15）
├── SKU 1: 128G / 黑色
├── SKU 2: 128G / 白色
├── SKU 3: 256G / 黑色
└── SKU 4: 256G / 白色
```

### 1.2 ruoyi 的商品表设计

```
product_spu            # SPU 主表（商品）
├── product_sku        # SKU 表（库存单元）
├── product_sku_spec   # SKU 规格值
├── product_attribute  # 属性表
├── product_category   # 分类
└── product_brand      # 品牌
```

### 1.3 核心字段

**SPU 主表**：
```java
public class ProductSpuDO {
    private Long id;
    private String name;              // 商品名
    private String keyword;           // 关键字
    private String introduction;      // 介绍
    private String description;       // 详细描述
    private String categoryId;        // 分类 ID
    private String brandId;           // 品牌 ID
    private String picUrl;            // 主图
    private String sliderPicUrls;     // 轮播图（JSON）
    private Integer status;           // 状态
    private BigDecimal price;         // 默认价格
    private Integer stock;            // 总库存
    private Integer salesCount;       // 销量
    private Integer commentCount;
    private Integer sort;
    private Integer deliveryType;     // 配送方式
}
```

**SKU 表**：
```java
public class ProductSkuDO {
    private Long id;
    private Long spuId;
    private String properties;        // 规格属性 JSON: [{"pid":1,"vid":2}]
    private String skuCode;           // SKU 编码
    private BigDecimal price;         // 售价
    private BigDecimal marketPrice;   // 市场价
    private BigDecimal costPrice;     // 成本价
    private Integer stock;            // 库存
    private Integer warnStock;        // 预警库存
    private String picUrl;
    private Integer salesCount;
    private Integer status;
}
```

## 2. 代码示例

### 2.1 创建 SPU 完整流程

```java
@Override
@Transactional(rollbackFor = Exception.class)
public Long createSpu(ProductSpuSaveReqVO createReqVO) {
    // 1. 校验分类、品牌
    validateCategory(createReqVO.getCategoryId());
    validateBrand(createReqVO.getBrandId());
    // 2. 保存 SPU
    ProductSpuDO spu = BeanUtils.toBean(createReqVO, ProductSpuDO.class);
    spuMapper.insert(spu);
    // 3. 保存 SKU 列表
    if (createReqVO.getSkus() != null) {
        for (ProductSkuDO sku : createReqVO.getSkus()) {
            sku.setSpuId(spu.getId());
            skuMapper.insert(sku);
        }
    }
    // 4. 保存商品属性
    if (createReqVO.getAttributes() != null) {
        for (ProductAttrDO attr : createReqVO.getAttributes()) {
            attr.setSpuId(spu.getId());
            attrMapper.insert(attr);
        }
    }
    return spu.getId();
}
```

### 2.2 SKU 规格 JSON

```json
[
  {"propertyId": 1, "valueId": 2, "propertyName": "颜色", "valueName": "黑色"},
  {"propertyId": 2, "valueId": 5, "propertyName": "容量", "valueName": "128G"}
]
```

### 2.3 商品状态管理

```java
public enum ProductStatusEnum {
    RECYCLE(-1, "回收站"),
    DISABLE(0, "下架"),
    ENABLE(1, "上架");
}
```

## 3. 关键要点总结

- SPU 是"产品"，SKU 是"具体规格的库存单元"
- SKU 通过 JSON 字段存储规格组合
- 商品状态：下架/上架/回收站
- 上下架是独立操作（不改数据，只改状态）
- 库存只在 SKU 级别维护

---

**文档版本**：v1.0
**最后更新**：2026-07-13
