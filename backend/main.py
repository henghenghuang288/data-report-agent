import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .llm_client import is_live
from .analyzer import generate_report

app = FastAPI(title="数据报告自动化助手")

class ReportRequest(BaseModel):
    csv_text: str

@app.get("/api/info")
def info():
    """项目信息接口——面试官打开API第一眼就能看到这是什么。"""
    return {
        "name": "数据报告自动化助手",
        "name_en": "Data Report Automation",
        "version": "1.0.0",
        "description": "CSV数据→Python精确统计→AI解读趋势异常建议",
        "description_en": "CSV → Python computes stats accurately → LLM writes findings (separation of calculation and language)",
        "architecture": "calculation-language separation, Python stats + LLM interpretation",
        "github": "https://github.com/henghenghuang288/data-report-agent",
        "endpoints": [
                "/api/health",
                "/api/report"
        ]
}


@app.get("/api/health")
def health():
    return {"status": "ok", "live_mode": is_live()}

@app.post("/api/report")
async def report(body: ReportRequest):
    if not body.csv_text.strip():
        raise HTTPException(status_code=400, detail="请粘贴 CSV 数据")
    try:
        return await generate_report(body.csv_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
