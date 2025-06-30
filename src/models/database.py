from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Index, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum

Base = declarative_base()

class TaskStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AnalysisStep(enum.Enum):
    INITIALIZING = "INITIALIZING"
    FETCHING_DATA = "FETCHING_DATA"
    CHECKING_HONEYPOT = "CHECKING_HONEYPOT"
    ANALYZING_LIQUIDITY = "ANALYZING_LIQUIDITY"
    VERIFYING_OWNERSHIP = "VERIFYING_OWNERSHIP"
    ANALYZING_HOLDERS = "ANALYZING_HOLDERS"
    EVALUATING_CONTRACT_SAFETY = "EVALUATING_CONTRACT_SAFETY"
    RUNNING_ML_DETECTION = "RUNNING_ML_DETECTION"
    TRACKING_SMART_MONEY = "TRACKING_SMART_MONEY"
    GENERATING_REPORT = "GENERATING_REPORT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    
    api_keys = relationship("APIKey", back_populates="owner")
    tasks = relationship("AnalysisTask", back_populates="user")

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="api_keys")

class TokenAnalysis(Base):
    __tablename__ = "token_analyses"
    
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_address = Column(String(42), nullable=False)
    chain_id = Column(Integer, nullable=False)
    risk_score = Column(Float)
    ml_scam_probability = Column(Float)
    smart_money_score = Column(Float)
    analysis_data = Column(JSON)
    recommendations = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_token_chain', 'token_address', 'chain_id'),
        Index('idx_created_at', 'created_at'),
    )

class KnownScam(Base):
    __tablename__ = "known_scams"
    
    token_address = Column(String(42), primary_key=True)
    chain_id = Column(Integer, nullable=False)
    scam_type = Column(String(50))
    evidence = Column(JSON)
    reported_by = Column(String(100))
    confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SmartWallet(Base):
    __tablename__ = "smart_wallets"
    
    wallet_address = Column(String(42), primary_key=True)
    total_trades = Column(Integer, default=0)
    profitable_trades = Column(Integer, default=0)
    total_profit_usd = Column(Float, default=0)
    average_return = Column(Float, default=0)
    win_rate = Column(Float, default=0)
    last_activity = Column(DateTime(timezone=True))
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_win_rate', 'win_rate'),
        Index('idx_last_activity', 'last_activity'),
    )

class TokenMetrics(Base):
    __tablename__ = "token_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_address = Column(String(42), nullable=False)
    chain_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    price_usd = Column(Float)
    liquidity_usd = Column(Float)
    volume_24h = Column(Float)
    holder_count = Column(Integer)
    market_cap = Column(Float)
    
    __table_args__ = (
        Index('idx_token_metrics', 'token_address', 'chain_id', 'timestamp'),
    )

class TrainingData(Base):
    __tablename__ = "training_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_address = Column(String(42), nullable=False)
    chain_id = Column(Integer, nullable=False)
    features = Column(JSON, nullable=False)
    is_scam = Column(Boolean, nullable=False)
    scam_type = Column(String(50))
    confidence = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_training_data', 'token_address', 'chain_id'),
    )

class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_address = Column(String(42), nullable=False)
    chain_id = Column(Integer, nullable=False)
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True) # Nullable for now for existing tasks
    user = relationship("User", back_populates="tasks")

    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    current_step = Column(Enum(AnalysisStep), default=AnalysisStep.INITIALIZING, nullable=False)
    progress_percent = Column(Integer, default=0, nullable=False)
    
    intermediate_results = Column(JSONB, default=lambda: {"risks": []})
    
    final_analysis_id = Column(UUID(as_uuid=True), ForeignKey('token_analyses.id'), nullable=True)
    final_analysis = relationship("TokenAnalysis")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_task_status', 'status'),
        Index('idx_task_created_at', 'created_at'),
    )