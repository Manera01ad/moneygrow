from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import asyncio
from web3 import Web3

from ..config.settings import settings
from ..models.schemas import Risk, HeuristicResult, RiskLevel

class HeuristicEngine:
    """Fast, rule-based analysis for immediate red flags"""
    
    def __init__(self):
        self.settings = settings
        self.critical_checks = {
            'honeypot': self.check_honeypot,
            'liquidity': self.check_liquidity,
            'ownership': self.check_ownership,
            'holders': self.check_holder_distribution,
            'contract': self.check_contract_safety,
            'trading': self.check_trading_patterns
        }
        
    async def analyze(self, token_data: Dict) -> HeuristicResult:
        """Run all heuristic checks in parallel"""
        risks = []
        
        # Run critical checks
        check_tasks = []
        for check_name, check_func in self.critical_checks.items():
            check_tasks.append(check_func(token_data))
        
        check_results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Collect risks
        for result in check_results:
            if isinstance(result, list):
                risks.extend(result)
            elif isinstance(result, Risk):
                risks.append(result)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(risks)
        critical_risks = [r for r in risks if r.severity == RiskLevel.CRITICAL]
        
        return HeuristicResult(
            risks=risks,
            overall_score=overall_score,
            passed=overall_score < self.settings.MAX_RISK_SCORE and len(critical_risks) == 0,
            critical_risks=critical_risks
        )
    
    async def check_honeypot(self, token_data: Dict) -> List[Risk]:
        """Check for honeypot indicators"""
        risks = []
        
        if not token_data.get('can_sell', True):
            risks.append(Risk(
                type="HONEYPOT_CANNOT_SELL",
                score=1.0,
                reason="Token cannot be sold",
                severity=RiskLevel.CRITICAL
            ))
        
        sell_tax = token_data.get('sell_tax', 0)
        if sell_tax > 50:
            risks.append(Risk(
                type="HONEYPOT_HIGH_TAX",
                score=0.9,
                reason=f"Extremely high sell tax: {sell_tax}%",
                severity=RiskLevel.CRITICAL
            ))
        elif sell_tax > 25:
            risks.append(Risk(
                type="HIGH_SELL_TAX",
                score=0.6,
                reason=f"High sell tax: {sell_tax}%",
                severity=RiskLevel.HIGH
            ))
        
        return risks
    
    async def check_liquidity(self, token_data: Dict) -> List[Risk]:
        """Analyze liquidity health"""
        risks = []
        
        liquidity_usd = token_data.get('liquidity_usd', 0)
        market_cap = token_data.get('market_cap', 1)
        liquidity_locked = token_data.get('liquidity_locked_percent', 0)
        
        if liquidity_usd < 5000:
            risks.append(Risk(
                type="EXTREMELY_LOW_LIQUIDITY",
                score=0.9,
                reason=f"Liquidity only ${liquidity_usd:,.0f}",
                severity=RiskLevel.CRITICAL
            ))
        elif liquidity_usd < self.settings.MIN_LIQUIDITY_USD:
            risks.append(Risk(
                type="LOW_LIQUIDITY",
                score=0.7,
                reason=f"Low liquidity: ${liquidity_usd:,.0f}",
                severity=RiskLevel.HIGH
            ))
        
        liq_ratio = liquidity_usd / market_cap if market_cap > 0 else 0
        if liq_ratio < 0.02:
            risks.append(Risk(
                type="POOR_LIQUIDITY_RATIO",
                score=0.8,
                reason=f"Liquidity only {liq_ratio*100:.1f}% of market cap",
                severity=RiskLevel.HIGH
            ))
        
        return risks
    
    async def check_ownership(self, token_data: Dict) -> List[Risk]:
        """Check contract ownership and permissions"""
        risks = []
        
        if not token_data.get('ownership_renounced', False):
            risks.append(Risk(
                type="CENTRALIZED_OWNERSHIP",
                score=0.5,
                reason="Contract ownership not renounced",
                severity=RiskLevel.MEDIUM
            ))
        
        if token_data.get('has_mint_function', False):
            if not token_data.get('mint_disabled', False):
                risks.append(Risk(
                    type="ACTIVE_MINT_FUNCTION",
                    score=0.8,
                    reason="Contract can mint new tokens",
                    severity=RiskLevel.HIGH
                ))
        
        return risks
    
    async def check_holder_distribution(self, token_data: Dict) -> List[Risk]:
        """Analyze token holder distribution"""
        risks = []
        
        holder_count = token_data.get('holder_count', 0)
        top10_percent = token_data.get('top10_holders_percent', 100)
        
        if holder_count < 20:
            risks.append(Risk(
                type="VERY_FEW_HOLDERS",
                score=0.9,
                reason=f"Only {holder_count} holders",
                severity=RiskLevel.CRITICAL
            ))
        elif holder_count < self.settings.MIN_HOLDERS:
            risks.append(Risk(
                type="LOW_HOLDER_COUNT",
                score=0.6,
                reason=f"Low holder count: {holder_count}",
                severity=RiskLevel.HIGH
            ))
        
        if top10_percent > 80:
            risks.append(Risk(
                type="HIGH_CONCENTRATION",
                score=0.7,
                reason=f"Top 10 holders own {top10_percent:.1f}%",
                severity=RiskLevel.HIGH
            ))
        
        return risks
    
    async def check_contract_safety(self, token_data: Dict) -> List[Risk]:
        """Check contract-related safety factors"""
        risks = []
        
        if not token_data.get('contract_verified', False):
            risks.append(Risk(
                type="UNVERIFIED_CONTRACT",
                score=0.5,
                reason="Contract source not verified",
                severity=RiskLevel.MEDIUM
            ))
        
        created_at = token_data.get('contract_created_at')
        if created_at and isinstance(created_at, datetime):
            age_hours = (datetime.now() - created_at).total_seconds() / 3600
            if age_hours < 24:
                risks.append(Risk(
                    type="NEW_CONTRACT",
                    score=0.5,
                    reason=f"Contract less than 24 hours old",
                    severity=RiskLevel.MEDIUM
                ))
        
        return risks
    
    async def check_trading_patterns(self, token_data: Dict) -> List[Risk]:
        """Analyze trading patterns for red flags"""
        risks = []
        
        volume_24h = token_data.get('volume_24h', 0)
        liquidity = token_data.get('liquidity_usd', 1)
        volume_liq_ratio = volume_24h / liquidity if liquidity > 0 else 0
        
        if volume_liq_ratio < 0.1:
            risks.append(Risk(
                type="LOW_TRADING_ACTIVITY",
                score=0.5,
                reason=f"Very low volume/liquidity ratio: {volume_liq_ratio:.2f}",
                severity=RiskLevel.MEDIUM
            ))
        
        return risks
    
    def _calculate_overall_score(self, risks: List[Risk]) -> float:
        """Calculate weighted overall risk score"""
        if not risks:
            return 0.0
        
        severity_weights = {
            RiskLevel.CRITICAL: 1.0,
            RiskLevel.HIGH: 0.8,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.LOW: 0.3
        }
        
        weighted_sum = sum(r.score * severity_weights.get(r.severity, 0.5) for r in risks)
        max_possible = len(risks)
        
        return min(weighted_sum / max_possible if max_possible > 0 else 0, 1.0)
