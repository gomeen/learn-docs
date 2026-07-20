# 7.7.6 报表：积木报表

> 理解 ruoyi 报表模块的设计与实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 报表模块的设计
- 理解积木报表（JimuReport）的集成
- 学会设计自定义报表
- 能扩展报表功能

## 📚 前置知识

- SQL 基础
- 报表设计基础
- MVC 分层（详见 [MVC 分层](./02-mvc-layers.md)）

## 1. 核心概念

### 1.1 报表类型

| 类型 | 工具 | 适用 |
|------|------|------|
| 普通报表 | Excel 导出 | 数据导出 |
| 可视化报表 | ECharts | 仪表盘 |
| 填报报表 | 积木报表 | 用户填写 |
| 大屏报表 | DataV / JimuBI | 数据大屏 |

### 1.2 积木报表（JimuReport）

**积木报表**是一个开源的报表设计器：
- 在线拖拽设计
- 支持 SQL 数据源
- 支持各种图表
- 支持打印、导出

### 1.3 ruoyi 报表模块结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-report/`

```
yudao-module-report/
├── controller/admin/    # 报表管理
├── dal/dataobject/      # 报表定义
└── service/
```

## 2. 代码示例

### 2.1 报表管理

```java
@PostMapping("/create")
public CommonResult<Long> createReport(@Valid @RequestParam("name") String name,
                                        @RequestParam("content") String content) {
    return success(reportService.createReport(name, content));
}

@GetMapping("/list")
public CommonResult<List<ReportRespVO>> getReportList() {
    return success(reportService.getReportList());
}
```

### 2.2 报表设计器

```java
@Data
public class ReportDO {
    private Long id;
    private String name;        // 报表名
    private String content;     // 报表 JSON 配置
    private String status;
    private Long creator;
    private LocalDateTime createTime;
}
```

### 2.3 数据源配置

```yaml
spring:
  datasource:
    # 业务数据源
    url: jdbc:mysql://127.0.0.1:3306/ruoyi-vue-pro
    # 报表数据源（可独立）
    bi:
      url: jdbc:mysql://bi-server:3306/bi
```

### 2.4 报表预览

```java
@GetMapping("/preview")
public void preview(@RequestParam("id") Long id, HttpServletResponse response) {
    ReportDO report = reportMapper.selectById(id);
    // 调用积木报表渲染
    jimuReport.render(report.getContent(), response);
}
```

## 3. 关键要点总结

- ruoyi 集成积木报表作为报表工具
- 报表内容是 JSON 配置
- 通过 SQL 查询数据
- 支持导出、打印、分页
- 前端通过 iframe 嵌入报表

---

**文档版本**：v1.0
**最后更新**：2026-07-13
