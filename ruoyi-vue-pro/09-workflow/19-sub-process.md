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
- 启动流程（详见 [启动流程](./12-start-process.md)）
- 多实例（详见 [多实例](./17-multi-instance.md)）

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

## 3. ruoyi 仓库源码解读

### 3.1 SimpleModelUtils 中的 ChildProcessConvert

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/SimpleModelUtils.java`
**核心代码**（行 41-50）：

```java
static {
    List<NodeConvert> converts = asList(new StartNodeConvert(), new EndNodeConvert(),
            new StartUserNodeConvert(), new ApproveNodeConvert(), new CopyNodeConvert(), new TransactorNodeConvert(),
            new DelayTimerNodeConvert(), new TriggerNodeConvert(),
            new ConditionBranchNodeConvert(), new ParallelBranchNodeConvert(), new InclusiveBranchNodeConvert(), new RouteBranchNodeConvert(),
            new ChildProcessConvert());  // 子流程转换器
    converts.forEach(convert -> NODE_CONVERTS.put(convert.getType(), convert));
}
```

**解读**：
- 第 48 行：`ChildProcessConvert` 是 12 个节点转换器之一
- 它把 ruoyi 的"简化子流程节点"翻译为 BPMN 的 `CallActivity`
- **关键设计**：每个转换器**只关注一种节点**，关注点分离

### 3.2 ChildProcessConvert 的实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/SimpleModelUtils.java`（内部类）
**核心代码**（推断）：

```java
class ChildProcessConvert implements NodeConvert {
    @Override
    public BpmSimpleModelNodeTypeEnum getType() {
        return BpmSimpleModelNodeTypeEnum.CHILD_PROCESS;
    }

    @Override
    public FlowElement convert(BpmSimpleModelNodeVO node, ConversionContext context) {
        CallActivity callActivity = new CallActivity();
        callActivity.setId(node.getId());
        callActivity.setName(node.getName());

        // calledElement：引用的子流程 key
        callActivity.setCalledElement(node.getChildProcessKey());

        // 配置 in/out 参数
        if (node.getInVariables() != null) {
            // 添加 flowable:in
        }
        if (node.getOutVariables() != null) {
            // 添加 flowable:out
        }
        return callActivity;
    }
}
```

**解读**：
- 转换为 `CallActivity`（不是 SubProcess）
- `calledElement` 引用外部已部署的流程 key
- 简化配置：前端只需配置 `childProcessKey`
- **关键设计**：ruoyi 的"子流程"实际是**跨流程复用**机制

### 3.3 实际案例：子流程的变量传递

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/listener/BpmCallActivityListener.java`
**核心代码**（推断）：

```java
@Component
public class BpmCallActivityListener implements ExecutionListener {
    @Override
    public void notify(DelegateExecution execution) {
        // 监听 callActivity 的启动/结束事件
        // 1. 主流程 → 子流程：拷贝 inVariables
        // 2. 子流程 → 主流程：合并 outVariables
    }
}
```

**解读**：
- ruoyi 用监听器在 callActivity 边界做"变量传递"
- **关键设计**：变量映射在业务层（listener）实现，**BPMN 文件保持简洁**

## 4. 关键要点总结

- 子流程（SubProcess）：内嵌在当前 BPMN 中，**变量共享**
- 调用活动（CallActivity）：引用外部 BPMN，**独立 ProcessInstance**
- ruoyi 的"子流程"**实际是 CallActivity**
- `calledElement` 指定被调用的流程 key
- `flowable:in` / `flowable:out` 实现变量映射
- ruoyi 用 `ChildProcessConvert` 把简化节点翻译为 CallActivity

## 5. 练习题

### 练习 1：基础（必做）

回答：
1. 子流程和调用活动的区别？
2. ruoyi 的"子流程"实际是哪种？
3. 变量如何从主流程传递到子流程？

**参考答案**：见 `solutions/19-sub-process.md`

### 练习 2：进阶

阅读 `ChildProcessConvert` 完整实现，看它如何处理 `inVariables` 和 `outVariables` 的转换。

### 练习 3：挑战（选做）

设计一个"通用审批"子流程（含 3 级审批：经理 → 总监 → CEO），然后用 callActivity 在主流程中调用它。写出主流程和子流程的 BPMN XML。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/SimpleModelUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/listener/BpmCallActivityListener.java`
- BPMN 2.0 CallActivity 规范：https://www.omg.org/spec/BPMN/2.0/#P1468

---

**文档版本**：v1.0
**最后更新**：2026-07-13
