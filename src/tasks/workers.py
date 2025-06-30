from celery import Celery
from celery.schedules import crontab
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging
from uuid import UUID

from ..config.settings import settings
from ..utils.database import get_db, init_db
from ..models.database import TokenAnalysis, TokenMetrics, AnalysisTask, TaskStatus, AnalysisStep
from ..models.schemas import Risk, HeuristicResult
from ..data.collectors import DataCollector
from ..analyzers.heuristic_engine import HeuristicEngine
from ..analyzers.ml_detector import MLScamDetector
from ..analyzers.smart_money_tracker import SmartMoneyTracker

logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    'moneygrow',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'monitor-trending-tokens': {
            'task': 'src.tasks.workers.monitor_trending_tokens',
            'schedule': crontab(minute='*/15'),  # Every 15 minutes
        },
        'update-token-metrics': {
            'task': 'src.tasks.workers.update_token_metrics',
            'schedule': crontab(minute='*/30'),  # Every 30 minutes
        },
        'cleanup-old-data': {
            'task': 'src.tasks.workers.cleanup_old_data',
            'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        },
    }
)

async def update_task_status(task_id: UUID, status: TaskStatus = None, step: AnalysisStep = None, progress: int = None, intermediate_results: Dict = None):
    """Update the status of an analysis task."""
    async with get_db() as db:
        task = await db.get(AnalysisTask, task_id)
        if task:
            if status:
                task.status = status
            if step:
                task.current_step = step
            if progress is not None:
                task.progress_percent = progress
            if intermediate_results:
                # Merge new results with existing ones
                if not task.intermediate_results:
                    task.intermediate_results = {}
                for key, value in intermediate_results.items():
                    if key not in task.intermediate_results:
                        task.intermediate_results[key] = []
                    task.intermediate_results[key].extend(value)

            await db.commit()

@celery_app.task(name="src.tasks.workers.run_analysis_task")
def run_analysis_task(task_id_str: str):
    """The main Celery task to run a full token analysis."""
    task_id = UUID(task_id_str)
    asyncio.run(_run_analysis_task(task_id))

async def _run_analysis_task(task_id: UUID):
    """Asynchronous orchestrator for the analysis task."""
    await update_task_status(task_id, status=TaskStatus.RUNNING, step=AnalysisStep.INITIALIZING, progress=5)
    
    try:
        async with get_db() as db:
            task = await db.get(AnalysisTask, task_id)
            if not task:
                logger.error(f"Task {task_id} not found.")
                return

        token_address = task.token_address
        chain_id = task.chain_id

        # Initialize components
        await init_db()
        collector = DataCollector()
        heuristic_engine = HeuristicEngine()
        ml_detector = MLScamDetector()
        smart_money_tracker = SmartMoneyTracker()

        # Step 1: Fetching Data
        await update_task_status(task_id, step=AnalysisStep.FETCHING_DATA, progress=10)
        async with collector:
            token_data = await collector.collect_all_data(token_address, chain_id)
        
        # Step 2: Heuristic Analysis (step-by-step)
        heuristic_risks = []
        analysis_steps = [
            (AnalysisStep.CHECKING_HONEYPOT, heuristic_engine.check_honeypot, 20),
            (AnalysisStep.ANALYZING_LIQUIDITY, heuristic_engine.check_liquidity, 30),
            (AnalysisStep.VERIFYING_OWNERSHIP, heuristic_engine.check_ownership, 40),
            (AnalysisStep.ANALYZING_HOLDERS, heuristic_engine.check_holder_distribution, 50),
            (AnalysisStep.EVALUATING_CONTRACT_SAFETY, heuristic_engine.check_contract_safety, 60),
        ]

        for step, check_func, progress in analysis_steps:
            await update_task_status(task_id, step=step, progress=progress)
            risks = await check_func(token_data)
            if risks:
                heuristic_risks.extend(risks)
                await update_task_status(task_id, intermediate_results={'risks': [r.dict() for r in risks]})

        heuristic_result = HeuristicResult(
            risks=heuristic_risks,
            overall_score=heuristic_engine._calculate_overall_score(heuristic_risks),
            passed=True, # Logic to be refined
            critical_risks=[r for r in heuristic_risks if r.severity == "CRITICAL"]
        )

        # Step 3: ML Detection
        await update_task_status(task_id, step=AnalysisStep.RUNNING_ML_DETECTION, progress=70)
        ml_result = await ml_detector.predict_scam_probability(token_data)

        # Step 4: Smart Money Tracking
        await update_task_status(task_id, step=AnalysisStep.TRACKING_SMART_MONEY, progress=80)
        smart_money_result = await smart_money_tracker.analyze_smart_money_flow(
            token_address, chain_id, token_data
        )

        # Step 5: Generating Report
        await update_task_status(task_id, step=AnalysisStep.GENERATING_REPORT, progress=90)
        overall_risk = (
            heuristic_result.overall_score * 0.4 +
            ml_result['scam_probability'] * 0.4 +
            (1 - smart_money_result['smart_money_score']) * 0.2
        )
        
        # This would call the recommendation engine from main.py, simplified here
        recommendations = {"action": "CAUTION", "reasons": ["Check detailed report."]}

        # Store final analysis in database
        async with get_db() as db:
            final_analysis = TokenAnalysis(
                token_address=token_address,
                chain_id=chain_id,
                risk_score=overall_risk,
                ml_scam_probability=ml_result['scam_probability'],
                smart_money_score=smart_money_result['smart_money_score'],
                analysis_data={
                    'heuristic': {'risks': [r.dict() for r in heuristic_result.risks]},
                    'ml': ml_result,
                    'smart_money': smart_money_result,
                },
                recommendations=recommendations
            )
            db.add(final_analysis)
            await db.flush() # Use flush to get the ID before commit
            
            # Link final analysis to the task
            task = await db.get(AnalysisTask, task_id)
            task.final_analysis_id = final_analysis.id
            await db.commit()

        # Final Step: Mark as complete
        await update_task_status(task_id, status=TaskStatus.COMPLETED, step=AnalysisStep.COMPLETED, progress=100)
        logger.info(f"Analysis task {task_id} completed successfully.")

    except Exception as e:
        logger.error(f"Analysis task {task_id} failed: {e}", exc_info=True)
        await update_task_status(task_id, status=TaskStatus.FAILED, step=AnalysisStep.FAILED, progress=100)

