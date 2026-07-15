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

## 3. ruoyi 仓库源码解读

### 3.1 报表模块结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-report/`

```
yudao-module-report/
├── src/main/java/.../report/
│   ├── controller/admin/
│   │   └── ReportController.java
│   ├── dal/
│   │   └── dataobject/
│   └── service/
└── src/main/resources/
    └── application.yml
```

### 3.2 报表 Controller

```java
@Tag(name = "管理后台 - 报表")
@RestController
@RequestMapping("/report")
@Validated
public class ReportController {

    @Resource
    private ReportService reportService;

    @PostMapping("/create")
    public CommonResult<Long> createReport(@Valid @RequestBody ReportSaveReqVO createReqVO) {
        return success(reportService.createReport(createReqVO));
    }

    @GetMapping("/list")
    public CommonResult<List<ReportRespVO>> getReportList() {
        return success(reportService.getReportList());
    }

    @GetMapping("/preview")
    public void preview(@RequestParam("id") Long id, HttpServletResponse response) {
        reportService.preview(id, response);
    }
}
```

### 3.3 报表数据源

积木报表通过 SQL 语句查询数据：

```json
{
  "sql": "SELECT DATE(create_time) AS date, COUNT(*) AS count FROM trade_order GROUP BY DATE(create_time)",
  "fields": [
    {"name": "date", "type": "date"},
    {"name": "count", "type": "int"}
  ]
}
```

## 4. 关键要点总结

- ruoyi 集成积木报表作为报表工具
- 报表内容是 JSON 配置
- 通过 SQL 查询数据
- 支持导出、打印、分页
- 前端通过 iframe 嵌入报表

## 5. 练习题

### 练习 1：基础（必做）

阅读 `ReportDO.java` 字段。

### 练习 2：进阶

阅读 `ReportServiceImpl.java`，理解报表存储和加载。

### 练习 3：挑战（选做）

设计"销售月报"：统计每月销售额、订单数、TOP10 商品。写出 SQL 和报表设计。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-report/`
- 积木报表：https://github.com/jeecgboot/JimuReport

---

**文档版本**：v1.0
**最后更新**：2026-07-13
