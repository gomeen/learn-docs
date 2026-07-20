# 1.1 BPMN 2.0 规范

> 理解 BPMN 2.0（Business Process Model and Notation）规范，看懂 Flowable 流程定义 XML 文件。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 BPMN 2.0 规范的诞生背景与目标
- 识别 BPMN 五大基本元素：流对象、连接对象、数据、泳道、制品
- 读懂 `.bpmn20.xml` 文件中的节点（StartEvent、UserTask、EndEvent、SequenceFlow）
- 能看懂 ruoyi 中部署到 Flowable 的流程定义文件结构

## 📚 前置知识

- XML 基础语法
- Java 基础（了解 POJO、注解）
- Spring Boot 基础（详见 [IoC](../02-spring-boot/01-ioc.md)）
- Flowable 对象模型（详见 [Flowable 概念](./02-flowable-concepts.md)）

## 1. 核心概念

### 1.1 什么是 BPMN？

**BPMN**（Business Process Model and Notation，业务流程模型与标记法）是由 OMG（Object Management Group）维护的**流程建模标准**。当前主流版本是 **BPMN 2.0**，自 2011 年发布，已成为工作流引擎的事实标准。

**目标**：让业务分析师（画流程图）和开发人员（实现流程）使用**同一套图形化符号**沟通，避免沟通歧义。

```
业务分析师（Visio/draw.io 画图）  ── 同一套符号 ──>  开发人员（Flowable/Activiti 实现）
```

### 1.2 BPMN 五大基本元素

| 元素类型 | 描述 | 示例 |
|---------|------|------|
| **流对象（Flow Objects）** | 流程核心行为 | 事件（圆圈）、活动（圆角矩形）、网关（菱形） |
| **连接对象（Connecting Objects）** | 元素之间的连接 | 顺序流（实线箭头）、消息流（虚线）、关联（点线） |
| **数据（Data）** | 数据输入/输出 | 数据对象、数据存储、数据输入/输出 |
| **泳道（Swimlanes）** | 组织职责划分 | 池（Pool）、道（Lane） |
| **制品（Artifacts）** | 附加信息 | 组、文本注释 |

### 1.3 常用节点速查

| 节点 | 图形 | 含义 |
|------|------|------|
| StartEvent | 细边圆 | 流程开始 |
| EndEvent | 粗边圆 | 流程结束 |
| UserTask | 圆角矩形 | 人工审批任务 |
| ServiceTask | 圆角矩形（齿轮） | 自动执行任务（Java/Script/Http） |
| ExclusiveGateway | 菱形（X） | 排他网关：根据条件选一条分支 |
| ParallelGateway | 菱形（+） | 并行网关：多分支并发 |
| InclusiveGateway | 菱形（O） | 包容网关：满足条件的分支都走 |
| SequenceFlow | 实线箭头 | 节点间流转关系 |

### 1.4 BPMN 与 Flowable 的关系

- **BPMN 2.0 是规范**：定义"流程长什么样"
- **Flowable 是实现**：基于 BPMN 2.0 规范的 Java 引擎（类似实现还有 Activiti、Camunda）

```
BPMN 2.0 规范 ───>  Flowable 引擎（解析 XML → 运行时模型）
                  └─> Activiti 引擎（同源分支）
                  └─> Camunda 引擎（独立实现）
```

## 2. 代码示例

### 2.1 一个最简单的请假流程

```xml
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:flowable="http://flowable.org/bpmn"
             targetNamespace="http://bpmn.io/schema/bpmn"
             id="Definitions_1">

    <process id="leave" name="请假流程" isExecutable="true">
        <!-- 开始节点 -->
        <startEvent id="start"/>

        <!-- 第一个审批：直属领导 -->
        <userTask id="approve_leader" name="直属领导审批"/>

        <!-- 第二个审批：HR -->
        <userTask id="approve_hr" name="HR 审批"/>

        <!-- 结束节点 -->
        <endEvent id="end"/>

        <!-- 流转顺序 -->
        <sequenceFlow id="flow1" sourceRef="start" targetRef="approve_leader"/>
        <sequenceFlow id="flow2" sourceRef="approve_leader" targetRef="approve_hr"/>
        <sequenceFlow id="flow3" sourceRef="approve_hr" targetRef="end"/>
    </process>
</definitions>
```

**说明**：
- `process id="leave"`：定义一个可执行流程
- `<startEvent>` 起点 → `<userTask>` 审批 → `<endEvent>` 终点
- `<sequenceFlow>` 把节点串起来

### 2.2 加入排他网关的报销流程

```xml
<process id="expense" name="报销流程" isExecutable="true">
    <startEvent id="start"/>
    <userTask id="submit" name="提交报销"/>
    <exclusiveGateway id="amountCheck" name="金额判断"/>
    <userTask id="managerApprove" name="经理审批"/>
    <userTask id="ceoApprove" name="CEO 审批"/>
    <endEvent id="end"/>

    <sequenceFlow id="f1" sourceRef="start" targetRef="submit"/>
    <sequenceFlow id="f2" sourceRef="submit" targetRef="amountCheck"/>

    <!-- 条件分支 -->
    <sequenceFlow id="f3" sourceRef="amountCheck" targetRef="managerApprove">
        <conditionExpression xsi:type="tFormalExpression">
            <![CDATA[${amount <= 1000}]]>
        </conditionExpression>
    </sequenceFlow>
    <sequenceFlow id="f4" sourceRef="amountCheck" targetRef="ceoApprove">
        <conditionExpression xsi:type="tFormalExpression">
            <![CDATA[${amount > 1000}]]>
        </conditionExpression>
    </sequenceFlow>

    <sequenceFlow id="f5" sourceRef="managerApprove" targetRef="end"/>
    <sequenceFlow id="f6" sourceRef="ceoApprove" targetRef="end"/>
</process>
```

**说明**：
- 排他网关根据 `${amount}` 变量值决定走哪个分支
- `conditionExpression` 内是 Flowable EL 表达式（类似 SpEL）

### 2.3 常见错误：忘记设置 `isExecutable`

```xml
<!-- ❌ 错误：缺 isExecutable="true"，流程无法启动 -->
<process id="leave" name="请假流程">
    <startEvent id="start"/>
    ...
</process>

<!-- ✅ 正确 -->
<process id="leave" name="请假流程" isExecutable="true">
    ...
</process>
```

**原因**：BPMN 2.0 中 `<process>` 可以是"可执行"或"抽象（仅文档）"。Flowable 只会执行 `isExecutable="true"` 的流程。

## 3. 关键要点总结

- BPMN 2.0 是**行业标准**（非具体产品），Flowable/Activiti/Camunda 都是它的实现
- 三大核心节点：**事件**（圆）、**活动**（矩形）、**网关**（菱形）
- `<process isExecutable="true">` 标记流程是否可执行，缺此属性将无法启动
- 条件分支写在 `<sequenceFlow>` 的 `<conditionExpression>` 中，**EL 表达式语法**（`${varName}`）
- ruoyi 通过 `BpmnModelUtils` 封装 BPMN 操作，**业务层不直接接触 Flowable 原生 API**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