@celery_app.task
def monitor_trending_tokens():
    """Monitor trending tokens from DEXs"""
    asyncio.run(_monitor_trending_tokens())

async def _monitor_trending_tokens():
    """Get trending tokens and analyze them"""
    try:
        # This would fetch trending tokens from various sources
        # For now, just a placeholder
        trending_tokens = [
            # Add trending token addresses here
        ]
        
        for token in trending_tokens:
            analyze_token_background.delay(token['address'], token['chain_id'])
            
    except Exception as e:
        print(f"Monitoring error: {e}")

@celery_app.task
def update_token_metrics():
    """Update metrics for tracked tokens"""
    asyncio.run(_update_token_metrics())

async def _update_token_metrics():
    """Update price and liquidity metrics"""
    try:
        async with get_db() as db:
            # Get recently analyzed tokens
            result = await db.execute(
                select(TokenAnalysis.token_address, TokenAnalysis.chain_id)
                .distinct()
                .where(TokenAnalysis.created_at > datetime.now() - timedelta(days=7))
                .limit(100)
            )
            tokens = result.all()
            
            collector = DataCollector()
            async with collector:
                for token_address, chain_id in tokens:
                    try:
                        # Collect fresh data
                        data = await collector.collect_dex_data(token_address, chain_id)
                        
                        # Store metrics
                        metrics = TokenMetrics(
                            token_address=token_address,
                            chain_id=chain_id,
                            price_usd=data.get('price_usd', 0),
                            liquidity_usd=data.get('liquidity_usd', 0),
                            volume_24h=data.get('volume_24h', 0),
                            market_cap=data.get('market_cap', 0)
                        )
                        db.add(metrics)
                        
                    except Exception as e:
                        print(f"Error updating metrics for {token_address}: {e}")
                
                await db.commit()
                
    except Exception as e:
        print(f"Metrics update error: {e}")

@celery_app.task
def cleanup_old_data():
    """Clean up old analysis data"""
    asyncio.run(_cleanup_old_data())

async def _cleanup_old_data():
    """Remove old records"""
    try:
        async with get_db() as db:
            cutoff_date = datetime.now() - timedelta(days=30)
            
            # Delete old analyses
            await db.execute(
                f"DELETE FROM token_analyses WHERE created_at < '{cutoff_date}'"
            )
            
            # Delete old metrics
            await db.execute(
                f"DELETE FROM token_metrics WHERE timestamp < '{cutoff_date}'"
            )
            
            await db.commit()
            print(f"Cleaned up data older than {cutoff_date}")
            
    except Exception as e:
        print(f"Cleanup error: {e}")