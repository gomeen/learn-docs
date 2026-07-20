# 1.1.5 LLM 能力边界与幻觉

> 把 LLM 当作概率生成器而非事实数据库，学会用证据、验证和安全边界构建可靠应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释幻觉为何是生成式模型的内在风险而非单一程序错误
- 区分知识缺失、上下文冲突、推理错误和工具失败
- 识别时效性、精确计算、长上下文和安全方面的能力边界
- 设计检索、引用、结构校验与人工复核等缓解措施
- 能看懂 dify 在 LLM 输出不稳定时采用的解析与降级逻辑

## 📚 前置知识

- [01-llm-overview.md](./01-llm-overview.md)
- [03-tokens-context.md](./03-tokens-context.md)
- [04-model-parameters.md](./04-model-parameters.md)
- 外部基础：基本概率、JSON 解析和软件测试思想

## 1. 核心概念

### 1.1 幻觉从哪里产生

LLM 的训练目标通常是预测在当前上下文中“更可能出现的下一个 token”，而不是逐条查询经过验证的事实数据库。一个回答可以语言流畅、格式正确，却在事实层面错误。常见来源包括：

- **知识缺失或过时**：训练数据没有相关事实，或事实已经变化。
- **提示诱导**：问题包含错误前提，模型顺着前提继续补全。
- **检索噪声**：RAG 找到无关、冲突或被恶意污染的材料。
- **推理与计算错误**：多步约束丢失、算术错误、代码未实际执行。
- **输出压力**：提示要求“必须回答”，使模型不愿表达不确定性。

低 temperature 通常只能降低随机变化，不能把错误知识变成正确事实。更大的模型和更长上下文也只会改变错误概率，不会消除幻觉。

### 1.2 能力边界与可靠性工程

应按照失败成本选择防护层，而不是期待一个“完美提示词”：

| 风险 | 推荐措施 |
| --- | --- |
| 最新事实 | 检索或调用权威实时 API，记录来源时间 |
| 关键结论 | 要求引用，并校验引用是否支持结论 |
| 计算与代码 | 使用计算器/代码执行，运行测试验证 |
| 结构化输出 | JSON Schema、解析器、业务规则校验 |
| 高风险决策 | 人工复核、权限控制、审计与可回滚操作 |
| 不确定输入 | 允许澄清、拒答或明确标记未知 |

长上下文同样有边界：材料“放进窗口”不等于模型一定正确使用。信息可能被埋在中间、与其他段落冲突或超过模型有效注意范围。可靠应用应保留原始证据、输出置信信号和失败状态，并使用真实业务样本持续评测。

## 2. 代码示例

### 2.1 对模型 JSON 输出进行证据校验

```python
# 文件：grounded_answer.py
import json
from typing import TypedDict


class Answer(TypedDict):
    answer: str
    evidence_ids: list[str]
    unknown: bool


def validate_answer(raw: str, evidence: dict[str, str]) -> Answer:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("response must be a JSON object")

    answer = parsed.get("answer")
    evidence_ids = parsed.get("evidence_ids")
    unknown = parsed.get("unknown")
    if not isinstance(answer, str) or not isinstance(evidence_ids, list) or not isinstance(unknown, bool):
        raise ValueError("response fields have invalid types")
    if not all(isinstance(item, str) and item in evidence for item in evidence_ids):
        raise ValueError("response cites unknown evidence")
    if not unknown and not evidence_ids:
        raise ValueError("factual answer must cite evidence")
    return {"answer": answer, "evidence_ids": evidence_ids, "unknown": unknown}


sources = {"doc-1": "退款申请必须在购买后 7 天内提交。"}
print(validate_answer('{"answer":"期限是 7 天","evidence_ids":["doc-1"],"unknown":false}', sources))
```

**说明**：校验器不能证明回答语义一定正确，但能阻止“无证据却装作确定”和“引用不存在来源”两类常见失败。生产环境还应检查引用片段是否真的支持结论。

## 3. 关键要点总结

- LLM 优化的是序列生成概率，不是真实性证明
- temperature 降低不能消除幻觉，长上下文也不保证信息被正确使用
- 可靠系统需要证据、解析、验证、评测、权限和人工复核共同工作
- LLM 输出应按不可信外部输入处理
- dify 对非关键生成任务采用修复、过滤和空结果降级

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
