from pydantic_settings import BaseSettings
from typing import Dict

class Settings(BaseSettings):
    NODE_ID: str
    MONGO_URI: str
    PEERS: str = ""
    LEASE_DURATION: int = 10
    ELECTION_INTERVAL: int = 5
    HEARTBEAT_INTERVAL: int = 2

    @property
    def peers_dict(self) -> Dict[str, str]:
        return dict(p.split(":", 1) for p in self.PEERS.split(",") if p)

    class Config:
        env_file = ".env"

settings = Settings()