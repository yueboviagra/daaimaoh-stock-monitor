"""
定时任务调度 — 每天中午 12:00（日本时间）自动抓取
"""
import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import SCHEDULE_HOUR, SCHEDULE_MINUTE, TIMEZONE

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_scrape_lock = asyncio.Lock()
_next_run_time: datetime | None = None


def setup_scheduler(scrape_callback):
    """
    设置定时任务。
    scrape_callback: 异步函数，执行抓取并保存到数据库。
    """
    async def daily_job():
        await _run_with_lock(scrape_callback)

    async def startup_job():
        await _run_with_lock(scrape_callback)

    # 每天中午 12:00 日本时间
    scheduler.add_job(
        daily_job,
        trigger=CronTrigger(
            hour=SCHEDULE_HOUR,
            minute=SCHEDULE_MINUTE,
            timezone=TIMEZONE,
        ),
        id="daily_noon_scrape",
        name="每天中午 12:00 自动检查库存",
        replace_existing=True,
    )

    # 启动后 30 秒执行一次首次抓取
    scheduler.add_job(
        startup_job,
        trigger="date",
        run_date=datetime.now() + timedelta(seconds=30),
        id="startup_scrape",
        name="启动时首次抓取",
    )

    scheduler.start()
    logger.info(f"定时任务已设置: 每天 {SCHEDULE_HOUR}:{SCHEDULE_MINUTE:02d} ({TIMEZONE})")


def get_next_run_time() -> datetime | None:
    """获取下次定时检查的时间"""
    job = scheduler.get_job("daily_noon_scrape")
    if job:
        return job.next_run_time
    return None


async def _run_with_lock(callback):
    """带锁的抓取执行，防止并发运行"""
    if _scrape_lock.locked():
        logger.warning("上一次抓取尚未完成，跳过本次执行")
        return

    async with _scrape_lock:
        try:
            await callback()
        except Exception as e:
            logger.error(f"定时抓取失败: {e}")
