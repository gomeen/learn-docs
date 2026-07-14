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

## 3. ruoyi 仓库源码解读

### 3.1 ExcelUtils

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-excel/`
**核心代码**（节选）：

```java
public class ExcelUtils {
    public static <T> void write(HttpServletResponse response, String filename, String sheetName,
                                  Class<T> head, List<T> data) throws IOException {
        // 1. 设置响应头
        response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        response.setCharacterEncoding("utf-8");
        response.setHeader("Content-disposition", "attachment;filename=" + URLEncoder.encode(filename, "UTF-8"));

        // 2. 用 EasyExcel 写出
        EasyExcel.write(response.getOutputStream(), head)
                .sheet(sheetName)
                .doWrite(data);
    }

    public static <T> List<T> read(MultipartFile file, Class<T> head) throws IOException {
        return EasyExcel.read(file.getInputStream(), head, null)
                .sheet()
                .doReadSync();
    }
}
```

### 3.2 DictConvert（字典翻译）

```java
public class DictConvert implements Converter<Integer> {
    @Override
    public Integer convertToJavaData(ReadCellData cellData, ExcelContentProperty contentProperty,
                                      GlobalConfiguration globalConfiguration) {
        // 导入：把 Excel 中的"正常"反序列化为 1
        String label = cellData.getStringValue();
        return DictFrameworkUtils.parseDictData("user_status", label);
    }

    @Override
    public WriteCellData<String> convertToExcelData(Integer value, ExcelContentProperty contentProperty,
                                                     GlobalConfiguration globalConfiguration) {
        // 导出：把 1 翻译成"正常"
        String label = DictFrameworkUtils.getDictDataLabel("user_status", value);
        return new WriteCellData<>(label);
    }
}
```

### 3.3 @InDict 校验

```java
public @interface InDict {
    String value();
}
```

```java
@Data
public class UserImportVO {
    @ExcelProperty("状态")
    @InDict("user_status")  // 校验值是否在字典中
    private String status;
}
```

**配合 `InDictValidator`**：

```java
public class InDictValidator implements ConstraintValidator<InDict, String> {
    @Override
    public boolean isValid(String value, ConstraintValidatorContext context) {
        if (value == null) return true;
        DictDataSimpleDO dict = DictFrameworkUtils.getDictData(inDict.value(), value);
        return dict != null;
    }
}
```

## 4. 关键要点总结

- **yudao 用 EasyExcel**（阿里开源，性能优于 Apache POI）
- **`ExcelUtils`** 简化导入导出
- **字典转换** 通过 `Converter` 接口
- **数据校验** 用 `@InDict` 注解
- **多级表头、合并单元格** 全部支持

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中实现"用户列表"的 Excel 导出（包含字典翻译）。

### 练习 2：进阶

实现"用户导入"功能：上传 Excel → 解析 → 批量插入 DB。

### 练习 3：挑战（选做）

实现"大数据量导入"：异步处理 + 进度条 + 失败行号记录。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-excel/`
- EasyExcel 文档：https://easyexcel.opensource.alibaba.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
