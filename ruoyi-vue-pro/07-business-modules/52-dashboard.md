# 7.7.7 大屏设计器

> 理解 ruoyi 大屏设计器的设计与实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 大屏模块的设计
- 理解数据可视化大屏的架构
- 学会设计自定义大屏
- 能扩展大屏功能

## 📚 前置知识

- 报表（详见 [报表](./51-report.md)）
- ECharts / DataV 基础
- WebSocket 基础（详见 [WebSocket Starter](../03-spring-boot-starters/46-websocket.md)）

## 1. 核心概念

### 1.1 什么是大屏？

数据大屏（Dashboard）是一种**展示型应用**，通常用于：
- 运营监控中心
- 实时数据展示
- 指挥调度中心
- 业务概览

**特点**：
- 全屏展示
- 多种图表组合
- 实时刷新
- 视觉效果震撼

### 1.2 大屏架构

```
[后端] --(WebSocket / SSE)--> [前端大屏]
   ↑
[数据源: MySQL/Redis/IoT]
```

**核心组件**：
- 大屏布局：画布 + 组件
- 数据源：SQL/API
- 图表组件：折线图、柱状图、地图
- 实时刷新：定时器 / WebSocket

### 1.3 ruoyi 大屏设计器

ruoyi 通常集成 **GoView** 或 **DataV** 作为大屏工具。

## 2. 代码示例

### 2.1 大屏定义

```java
@Data
public class DashboardDO {
    private Long id;
    private String name;          // 大屏名
    private String content;       // JSON 配置
    private String status;
    private Long creator;
    private LocalDateTime createTime;
}
```

### 2.2 大屏管理接口

```java
@PostMapping("/create")
public CommonResult<Long> createDashboard(@Valid @RequestBody DashboardSaveReqVO createReqVO) {
    return success(dashboardService.createDashboard(createReqVO));
}

@GetMapping("/list")
public CommonResult<List<DashboardRespVO>> getDashboardList() {
    return success(dashboardService.getDashboardList());
}
```

### 2.3 数据查询

```java
@PostMapping("/query")
public CommonResult<Object> queryData(@Valid @RequestBody DashboardDataQueryReqVO reqVO) {
    return success(dashboardService.queryData(reqVO));
}

public Object queryData(DashboardDataQueryReqVO reqVO) {
    // 1. 解析 SQL
    String sql = parseSql(reqVO.getSql());
    // 2. 执行查询
    List<Map<String, Object>> data = jdbcTemplate.queryForList(sql);
    // 3. 转换为图表数据
    return convertToChartData(data, reqVO.getChartType());
}
```

### 2.4 实时数据

```java
@Scheduled(fixedRate = 5000)  // 5 秒一次
public void pushRealtimeData() {
    // 1. 查询最新数据
    Map<String, Object> data = queryRealtimeData();
    // 2. 推送给所有大屏
    webSocketSenderApi.sendObject(UserTypeEnum.ADMIN.getValue(),
                                   "dashboard-update", data);
}
```

## 3. 关键要点总结

- 大屏由"画布 + 组件"组成
- 组件类型：图表、数字、表格、地图
- 数据源：SQL 查询 / API 调用
- 实时数据通过 WebSocket 推送
- 设计器支持拖拽布局

---

**文档版本**：v1.0
**最后更新**：2026-07-13
