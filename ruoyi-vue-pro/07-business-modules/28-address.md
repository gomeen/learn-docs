# 7.4.5 收货地址

> 理解 ruoyi 会员收货地址（Address）模块的设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 收货地址的设计
- 理解"默认地址"的唯一性设计
- 学会省市区级联数据结构
- 能扩展收货地址业务

## 📚 前置知识

- 会员认证（详见 [会员认证](./24-member-auth.md)）
- DTO/VO/DO（详见 [DTO/VO/DO](./03-dto-vo-do.md)）

## 1. 核心概念

### 1.1 收货地址模型

```
[用户] 1:N [收货地址]
              ↓
          [默认地址唯一]
              ↓
      [省/市/区 级联]
```

### 1.2 核心字段

```java
public class MemberAddressDO {
    private Long id;
    private Long userId;          // 所属用户
    private String name;          // 收货人
    private String mobile;        // 收货手机
    private String provinceCode;  // 省编码
    private String provinceName;
    private String cityCode;
    private String cityName;
    private String areaCode;
    private String areaName;
    private String detailAddress; // 详细地址
    private Boolean defaultStatus; // 是否默认
    private Integer areaId;       // 区域 ID
}
```

### 1.3 默认地址设计

- 同一用户只能有一个默认地址
- 切换默认地址时**事务更新**两条记录
- 新建地址可选择是否默认

## 2. 代码示例

### 2.1 收货地址 CRUD

```java
@PostMapping("/create")
public CommonResult<Long> createAddress(@Valid @RequestBody MemberAddressSaveReqVO createReqVO) {
    return success(addressService.createAddress(getLoginUserId(), createReqVO));
}

@PutMapping("/update")
public CommonResult<Boolean> updateAddress(@Valid @RequestBody MemberAddressSaveReqVO updateReqVO) {
    addressService.updateAddress(getLoginUserId(), updateReqVO);
    return success(true);
}

@DeleteMapping("/delete")
public CommonResult<Boolean> deleteAddress(@RequestParam("id") Long id) {
    addressService.deleteAddress(getLoginUserId(), id);
    return success(true);
}

@GetMapping("/list")
public CommonResult<List<MemberAddressRespVO>> getAddressList() {
    return success(BeanUtils.toBean(addressService.getAddressList(getLoginUserId()),
            MemberAddressRespVO.class));
}
```

### 2.2 设为默认地址

```java
@PutMapping("/set-default")
public CommonResult<Boolean> setDefaultAddress(@RequestParam("id") Long id) {
    addressService.setDefaultAddress(getLoginUserId(), id);
    return success(true);
}

@Transactional
@Override
public void setDefaultAddress(Long userId, Long id) {
    // 1. 取消所有默认
    addressMapper.updateDefaultStatus(userId, false, null);
    // 2. 设置新的默认
    addressMapper.updateDefaultStatus(userId, true, id);
}
```

### 2.3 获取默认地址

```java
@GetMapping("/get-default")
public CommonResult<MemberAddressRespVO> getDefaultAddress() {
    MemberAddressDO address = addressService.getDefaultAddress(getLoginUserId());
    return success(BeanUtils.toBean(address, MemberAddressRespVO.class));
}
```

## 3. 关键要点总结

- 收货地址是会员的 1:N 数据
- 默认地址唯一，通过事务保证
- 省市区用 code + name 双重存储
- 详细地址是用户输入的字符串
- 地址常用于订单的下单流程

---

**文档版本**：v1.0
**最后更新**：2026-07-13
