from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ETHERSCAN_API_KEY: str = ""
    TWITTER_API_KEY: str = ""
    DISCORD_BOT_TOKEN: str = ""
    TELEGRAM_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    POSTGRES_URI: str = "postgresql://user:password@localhost/db"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    SCAN_DEPTH_DAYS: int = 7
    MIN_LIQUIDITY_USD: float = 50000
    MIN_HOLDERS: int = 100

    class Config:
        env_file = ".env"

settings = Settings()
