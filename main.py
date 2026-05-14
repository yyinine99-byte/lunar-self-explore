"""AI 自我探索工具 — FastAPI 服务入口。

提供两个核心 API：
- POST /api/chart  — 计算星盘/八字/星宿综合画像
- POST /api/chat   — 与 AI 对话（流式 SSE）
- GET  /           — 前端页面
"""

import datetime
import json
import uuid
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os

from chart_calculator import compute_chart
from bazi_calculator import compute_bazi
from star_database import get_mansion_by_lunar_date, get_mansion_by_moon_longitude
from lunar_calendar import solar_to_lunar
from ai_service import chat_stream, chat_non_stream
from rate_limiter import chat_limiter, chart_limiter

app = FastAPI(title="AI 自我探索工具", version="0.1.0")

# 静态文件
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ─── Request Models ───────────────────────────────────────────

class ChartRequest(BaseModel):
    birth_date: str       # "1990-05-20"
    birth_time: str        # "14:30"
    longitude: float       # 经度，如 116.4074
    latitude: float        # 纬度，如 39.9042
    gender: str = ""       # "male" / "female"
    timezone_offset: int = 8  # UTC偏移，默认+8（北京时间）


class ChatRequest(BaseModel):
    session_id: str
    message: str
    chart_data: dict
    history: Optional[list] = None


# ─── Routes ───────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """返回前端页面。"""
    html_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)


@app.post("/api/chart")
async def api_chart(request: Request, body: ChartRequest):
    """计算综合画像（星盘 + 八字 + 星宿）。"""
    # 限流
    client_ip = request.client.host if request.client else "unknown"
    if not chart_limiter.allow(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "请求太频繁，请稍后再试", "remaining": 0},
        )

    try:
        # 解析输入
        birth_date = datetime.date.fromisoformat(body.birth_date)
        time_parts = body.birth_time.split(":")
        birth_hour = int(time_parts[0]) if len(time_parts) > 0 else 12
        birth_minute = int(time_parts[1]) if len(time_parts) > 1 else 0

        # 转换为 UTC 时间
        local_dt = datetime.datetime(
            birth_date.year, birth_date.month, birth_date.day,
            birth_hour, birth_minute, 0
        )
        utc_dt = local_dt - datetime.timedelta(hours=body.timezone_offset)

        # 1. 计算星盘
        chart_result = compute_chart(
            birth_dt=utc_dt,
            lat=body.latitude,
            lon=body.longitude,
        )

        # 2. 计算八字
        bazi_result = compute_bazi(
            birth_date=birth_date,
            birth_hour=birth_hour,
            gender=body.gender,
        )

        # 3. 计算农历日期 → 星宿（农历月法）
        lunar = solar_to_lunar(birth_date)
        star_result = get_mansion_by_lunar_date(
            lunar_month=lunar["month"],
            lunar_day=lunar["day"],
        )

        # 3b. 用月亮实际黄经做天文校验
        moon_planet = next((p for p in chart_result["planets"] if p["name_en"] == "Moon"), None)
        if moon_planet:
            moon_lon = moon_planet["ecliptic_longitude"]
            star_result_astro = get_mansion_by_moon_longitude(moon_lon)
            # 将天文校验结果附带到返回中
            star_result["moon_lon_mansion"] = star_result_astro["name"]

        # 4. 组装响应
        combined = {
            "chart": chart_result,
            "bazi": bazi_result,
            "star_mansion": star_result,
            "lunar_date": f"农历{lunar['month']}月{lunar['day']}日",
        }

        return JSONResponse(content=combined)

    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": f"输入格式错误: {str(e)}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"计算失败: {str(e)}"})


@app.post("/api/chat")
async def api_chat(request: Request, body: ChatRequest):
    """AI 对话接口（流式 SSE）。"""
    # 限流
    client_ip = request.client.host if request.client else "unknown"
    if not chat_limiter.allow(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "请求太频繁，请稍后再试", "remaining": 0},
        )

    # 检查 API Key
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        # 无 API Key 时，返回错误
        return JSONResponse(
            status_code=503,
            content={"error": "AI 服务暂未配置，请联系管理员设置 DEEPSEEK_API_KEY"},
        )

    async def event_generator():
        try:
            async for chunk in chat_stream(
                chart_data=body.chart_data,
                user_message=body.message,
                history=body.history,
            ):
                yield chunk
        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat/sync")
async def api_chat_sync(request: Request, body: ChatRequest):
    """AI 对话接口（非流式，备用）。"""
    client_ip = request.client.host if request.client else "unknown"
    if not chat_limiter.allow(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "请求太频繁，请稍后再试"},
        )

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return JSONResponse(
            status_code=503,
            content={"error": "AI 服务暂未配置，请联系管理员设置 DEEPSEEK_API_KEY"},
        )

    result = await chat_non_stream(
        chart_data=body.chart_data,
        user_message=body.message,
        history=body.history,
    )

    if result["error"]:
        return JSONResponse(status_code=500, content=result)

    return JSONResponse(content=result)


@app.get("/api/health")
async def health_check():
    """健康检查。"""
    return {
        "status": "ok",
        "api_key_configured": bool(os.environ.get("DEEPSEEK_API_KEY", "")),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
