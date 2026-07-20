# 6.6 Excel 导入导出：EasyExcel

> 掌握 yudao 基于 EasyExcel 的 Excel 导入导出增强。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解 yudao Excel Starter 的能力
- 掌握 EasyExcel 的 `@ExcelProperty` 等注解
- 能用 `ExcelUtils` 实现导入导出
- 了解字典翻译在 Excel 中的应用

## 📚 前置知识

- EasyExcel 基础
- Apache POI

## 1. 核心概念

### 1.1 yudao Excel Starter 能力

| 能力 | 组件 |
|------|------|
| 导入导出工具 | `ExcelUtils` |
| 字典转换 | `DictDataConvert` |
| 多级表头 | `MultiDictConvert` |
| 数字格式化 | `MoneyConvert` |
| 下拉框 | `SelectSheetWriteHandler` |
| 字典校验 | `@InDict` |

## 2. 代码示例

### 2.1 定义 Excel VO

```java
@Data
public class UserExcelVO {
    @ExcelProperty("用户名")
    private String username;

    @ExcelProperty("昵称")
    private String nickname;

    @ExcelProperty(value = "状态", converter = DictConvert.class)
    @DictFormat("user_status")
    private Integer status;
}
```

### 2.2 导出 Excel

```java
@GetMapping("/export")
public void exportUsers(HttpServletResponse response) throws IOException {
    List<UserExcelVO> data = userService.listUsers();
    // 写出到 response
    ExcelUtils.write(response, "用户列表.xlsx", "Sheet1", UserExcelVO.class, data);
}
```

### 2.3 导入 Excel

```java
@PostMapping("/import")
public CommonResult<Boolean> importUsers(@RequestParam("file") MultipartFile file) {
    List<UserImportVO> data = ExcelUtils.read(file, UserImportVO.class);
    userService.importUsers(data);
    return success(true);
}
```

## 3. 关键要点总结

- **yudao 用 EasyExcel**（阿里开源，性能优于 Apache POI）
- **`ExcelUtils`** 简化导入导出
- **字典转换** 通过 `Converter` 接口
- **数据校验** 用 `@InDict` 注解
- **多级表头、合并单元格** 全部支持

---

**文档版本**：v1.0
**最后更新**：2026-07-13
