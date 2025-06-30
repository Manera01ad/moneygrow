from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional, List
import asyncio
from datetime import datetime, timedelta
import time
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config.settings import settings
from ..analyzers.heuristic_engine import HeuristicEngine
from ..analyzers.ml_detector import MLScamDetector
from ..analyzers.smart_money_tracker import SmartMoneyTracker
from ..data.collectors import DataCollector
from ..utils.database import init_db, get_db
from ..models import database, schemas
from ..models.schemas import (
    TokenAnalysisRequest, TokenAnalysisResponse, Risk,
    AnalysisTaskInfo, AnalysisStatus
)
from ..models.database import TokenAnalysis, AnalysisTask, TaskStatus
from ..tasks.workers import run_analysis_task
from sqlalchemy import select
from . import auth, users, security

app = FastAPI(
    title="MoneyGrow API",
    description="Advanced crypto token analysis API",
    version="1.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
heuristic_engine = HeuristicEngine()
ml_detector = MLScamDetector()
smart_money_tracker = SmartMoneyTracker()

# Include routers
app.include_router(auth.router)
app.include_router(users.router)

@app.get("/")
async def root():
    return {
        "message": "MoneyGrow API is running!",
        "version": "1.2.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "api": "ok",
            "etherscan_configured": bool(settings.ETHERSCAN_API_KEY),
            "database": "ok"  # Add real DB check later
        }
    }

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_db()
    print("Database initialized")

@app.post("/api/v1/analysis", response_model=AnalysisTaskInfo, status_code=202)
async def start_analysis(
    request: TokenAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: database.User = Depends(security.get_user_from_api_key)
):
    """
    Start a new asynchronous token analysis task. Requires API Key authentication.
    """
    # Create a new task record in the database, associated with the user
    new_task = AnalysisTask(
        token_address=request.token_address,
        chain_id=request.chain_id,
        user_id=current_user.id
    )
    async with db as session:
        session.add(new_task)
        await session.commit()
        await session.refresh(new_task)

    # Enqueue the background job
    run_analysis_task.delay(str(new_task.id))

    return AnalysisTaskInfo(
        task_id=new_task.id,
        status=new_task.status.value,
        token_address=new_task.token_address,
        chain_id=new_task.chain_id,
        created_at=new_task.created_at
    )

