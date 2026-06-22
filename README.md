# Data Report Automation

> 🇨🇳 [中文版见下方](#中文说明)

Paste CSV data, get an automated analysis report: key findings, trend analysis, anomalies, and actionable recommendations.

## Core Design Principle: Separate Calculation from Language

LLMs are unreliable at arithmetic. The solution isn't to hope they get it right — it's to not ask them to do math at all.

```
CSV input
    │
    ▼
[Python layer]  →  compute stats accurately
                   (mean, sum, max, min, growth %, per-column type detection)
    │
    ▼
[LLM layer]     →  read numbers, write conclusions
                   ("sales grew 56% — here's what that means for operations")
```

Each component does only what it's good at. The LLM never sees raw CSV — it sees a pre-computed summary.

This same principle appears in doc-qa-agent's safe calculator tool: arithmetic goes to code (AST-safe eval), language generation stays with the model.

## Offline Mode

Without an API key, Python still computes all statistics and returns them with basic labels. The calculation layer works independently of the language layer.

## Stack

Python · FastAPI · asyncio · DeepSeek/OpenAI-compatible · Docker

## Quick Start

```bash
pip install -r requirements.txt
export DEEPSEEK_API_KEY=sk-xxxx   # optional
uvicorn backend.main:app --reload
```

---

## 中文说明

粘贴 CSV 数据，自动生成分析报告：关键发现、趋势分析、异常、建议。

**核心设计：数字计算和语言生成分离。** AI 算数不可靠是公认问题，所以 Python 层负责把统计数字算准确，然后把计算好的摘要喂给 AI，让它只做"读懂数字、写结论"这件它擅长的事。这和 doc-qa-agent 里安全计算器工具的设计原则完全一致。
