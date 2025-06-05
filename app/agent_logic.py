from .memory import HybridMemory
from .tools.onchain import OnChainScanner
from .tools.social import SocialScanner
from .tools.docs import DocsScanner
from .tools.github import GithubScanner
from .anti_scam import ScamDetector
from .eval import AgentEvaluator

import asyncio

async def run_agent(input_data):
    # Initialize tools and modules
    memory = HybridMemory()
    scam_detector = ScamDetector()
    evaluator = AgentEvaluator()
    tools = {
        'onchain': OnChainScanner(),
        'social': SocialScanner(),
        'docs': DocsScanner(),
        'github': GithubScanner()
    }

    # 1. Quick scam check
    if await scam_detector.quick_check(input_data["token_address"], input_data["chain_id"]):
        return {"status": "rejected", "reason": "Failed initial safety checks"}, []

    # 2. Gather data in parallel
    results = await asyncio.gather(
        tools['onchain'].scan_token(input_data["token_address"], input_data["chain_id"]),
        tools['social'].scan(input_data["token_address"], input_data["chain_id"]),
        tools['docs'].fetch_and_parse(input_data["token_address"], input_data["chain_id"]),
        tools['github'].analyze(input_data["token_address"])
    )
    data = dict(zip(['onchain', 'social', 'docs', 'github'], results))

    # 3. Deep scam check
    scam_risk = await scam_detector.deep_check(*results)
    if scam_risk:
        return {"status": "rejected", "reason": "Failed deep scam check", "details": data}, data

    # 4. Self-evaluation and scoring
    confidence = evaluator.evaluate_analysis(data)

    return {
        "status": "success",
        "analysis": data,
        "confidence": confidence
    }, data
