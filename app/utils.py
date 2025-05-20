import asyncio, motor.motor_asyncio as mm

async def wait_for_mongo(uri: str, timeout=30):
    cli = mm.AsyncIOMotorClient(uri)
    for _ in range(timeout):
        try:
            await cli.admin.command("ping")
            return cli
        except Exception:
            await asyncio.sleep(1)
    raise RuntimeError("MongoDB not reachable in time")