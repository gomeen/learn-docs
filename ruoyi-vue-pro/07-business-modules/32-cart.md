# 7.5.3 购物车

> 理解 ruoyi 商城购物车（Cart）的设计与实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 购物车的设计
- 理解购物车的持久化和缓存策略
- 学会购物车商品数量、选中状态管理
- 能扩展购物车业务

## 📚 前置知识

- 会员认证（详见 [会员认证](./24-member-auth.md)）
- SPU/SKU（详见 [SPU/SKU](./30-spu-sku.md)）
- Redis 基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- 缓存策略（详见 [缓存策略](../../_common/03-cache-patterns/01-strategies.md)）

## 1. 核心概念

### 1.1 购物车设计

**两种存储方式**：

| 方式 | 适用场景 | 优缺点 |
|------|----------|--------|
| 登录前 - LocalStorage | 未登录用户 | 简单，但不跨设备 |
| 登录后 - 数据库 | 登录用户 | 跨设备同步 |

ruoyi 同时支持：
- 登录后使用 DB 持久化
- 未登录时使用 Redis 临时存储

### 1.2 购物车表

```sql
CREATE TABLE trade_cart (
    id BIGINT PRIMARY KEY,
    user_id BIGINT,
    spu_id BIGINT,
    sku_id BIGINT,
    count INT,                -- 数量
    selected BOOLEAN,         -- 是否选中
    create_time DATETIME
);
```

### 1.3 核心字段

```java
public class CartDO {
    private Long id;
    private Long userId;
    private Long spuId;
    private Long skuId;
    private Integer count;
    private Boolean selected;
    private LocalDateTime createTime;
}
```

## 2. 代码示例

### 2.1 添加购物车

```java
@PostMapping("/add")
public CommonResult<Boolean> addCart(@Valid @RequestBody AppCartAddReqVO addReqVO) {
    cartService.addCart(getLoginUserId(), addReqVO);
    return success(true);
}

@Override
@Transactional
public void addCart(Long userId, AppCartAddReqVO addReqVO) {
    // 1. 校验 SKU
    ProductSkuDO sku = skuService.getSku(addReqVO.getSkuId());
    if (sku == null || sku.getStock() < addReqVO.getCount()) {
        throw exception(SKU_NOT_ENOUGH_STOCK);
    }
    // 2. 查询是否已存在
    CartDO cart = cartMapper.selectByUserIdAndSkuId(userId, addReqVO.getSkuId());
    if (cart == null) {
        // 3. 新增
        cart = new CartDO();
        cart.setUserId(userId);
        cart.setSpuId(sku.getSpuId());
        cart.setSkuId(sku.getId());
        cart.setCount(addReqVO.getCount());
        cart.setSelected(true);
        cartMapper.insert(cart);
    } else {
        // 4. 累加数量
        cart.setCount(cart.getCount() + addReqVO.getCount());
        cartMapper.updateById(cart);
    }
}
```

### 2.2 购物车列表

```java
@GetMapping("/list")
public CommonResult<List<AppCartRespVO>> getCartList() {
    return success(cartService.getCartList(getLoginUserId()));
}
```

### 2.3 修改数量

```java
@PutMapping("/update-count")
public CommonResult<Boolean> updateCartCount(@RequestParam("id") Long id,
                                              @RequestParam("count") Integer count) {
    cartService.updateCartCount(getLoginUserId(), id, count);
    return success(true);
}
```

### 2.4 选中/取消选中

```java
@PutMapping("/update-selected")
public CommonResult<Boolean> updateCartSelected(@Valid @RequestBody AppCartSelectedReqVO reqVO) {
    cartService.updateCartSelected(getLoginUserId(), reqVO);
    return success(true);
}
```

## 3. 关键要点总结

- 购物车是会员的 1:N 数据
- 通过 (userId, skuId) 唯一索引防重
- 选中状态独立维护
- 库存独立校验
- 删除可以批量

---

**文档版本**：v1.0
**最后更新**：2026-07-13
