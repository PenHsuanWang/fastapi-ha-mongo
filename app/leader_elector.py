import asyncio, logging
from datetime import datetime, timedelta
from pymongo import ReturnDocument
from motor.core import AgnosticDatabase
from config import settings

log = logging.getLogger("elector")


class LeaderElector:
    def __init__(self, db: AgnosticDatabase):
        self.db = db
        self.node_id = settings.NODE_ID
        self.lease_sec = settings.LEASE_DURATION
        self.is_leader: bool = False
        self.term: int = 0

    async def try_elect(self):
        now = datetime.utcnow()
        new_lease = now + timedelta(seconds=self.lease_sec)
        doc = await self.db.leader_lock.find_one_and_update(
            {"_id": "leader_lock", "lease_until": {"$lte": now}},
            {"$set": {"leader_id": self.node_id, "lease_until": new_lease},
             "$inc": {"term": 1}},
            return_document=ReturnDocument.AFTER
        )
        if doc:
            self.is_leader, self.term = True, doc["term"]
            log.warning("%s became LEADER (term %s)", self.node_id, self.term)
        else:
            # keep cached state in sync
            lock = await self.db.leader_lock.find_one({"_id": "leader_lock"})
            if lock:
                self.is_leader = (lock["leader_id"] == self.node_id)
                self.term = lock["term"]

    async def renew_lease(self):
        if not self.is_leader:
            return
        new_lease = datetime.utcnow() + timedelta(seconds=self.lease_sec)
        res = await self.db.leader_lock.update_one(
            {"_id": "leader_lock", "leader_id": self.node_id},
            {"$set": {"lease_until": new_lease}}
        )
        if res.matched_count == 0:
            # Lost the lock
            self.is_leader = False
            log.warning("%s lost leadership", self.node_id)