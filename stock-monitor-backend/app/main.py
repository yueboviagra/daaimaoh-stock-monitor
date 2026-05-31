"""
FastAPI 应用主入口 — Web 仪表盘 + API
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from starlette.types import ASGIApp, Scope, Receive, Send
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import PRODUCTS, TIMEZONE
from app.database import (
    init_db, save_snapshot, get_latest_snapshot,
    get_snapshot_history, get_snapshot_detail, get_stock_changes,
)
from app.scraper import scrape_all_products
from app.scheduler import setup_scheduler, get_next_run_time, _run_with_lock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="app/templates")


class StripRootPathMiddleware:
    """ASGI 中间件：剥离 root_path 前缀，让反向代理子路径正常工作"""
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            root_path = scope.get("root_path", "")
            path = scope.get("path", "/")
            if root_path and path.startswith(root_path):
                scope["path"] = path[len(root_path):] or "/"
        await self.app(scope, receive, send)


def root_path(request: Request) -> str:
    """获取根路径，用于模板中生成 URL"""
    return request.scope.get("root_path", "")


templates.env.globals["root_path"] = root_path


# ====== 抓取回调（用于定时任务） ======

async def scheduled_scrape():
    """定时任务回调：执行抓取并保存到数据库"""
    logger.info("=== 定时抓取开始 ===")
    results = await scrape_all_products(PRODUCTS)
    summary = save_snapshot(results)
    logger.info(f"=== 定时抓取完成: {summary} ===")
    return summary


# ====== 应用生命周期 ======

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    logger.info("初始化数据库...")
    init_db()
    logger.info("设置定时任务...")
    setup_scheduler(scheduled_scrape)
    yield
    # 关闭时清理
    logger.info("应用关闭")


app = FastAPI(
    title="大魔王库存监控",
    description="自动抓取 daimaoh.co.jp 商品库存，每日 12:00 日本时间自动检查",
    version="1.0.0",
    lifespan=lifespan,
)

# 添加根路径剥离中间件
app.add_middleware(StripRootPathMiddleware)

# 静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ====== 页面路由 ======

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """仪表盘首页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/history/{snapshot_id}", response_class=HTMLResponse)
async def history_detail_page(request: Request, snapshot_id: int):
    """历史快照详情页"""
    result = get_snapshot_detail(snapshot_id)
    if not result:
        raise HTTPException(status_code=404, detail="快照不存在")
    return templates.TemplateResponse("history_detail.html", {
        "request": request,
        "snapshot": result,
    })


# ====== API 路由 ======

@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.get("/api/status")
async def api_status():
    """获取最新一次检查结果"""
    result = get_latest_snapshot()
    if not result:
        return JSONResponse({"error": "暂无数据，请先执行检查"}, status_code=404)
    return result


@app.get("/api/history")
async def api_history(limit: int = 30):
    """获取历史快照列表"""
    return get_snapshot_history(limit)


@app.get("/api/history/{snapshot_id}")
async def api_history_detail(snapshot_id: int):
    """获取指定快照详情"""
    result = get_snapshot_detail(snapshot_id)
    if not result:
        raise HTTPException(status_code=404, detail="快照不存在")
    return result


@app.get("/api/changes")
async def api_changes():
    """获取最近一次与上一次的库存变化"""
    return get_stock_changes()


@app.post("/api/scrape")
async def api_scrape():
    """手动触发抓取"""
    logger.info("手动触发抓取...")
    try:
        results = await scrape_all_products(PRODUCTS)
        summary = save_snapshot(results)
        return {"message": "抓取完成", **summary}
    except Exception as e:
        logger.error(f"手动抓取失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schedule")
async def api_schedule():
    """获取定时任务信息"""
    next_run = get_next_run_time()
    return {
        "next_run": next_run.isoformat() if next_run else None,
        "schedule": f"每天 12:00 ({TIMEZONE})",
    }
