import asyncio
from fastapi import FastAPI
from config import settings
from utils import wait_for_mongo
from leader_elector import LeaderElector
from heartbeat import HeartbeatScheduler

app = FastAPI(title="SIE-HA PoC")

# block-until-ready → guarantees no ServerSelectionTimeout
client = asyncio.run(wait_for_mongo(settings.MONGO_URI))
db = client.get_default_database()

elector = LeaderElector(db)
hb = HeartbeatScheduler(db, elector)

@app.on_event("startup")
async def startup():
    loop = asyncio.get_event_loop()

    async def election_loop():
        while True:
            if elector.is_leader:
                await elector.renew_lease()
            else:
                await elector.try_elect()
            await asyncio.sleep(settings.ELECTION_INTERVAL)

    loop.create_task(election_loop())
    loop.create_task(hb.run())

@app.get("/api/heartbeat")
async def heartbeat():
    return {
        "node": settings.NODE_ID,
        "role": "leader" if elector.is_leader else "follower",
        "term": elector.term
    }