"""
数据报告自动化

场景:运营/销售拿到一份数据表,不知道怎么看,需要快速得到结论。
流程:
  1. 上传或粘贴 CSV 数据
  2. 代码层先做统计计算(不让 LLM 算数,LLM 算数不可靠这是已知的)
  3. 把计算好的统计摘要喂给 LLM,让它做"解读+趋势+异常+建议"
  4. 返回结构化报告

关键设计:数字计算全在 Python 里做(准确),LLM 只做"读懂数字、写结论"(擅长)。
这是和 doc-qa-agent 里安全计算器同一个设计原则的延伸:
让每个组件只干它擅长的事,不让 LLM 去做它容易出错的事。
"""

import csv
import io
import json
import time
from typing import Any

from .llm_client import call_llm, is_live

ANALYST_SYSTEM = (
    "你是一名数据分析师,擅长从数字里找出有意义的结论。"
    "用户会给你一份已经计算好的数据摘要(不是原始数据),请基于这些数字写分析报告。"
    "不要重复罗列数字,要说明这些数字意味着什么、趋势是什么、有没有异常、给运营什么建议。"
    "只输出一个 JSON 对象(不要 markdown 代码块标记),字段:"
    "title(字符串,报告标题), "
    "key_findings(数组,3-5 条最重要的发现,每条是一句话结论), "
    "trends(字符串,趋势分析), "
    "anomalies(数组,异常或值得关注的地方,没有则返回空数组), "
    "recommendations(数组,2-4 条可操作的建议), "
    "summary(字符串,给高管看的一句话总结)。"
)


def parse_csv(text: str) -> tuple[list[str], list[dict]]:
    """解析 CSV 文本,返回 (列名列表, 数据行列表)。容错处理常见编码和格式问题。"""
    text = text.strip()
    if not text:
        raise ValueError("数据为空")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV 没有数据行")
    return list(reader.fieldnames or []), rows


def compute_stats(columns: list[str], rows: list[dict]) -> dict[str, Any]:
    """
    对每一列做统计:数值列算 sum/mean/max/min/增长率,文本列算频率分布。
    结果喂给 LLM 做解读。数字在这里算好,LLM 只负责"读懂数字写结论"。
    """
    stats: dict[str, Any] = {
        "row_count": len(rows),
        "columns": columns,
        "column_stats": {},
    }

    for col in columns:
        values = [r.get(col, "").strip() for r in rows]
        # 尝试当数值列处理
        numeric = []
        for v in values:
            try:
                numeric.append(float(v.replace(",", "").replace("¥", "").replace("$", "").replace("%", "")))
            except (ValueError, AttributeError):
                pass

        if len(numeric) >= len(values) * 0.6:  # 60% 以上能解析为数字,认为是数值列
            s = {
                "type": "numeric",
                "count": len(numeric),
                "sum": round(sum(numeric), 2),
                "mean": round(sum(numeric) / len(numeric), 2),
                "max": max(numeric),
                "min": min(numeric),
            }
            # 计算首尾增长率(如果是时序数据,第一行到最后一行的变化)
            if len(numeric) >= 2:
                first, last = numeric[0], numeric[-1]
                if first != 0:
                    s["first_to_last_change_pct"] = round((last - first) / abs(first) * 100, 1)
            stats["column_stats"][col] = s
        else:
            # 文本列:算频率分布,取前5
            freq: dict[str, int] = {}
            for v in values:
                if v:
                    freq[v] = freq.get(v, 0) + 1
            top5 = sorted(freq.items(), key=lambda x: -x[1])[:5]
            stats["column_stats"][col] = {
                "type": "categorical",
                "unique_count": len(freq),
                "top_values": [{"value": k, "count": v} for k, v in top5],
            }

    return stats


def _offline_report(stats: dict) -> dict:
    """无 key 时的离线模拟报告,基于统计数据生成基础分析。"""
    numeric_cols = {k: v for k, v in stats["column_stats"].items() if v["type"] == "numeric"}
    findings = [f"数据共 {stats['row_count']} 行,{len(stats['columns'])} 列"]
    for col, s in list(numeric_cols.items())[:3]:
        findings.append(f"{col}:均值 {s['mean']},最大 {s['max']},最小 {s['min']}")
        if "first_to_last_change_pct" in s:
            direction = "上涨" if s["first_to_last_change_pct"] > 0 else "下降"
            findings.append(f"{col} 首尾变化:{direction} {abs(s['first_to_last_change_pct'])}%(离线初判)")

    return {
        "title": "数据概况报告(离线模式)",
        "key_findings": findings[:5],
        "trends": "离线模式仅做统计计算,趋势解读需开启智能模式。",
        "anomalies": [],
        "recommendations": ["开启智能模式(配置 DEEPSEEK_API_KEY)获得完整 AI 分析报告"],
        "summary": f"数据集包含 {stats['row_count']} 条记录,{len(numeric_cols)} 个数值字段,离线模式下完成基础统计。",
        "_offline": True,
    }


async def generate_report(csv_text: str) -> dict[str, Any]:
    t0 = time.perf_counter()

    columns, rows = parse_csv(csv_text)
    stats = compute_stats(columns, rows)

    if not is_live():
        report = _offline_report(stats)
        return {
            "mode": "offline_simulation",
            "stats": stats,
            "report": report,
            "total_latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "total_tokens": None,
        }

    # 在线模式:把统计摘要喂给 LLM 做解读
    stats_summary = json.dumps(stats, ensure_ascii=False, indent=2)
    user_prompt = f"以下是一份数据集的统计摘要,请分析并写出报告:\n\n{stats_summary}"
    res = await call_llm(ANALYST_SYSTEM, user_prompt, max_tokens=1200)

    cleaned = res["text"].replace("```json", "").replace("```", "").strip()
    try:
        report = json.loads(cleaned)
    except json.JSONDecodeError:
        report = {
            "title": "数据报告",
            "key_findings": ["模型输出解析失败,请查看原始统计数据"],
            "trends": res["text"],
            "anomalies": [],
            "recommendations": [],
            "summary": "解析失败,请查看 stats 字段中的原始统计数据",
        }

    return {
        "mode": f"live_{res['provider']}",
        "stats": stats,
        "report": report,
        "total_latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        "total_tokens": res["usage"]["total_tokens"] if res.get("usage") else None,
    }
