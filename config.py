from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # Telegram
    BOT_TOKEN: str
    REPORT_CHAT_ID: int
    
    # MongoDB
    MONGO_USER: str
    MONGO_PASS: str
    MONGO_HOST: str
    MONGO_DB_NAME: str

    @property
    def MONGO_URI(self) -> str:
        return f"mongodb+srv://{self.MONGO_USER}:{quote_plus(self.MONGO_PASS)}@{self.MONGO_HOST}/?retryWrites=true&w=majority&appName=Cluster0"

settings = Settings()