# 1.1.9 Chain-of-Thought 提示

> 通过任务分解、可验证中间产物和工具辅助提升复杂问题表现，而不是把隐藏推理当作可靠答案。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Chain-of-Thought（CoT）为何可能改善多步任务
- 区分 zero-shot CoT、few-shot CoT、自洽采样和结构化分解
- 知道何时应要求简短依据或可验证步骤，而非暴露内部推理
- 为计算、规划和生成任务设计“分解—执行—验证”流程
- 能看懂 dify 如何把一个复杂生成任务拆成多次 LLM 调用

## 📚 前置知识

- [模型参数](./04-model-parameters.md)
- [LLM 局限](./05-llm-limitations.md)
- Prompt 角色与基础写法（详见 [Prompt 基础](./08-prompt-basics.md)）
- 外部基础：基本概率和软件验证思维

## 1. 核心概念

### 1.1 CoT 的形式与适用场景

Chain-of-Thought 是让模型在得到最终答案前进行中间推理或任务分解的提示方法。经典形式包括：

- **Zero-shot CoT**：给出“分步骤解决”等简短指令。
- **Few-shot CoT**：提供带中间步骤的示例，教模型模仿推理结构。
- **Self-consistency**：采样多条候选路径，对最终答案投票或用验证器选择。
- **Least-to-most**：先拆子问题，再按依赖顺序逐个解决。

它更适合数学、多约束规划、复杂分类或代码分析，不适合简单查事实、低延迟分类等任务。CoT 会增加输出 token、延迟和成本，而且一条看似连贯的推理链仍可能是事后编造，不能当作事实证明。

### 1.2 从“展示思维”转向“可验证推理”

生产系统应关注答案是否可检查，而不是依赖模型输出冗长的内部思维。更稳健的提示模式是：

1. 明确任务、约束和成功标准。
2. 要求输出可验证的中间产物，如公式、计划、证据 ID 或测试结果。
3. 让工具执行算术、查询和代码验证。
4. 最终只返回结论、简短依据与验证状态。

对于支持内部推理或 reasoning 的模型，不应通过提示索取隐藏的原始思维过程。可以请求“简洁解释”“关键假设”“可复现步骤”或“引用证据”，也可以使用供应商明确提供的推理摘要能力。这样既能辅助审计，也避免把未经验证的自然语言推理误当作真实过程。

## 2. 代码示例

### 2.1 用“计划—执行—校验”替代一条超长提示

```python
# 文件：verified_reasoning.py
from collections.abc import Callable


def solve_with_verification(
    problem: str,
    generate: Callable[[str], str],
    verify: Callable[[str, str], bool],
) -> str:
    plan_prompt = (
        "把问题拆成最多 4 个可验证步骤。只输出编号计划，不给最终答案。\n"
        f"问题：{problem}"
    )
    plan = generate(plan_prompt)

    answer_prompt = (
        "依据计划解决问题。输出 JSON，字段为 answer、assumptions、checks。"
        "不要输出隐藏思维，只给可复现的关键依据。\n"
        f"问题：{problem}\n计划：{plan}"
    )
    candidate = generate(answer_prompt)
    if not verify(problem, candidate):
        repair_prompt = (
            "下面候选答案未通过外部校验。修正答案并保持同一 JSON 格式。\n"
            f"问题：{problem}\n候选：{candidate}"
        )
        candidate = generate(repair_prompt)
    return candidate


# generate 可接入任意 LLM，verify 应接入 JSON Schema、计算器或业务规则。
```

**说明**：该函数把复杂任务拆成两个模型阶段，并把真实性判断交给外部验证器。计划是可控的中间产物，不要求模型泄露或声称展示其隐藏内部推理。

## 3. 关键要点总结

- CoT 可能改善多步推理，但会增加 token、延迟和成本
- 自然语言推理链可能同样出错，不能自动视作证据
- 生产环境更应输出关键依据、假设、证据和验证结果
- 将任务拆成多次调用能获得可重试、可测试的中间产物
- dify 的规则生成通过分阶段调用实现应用级“分解—执行”

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