@app.get("/api/v1/analysis/{task_id}/status", response_model=AnalysisStatus)
async def get_analysis_status(task_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get the status of an analysis task.
    """
    async with db as session:
        task = await session.get(AnalysisTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Analysis task not found")

        intermediate_risks = []
        if task.intermediate_results and 'risks' in task.intermediate_results:
            intermediate_risks = [Risk(**r) for r in task.intermediate_results['risks']]

        return AnalysisStatus(
            task_id=task.id,
            status=task.status.value,
            current_step=task.current_step.value,
            progress_percent=task.progress_percent,
            intermediate_risks=intermediate_risks,
            updated_at=task.updated_at or task.created_at
        )

@app.get("/api/v1/analysis/{task_id}/results", response_model=TokenAnalysisResponse)
async def get_analysis_results(task_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get the final results of a completed analysis task.
    """
    async with db as session:
        result = await session.execute(
            select(AnalysisTask).options(selectinload(AnalysisTask.final_analysis))
            .where(AnalysisTask.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Analysis task not found")
        if task.status != TaskStatus.COMPLETED or not task.final_analysis:
            raise HTTPException(status_code=400, detail="Analysis is not yet complete")

        analysis = task.final_analysis
        analysis_data = analysis.analysis_data or {}
        heuristic_data = analysis_data.get('heuristic', {})
        risks_data = heuristic_data.get('risks', [])

        return TokenAnalysisResponse(
            token_address=analysis.token_address,
            chain_id=analysis.chain_id,
            risk_score=analysis.risk_score,
            heuristic_risks=[Risk(**r) for r in risks_data],
            ml_prediction=analysis_data.get('ml', {}),
            smart_money_analysis=analysis_data.get('smart_money', {}),
            recommendations=analysis.recommendations or {},
            timestamp=analysis.created_at,
            analysis_time_ms=None # Not applicable for async tasks
        )


@app.post("/analyze", response_model=TokenAnalysisResponse, deprecated=True, include_in_schema=False)
async def analyze_token(request: TokenAnalysisRequest):
    """(DEPRECATED) Complete token analysis endpoint"""
    start_time = time.time()
    
    try:
        # Check if we have recent analysis in cache/db
        async with get_db() as db:
            result = await db.execute(
                select(TokenAnalysis)
                .where(
                    TokenAnalysis.token_address == request.token_address,
                    TokenAnalysis.chain_id == request.chain_id,
                    TokenAnalysis.created_at > datetime.now() - timedelta(minutes=5)
                )
                .order_by(TokenAnalysis.created_at.desc())
                .limit(1)
            )
            recent_analysis = result.scalar_one_or_none()
            
            if recent_analysis and not request.deep_analysis:
                # Return cached analysis
                # Properly deserialize the cached analysis data
                analysis_data = recent_analysis.analysis_data or {}
                heuristic_data = analysis_data.get('heuristic', {})
                risks_data = heuristic_data.get('risks', [])
                
                return TokenAnalysisResponse(
                    token_address=recent_analysis.token_address,
                    chain_id=recent_analysis.chain_id,
                    risk_score=recent_analysis.risk_score,
                    heuristic_risks=[Risk(**r) for r in risks_data],
                    ml_prediction=analysis_data.get('ml', {}),
                    smart_money_analysis=analysis_data.get('smart_money', {}),
                    recommendations=recent_analysis.recommendations or {},
                    timestamp=recent_analysis.created_at,
                    analysis_time_ms=1 # Indicate it's a cached response
                )
        
        # Collect token data
        async with DataCollector() as collector:
            token_data = await collector.collect_all_data(
                request.token_address,
                request.chain_id
            )
        # Run all analyses in parallel
        heuristic_task = heuristic_engine.analyze(token_data)
        ml_task = ml_detector.predict_scam_probability(token_data)
        smart_money_task = smart_money_tracker.analyze_smart_money_flow(
            request.token_address, request.chain_id, token_data
        )
        heuristic_result, ml_result, smart_money_result = await asyncio.gather(
            heuristic_task, ml_task, smart_money_task
        )
        # Calculate overall risk score
        overall_risk_score = (
            heuristic_result.overall_score * 0.4 +
            ml_result['scam_probability'] * 0.4 +
            (1 - smart_money_result['smart_money_score']) * 0.2
        )
        # Generate recommendations
        recommendations = generate_enhanced_recommendations(
            heuristic_result, ml_result, smart_money_result, overall_risk_score
        )
        
        # Queue background task for detailed analysis
        run_analysis_task.delay(request.token_address, request.chain_id)
        
        # Calculate analysis time
        analysis_time_ms = int((time.time() - start_time) * 1000)
        
        # Store in database
        async with get_db() as db:
            analysis = TokenAnalysis(
                token_address=request.token_address,
                chain_id=request.chain_id,
                risk_score=overall_risk_score,
                ml_scam_probability=ml_result['scam_probability'],
                smart_money_score=smart_money_result['smart_money_score'],
                analysis_data={
                    'heuristic': {'risks': [r.dict() for r in heuristic_result.risks]},
                    'ml': ml_result,
                    'smart_money': smart_money_result
                },
                recommendations=recommendations
            )
            db.add(analysis)
            await db.commit()
            
        return TokenAnalysisResponse(
            token_address=request.token_address,
            chain_id=request.chain_id,
            risk_score=overall_risk_score,
            heuristic_risks=heuristic_result.risks,
            ml_prediction=ml_result,
            smart_money_analysis=smart_money_result,
            recommendations=recommendations,
            timestamp=datetime.now(),
            analysis_time_ms=analysis_time_ms
        )
    except Exception as e:
        print(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/data-sources")
async def check_data_sources():
    """Check which data sources are configured and working"""
    status = {
        "etherscan": {
            "configured": bool(settings.ETHERSCAN_API_KEY),
            "chains": [1] if settings.ETHERSCAN_API_KEY else []
        },
        "bscscan": {
            "configured": bool(settings.BSCSCAN_API_KEY),
            "chains": [56] if settings.BSCSCAN_API_KEY else []
        },
        "geckoterminal": {
            "configured": True,  # No API key needed
            "chains": [1, 56, 137, 8453, 42161]
        },
        "web3_rpc": {
            "ethereum": bool(settings.ETH_RPC),
            "bsc": bool(settings.BSC_RPC),
            "polygon": bool(settings.POLYGON_RPC)
        }
    }
    return status

@app.get("/smart-money/wallets")
async def get_smart_wallets(limit: int = 100):
    """Get list of tracked smart money wallets"""
    wallets = await smart_money_tracker.get_top_smart_wallets(limit)
    return {"wallets": wallets}

@app.get("/analysis/history/{token_address}")
async def get_analysis_history(token_address: str, chain_id: int = 1):
    """Get historical analyses for a token"""
    async with get_db() as db:
        result = await db.execute(
            select(TokenAnalysis)
            .where(
                TokenAnalysis.token_address == token_address,
                TokenAnalysis.chain_id == chain_id
            )
            .order_by(TokenAnalysis.created_at.desc())
            .limit(10)
        )
        analyses = result.scalars().all()
        
        return {
            "token_address": token_address,
            "chain_id": chain_id,
            "analyses": [
                {
                    "timestamp": a.created_at,
                    "risk_score": a.risk_score,
                    "ml_scam_probability": a.ml_scam_probability,
                    "smart_money_score": a.smart_money_score
                }
                for a in analyses
            ]
        }

def generate_enhanced_recommendations(heuristic_result, ml_result, smart_money_result, overall_risk_score) -> Dict:
    """Generate enhanced recommendations with all analyses"""
    recommendations = {
        'action': 'AVOID',
        'confidence': 'HIGH',
        'reasons': [],
        'suggested_actions': []
    }
    # Determine primary action based on all factors
    if overall_risk_score > 0.7:
        recommendations['action'] = 'AVOID'
        recommendations['reasons'].append(f"High overall risk score: {overall_risk_score:.2f}")
    elif overall_risk_score < 0.3 and smart_money_result['smart_money_score'] > 0.7:
        recommendations['action'] = 'INVESTIGATE'
        recommendations['reasons'].append("Low risk with high smart money interest")
        recommendations['suggested_actions'].append("Consider small position with stop-loss")
    else:
        recommendations['action'] = 'CAUTION'
        recommendations['reasons'].append("Mixed signals require careful analysis")
    # Add specific ML insights
    if ml_result['scam_probability'] > 0.7:
        recommendations['reasons'].append(
            f"ML model indicates {ml_result['scam_probability']*100:.0f}% scam probability"
        )
    # Add smart money insights
    if smart_money_result['accumulation_phase']:
        recommendations['suggested_actions'].append("Smart money appears to be accumulating")
    elif smart_money_result['distribution_phase']:
        recommendations['reasons'].append("Smart money appears to be exiting")
    # Add top risk factors
    for risk in heuristic_result.critical_risks[:2]:
        recommendations['reasons'].append(risk.reason)
    return recommendations