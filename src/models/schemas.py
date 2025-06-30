from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID

class ChainId(int, Enum):
    ETHEREUM = 1
    BSC = 56
    POLYGON = 137
    BASE = 8453
    ARBITRUM = 42161

class RiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class TokenAnalysisRequest(BaseModel):
    token_address: str = Field(..., pattern="^0x[a-fA-F0-9]{40}$")
    chain_id: ChainId
    deep_analysis: bool = False

class Risk(BaseModel):
    type: str
    score: float = Field(..., ge=0, le=1)
    reason: str
    severity: RiskLevel

class HeuristicResult(BaseModel):
    risks: List[Risk]
    overall_score: float = Field(..., ge=0, le=1)
    passed: bool
    critical_risks: List[Risk]

class MLPrediction(BaseModel):
    scam_probability: float = Field(..., ge=0, le=1)
    prediction: str
    confidence: float = Field(..., ge=0, le=1)
    model_available: bool
    top_risk_factors: List[Dict[str, Any]]

class SmartMoneyAnalysis(BaseModel):
    smart_money_score: float = Field(..., ge=0, le=1)
    smart_wallets_holding: List[Dict[str, Any]]
    smart_money_net_flow: float
    recent_smart_buys: List[Dict[str, Any]]
    recent_smart_sells: List[Dict[str, Any]]
    whale_movements: List[Dict[str, Any]]
    accumulation_phase: bool
    distribution_phase: bool
    confidence: float = Field(..., ge=0, le=1)

class TokenAnalysisResponse(BaseModel):
    token_address: str
    chain_id: int
    risk_score: float = Field(..., ge=0, le=1)
    heuristic_risks: List[Risk]
    ml_prediction: Optional[MLPrediction] = None
    smart_money_analysis: Optional[SmartMoneyAnalysis] = None
    recommendations: Dict[str, Any]
    timestamp: datetime
    analysis_time_ms: Optional[int] = None

class AnalysisTaskInfo(BaseModel):
    task_id: UUID
    status: str
    token_address: str
    chain_id: int
    created_at: datetime

class AnalysisStatus(BaseModel):
    task_id: UUID
    status: str
    current_step: str
    progress_percent: int
    intermediate_risks: List[Risk]
    updated_at: datetime

# --- User and Auth Schemas ---

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
