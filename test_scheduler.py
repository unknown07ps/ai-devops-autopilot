# test_scheduler.py
import asyncio
import sys
sys.path.insert(0, 'src')

from scheduler_service import check_trial_expirations, send_trial_reminders

async def test():
    print("Testing trial expiration check...")
    await check_trial_expirations()
    
    print("\nTesting trial reminders...")
    await send_trial_reminders()

asyncio.run(test())