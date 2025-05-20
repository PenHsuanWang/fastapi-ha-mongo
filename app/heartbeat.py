import asyncio, logging, httpx
from datetime import datetime
from motor.core import AgnosticDatabase
from config import settings

log = logging.getLogger("heartbeat")


class HeartbeatScheduler:
    def __init__(self, db: AgnosticDatabase, elector):
        self.db = db
        self.elector = elector
        self.node_id = settings.NODE_ID
        self.peers = settings.peers_dict
        self.interval = settings.HEARTBEAT_INTERVAL

    async def run(self):
        while True:
            now = datetime.utcnow()
            # Update own runner_state
            await self.db.runner_state.update_one(
                {"_id": self.node_id},
                {"$set": {"last_heartbeat": now, "term": self.elector.term}},
                upsert=True
            )
            # If follower, ping leader HTTP
            if not self.elector.is_leader:
                lock = await self.db.leader_lock.find_one({"_id": "leader_lock"})
                if lock:
                    leader_id = lock.get("leader_id")
                    if leader_id and leader_id in self.peers:
                        try:
                            async with httpx.AsyncClient() as client:
                                await client.get(f"{self.peers[leader_id]}/api/heartbeat",
                                                 timeout=1.0)
                        except Exception:
                            log.warning("Leader %s unreachable → trigger election", leader_id)
                            await self.elector.try_elect()
            await asyncio.sleep(self.interval)