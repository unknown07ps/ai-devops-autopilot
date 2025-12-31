import os
import json
import httpx
import redis
from datetime import datetime, timezone

from notifications.email import send_expiry_reminder_email

async def check_trial_expirations():
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                'http://localhost:8000/api/subscription/check-expirations'
            )
    except Exception as e:
        print(f"[SCHEDULER ERROR] {e}")


async def send_trial_reminders():
    redis_client = redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379")
    )

    now = datetime.now(timezone.utc)

    for key in redis_client.scan_iter("subscription:*"):
        sub = json.loads(redis_client.get(key))

        if sub["status"] != "trialing":
            continue

        trial_end = datetime.fromisoformat(
            sub["trial_end"].replace("Z", "+00:00")
        )

        days_remaining = (trial_end - now).days

        if days_remaining in (1, 3):
            await send_expiry_reminder_email(
                email=sub["email"],
                user_id=sub["user_id"],
                days_remaining=days_remaining
            )
