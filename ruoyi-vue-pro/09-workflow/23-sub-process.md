# 5.3 子流程与调用活动

> 理解 BPMN 中的"子流程"（Sub-Process）和"调用活动"（Call Activity），以及在 ruoyi 中的应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"子流程"（Sub-Process）和"调用活动"（Call Activity）
- 知道 ruoyi 在 `ChildProcessConvert` 中如何转换子流程节点
- 理解"子流程"的"流程实例-子流程实例"嵌套关系
- 知道 ruoyi 提供的"子流程"业务场景

## 📚 前置知识

- BPMN 基础（详见 [BPMN](./01-bpmn.md)）
- 启动流程（详见 [启动流程](./15-start-process.md)）
- 多实例（详见 [多实例](./21-multi-instance.md)）

## 1. 核心概念

### 1.1 子流程 vs 调用活动

| 维度 | 子流程（Sub-Process） | 调用活动（Call Activity） |
|------|---------------------|--------------------------|
| **定义位置** | 在**当前** BPMN 文件中 | 在**外部** BPMN 文件中 |
| **实例** | 共享**同一个** ProcessInstance | 创建**独立**的 ProcessInstance |
| **数据传递** | 同 execution，**变量共享** | 通过 `inParameters` / `outParameters` 传参 |
| **可重用** | ❌ 不可重用 | ✅ 同一子流程可被多个流程调用 |
| **应用** | 把大流程拆为内嵌模块 | 复用通用流程（如"通用审批"） |

### 1.2 BPMN 表示

**子流程**（内嵌）：
```xml
<subProcess id="sub1" name="子流程">
    <startEvent id="subStart"/>
    <userTask id="subTask"/>
    <endEvent id="subEnd"/>
    <sequenceFlow id="f1" sourceRef="subStart" targetRef="subTask"/>
    <sequenceFlow id="f2" sourceRef="subTask" targetRef="subEnd"/>
</subProcess>
```

**调用活动**（外部）：
```xml
<callActivity id="callCommon" name="调用通用审批"
              calledElement="common-approve">
    <extensionElements>
        <flowable:in source="totalAmount" target="amount"/>
        <flowable:out source="result" target="finalResult"/>
    </extensionElements>
</callActivity>
```

### 1.3 ruoyi 的"子流程"实现

ruoyi 的简化模型支持**子流程节点**（`ChildProcessConvert`），作用：
- 把通用模块（如"通用审批"）**抽象为子流程**
- 在主流程中通过节点引用

**注意**：ruoyi 的"子流程"**实际上是 Call Activity**（引用另一个已部署的流程）。

## 2. 代码示例

### 2.1 子流程 BPMN（嵌入式）

```xml
<process id="main" name="主流程" isExecutable="true">
    <startEvent id="start"/>
    <subProcess id="sub1" name="材料收集">
        <userTask id="collect" name="收集材料"/>
        <userTask id="verify" name="验证材料"/>
        <sequenceFlow sourceRef="collect" targetRef="verify"/>
    </subProcess>
    <userTask id="approve" name="审批"/>
    <endEvent id="end"/>

    <sequenceFlow sourceRef="start" targetRef="sub1"/>
    <sequenceFlow sourceRef="sub1" targetRef="approve"/>
    <sequenceFlow sourceRef="approve" targetRef="end"/>
</process>
```

### 2.2 调用活动 BPMN（外部）

```xml
<!-- 主流程 -->
<process id="main">
    <callActivity id="callCommon" name="调用通用审批"
                  calledElement="common-approve">
        <extensionElements>
            <flowable:in source="applicant" target="userId"/>
            <flowable:out source="result" target="approveResult"/>
        </extensionElements>
    </callActivity>
</process>

<!-- 子流程 common-approve 是独立的 BPMN 文件 -->
```

### 2.3 常见错误：子流程与调用活动混淆

```xml
<!-- ❌ 错误：用子流程引用外部 BPMN（Flowable 不支持） -->
<subProcess id="sub1" name="外部流程" triggeredByEvent="false">
    <!-- 子流程必须是内嵌的，不能引用外部文件 -->
</subProcess>

<!-- ✅ 正确：用 callActivity 引用外部 BPMN -->
<callActivity id="call1" name="调用外部流程" calledElement="external-key">
</callActivity>
```

## 3. 关键要点总结

- 子流程（SubProcess）：内嵌在当前 BPMN 中，**变量共享**
- 调用活动（CallActivity）：引用外部 BPMN，**独立 ProcessInstance**
- ruoyi 的"子流程"**实际是 CallActivity**
- `calledElement` 指定被调用的流程 key
- `flowable:in` / `flowable:out` 实现变量映射
- ruoyi 用 `ChildProcessConvert` 把简化节点翻译为 CallActivity

---

**文档版本**：v1.0
**最后更新**：2026-07-13
