import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .llm_client import is_live
from .analyzer import generate_report

app = FastAPI(title="数据报告自动化助手")

class ReportRequest(BaseModel):
    csv_text: str

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
