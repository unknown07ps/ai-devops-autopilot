import asyncio
import httpx

async def test():
    client = httpx.AsyncClient(timeout=30.0)
    response = await client.post(
        "http://localhost:8000/api/v3/autonomous/adjust-weights",
        json={"rule_weight": 1.5}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    await client.aclose()

asyncio.run(test())
