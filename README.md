# 数据报告自动化助手

粘贴 CSV 数据,自动生成分析报告:关键发现、趋势、异常、建议。

## 核心设计

**数字在代码里算,结论让 AI 写。** LLM 算数不可靠是已知问题,所以统计计算(均值、增长率、异常检测)全在 Python 里完成,LLM 只拿计算好的摘要做"读懂数字、写结论"——让每个组件只干它擅长的事。

## 五个项目对比

| 项目 | 形态 | 场景 |
|------|------|------|
| doc-qa-agent | 问答型 | 基于文档精确回答 |
| ecom-agent-crew | 协作型 | 多角色接力生成内容 |
| contract-review-agent | 审查型 | 逐条标记风险 |
| resume-screener | 评估型 | 批量对比打分排序 |
| data-report-agent(本项目) | 分析型 | 数据统计+AI解读 |

## 运行

```bash
pip install -r requirements.txt
export DEEPSEEK_API_KEY=sk-xxxx
uvicorn backend.main:app --reload
```
