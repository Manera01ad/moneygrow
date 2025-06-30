from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # API Keys
    ETHERSCAN_API_KEY: str
    BSCSCAN_API_KEY: Optional[str] = ""
    POLYGONSCAN_API_KEY: Optional[str] = ""
    DEXTOOLS_API_KEY: Optional[str] = ""
    GECKOTERMINAL_API_KEY: Optional[str] = ""
    GOPLUS_API_KEY: Optional[str] = ""
    
    # Web3 RPCs
    ETH_RPC: str = "https://eth.llamarpc.com"
    BSC_RPC: str = "https://binance.llamarpc.com"
    POLYGON_RPC: str = "https://polygon.llamarpc.com"
    
    # Database
    DATABASE_URL: str = "postgresql://moneygrow:password@localhost:5432/moneygrow"
    REDIS_URL: str = "redis://localhost:6379"
    
    # Application Settings
    SECRET_KEY: str = "your-secret-key-here"
    API_RATE_LIMIT: int = 100
    MIN_LIQUIDITY_USD: float = 10000
    MAX_RISK_SCORE: float = 0.7
    MIN_HOLDERS: int = 50
    
    # ML Model Paths
    SCAM_MODEL_PATH: str = "ml/models/scam_detector.pkl"
    SCALER_PATH: str = "ml/models/scaler.pkl"
    
    # Smart Money Wallets
    SMART_WALLETS: List[str] = []
    
    # Email Settings (optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
