import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from decimal import Decimal
from bson import ObjectId

class Database:
    def __init__(self, uri, db_name):
        self._client = AsyncIOMotorClient(uri)
        self.db = self._client[db_name]
        self.users = self.db.users
        self.logs = self.db.logs
        self.config = self.db.config

    async def is_user_allowed(self, user_id: int) -> bool:
        user = await self.users.find_one({"user_id": user_id, "is_active": True})
        return user is not None

    async def log_calculation(self, user_id: int, result: dict, params: dict) -> ObjectId:
        def to_str(val):
            if isinstance(val, Decimal):
                return str(val.quantize(Decimal("0.0001")))
            return str(val)

        safe_result = {k: to_str(v) for k, v in result.items()}
        safe_params = {k: to_str(v) for k, v in params.items()}

        log_document = {
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc),
            "parameters": safe_params,
            "result": safe_result,
        }
        inserted = await self.logs.insert_one(log_document)
        return inserted.inserted_id

    async def get_log_by_id(self, log_id: str):
        return await self.logs.find_one({"_id": ObjectId(log_id)})

db = Database(settings.MONGO_URI, settings.MONGO_DB_NAME)