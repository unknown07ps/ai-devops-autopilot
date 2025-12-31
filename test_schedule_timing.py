# test_schedule_timing.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

scheduler = AsyncIOScheduler()

# Test job that runs every minute
@scheduler.scheduled_job(CronTrigger(minute='*'))
async def test_job():
    print(f"[TEST] Job executed at {datetime.now()}")

scheduler.start()

# Run for 5 minutes
asyncio.run(asyncio.sleep(300))
scheduler.shutdown()