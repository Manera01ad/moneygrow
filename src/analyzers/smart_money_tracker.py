from typing import Dict, List, Set, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import settings
from ..models.database import SmartWallet, TokenAnalysis
from ..utils.database import get_db

class SmartMoneyTracker:
    """Track and analyze smart money movements"""
    
    def __init__(self):
        self.smart_wallets = set()
        self.whale_threshold = 100000  # $100k USD
        self._load_initial_wallets()
    
    def _load_initial_wallets(self):
        """Load known smart wallets from settings"""
        if settings.SMART_WALLETS:
            self.smart_wallets.update(settings.SMART_WALLETS)
        
        # Add some known smart wallets (examples)
        self.smart_wallets.update([
            "0x0000000000000000000000000000000000000001",  # Example
            # Add real profitable wallet addresses here
        ])
    
    async def analyze_smart_money_flow(self, token_address: str, chain_id: int, token_data: Dict) -> Dict:
        """Analyze smart money activity for a token"""
        analysis = {
            'smart_money_score': 0.0,
            'smart_wallets_holding': [],
            'smart_money_net_flow': 0,
            'recent_smart_buys': [],
            'recent_smart_sells': [],
            'whale_movements': [],
            'accumulation_phase': False,
            'distribution_phase': False,
            'confidence': 0.5
        }
        
        try:
            # Get holder addresses from token data
            holder_addresses = token_data.get('holder_addresses', [])
            
            # Check which smart wallets are holding
            smart_holders = []
            for holder in holder_addresses:
                if holder.lower() in [w.lower() for w in self.smart_wallets]:
                    smart_holders.append({
                        'address': holder,
                        'is_smart_money': True
                    })
            
            analysis['smart_wallets_holding'] = smart_holders
            
            # Calculate smart money score based on various factors
            score = 0.0
            
            # Factor 1: Smart wallets holding (40%)
            if len(smart_holders) > 0:
                score += min(len(smart_holders) * 0.1, 0.4)
            
            # Factor 2: Low holder concentration (30%)
            top10_percent = token_data.get('top10_holders_percent', 100)
            if top10_percent < 50:
                score += 0.3
            elif top10_percent < 70:
                score += 0.15
            
            # Factor 3: Good liquidity (30%)
            liquidity = token_data.get('liquidity_usd', 0)
            if liquidity > 100000:
                score += 0.3
            elif liquidity > 50000:
                score += 0.15
            
            analysis['smart_money_score'] = min(score, 1.0)
            
            # Determine market phase
            volume_ratio = token_data.get('volume_liquidity_ratio', 0)
            if volume_ratio > 0.5 and len(smart_holders) > 0:
                analysis['accumulation_phase'] = True
            elif volume_ratio < 0.1 and len(smart_holders) == 0:
                analysis['distribution_phase'] = True
            
            # Set confidence based on data availability
            if holder_addresses:
                analysis['confidence'] = 0.8
            else:
                analysis['confidence'] = 0.3
            
        except Exception as e:
            print(f"Smart money analysis error: {e}")
        
        return analysis
    
    async def get_top_smart_wallets(self, limit: int = 100) -> List[Dict]:
        """Get top performing smart wallets from database"""
        async with get_db() as db:
            try:
                result = await db.execute(
                    select(SmartWallet)
                    .order_by(SmartWallet.win_rate.desc())
                    .limit(limit)
                )
                wallets = result.scalars().all()
                
                return [
                    {
                        'address': w.wallet_address,
                        'total_trades': w.total_trades,
                        'profitable_trades': w.profitable_trades,
                        'win_rate': w.win_rate,
                        'average_return': w.average_return,
                        'last_activity': w.last_activity.isoformat() if w.last_activity else None
                    }
                    for w in wallets
                ]
            except Exception as e:
                print(f"Database error: {e}")
                # Return mock data for testing
                return [
                    {
                        'address': '0x742d35Cc6634C0532925a3b844Bc9e7595f8b399',
                        'total_trades': 156,
                        'profitable_trades': 134,
                        'win_rate': 0.859,
                        'average_return': 3.4,
                        'last_activity': datetime.now().isoformat()
                    }
                ]
    
    async def update_smart_wallet_metrics(self, wallet_address: str, trade_result: Dict):
        """Update smart wallet performance metrics"""
        async with get_db() as db:
            try:
                # Get or create wallet
                result = await db.execute(
                    select(SmartWallet).where(SmartWallet.wallet_address == wallet_address)
                )
                wallet = result.scalar_one_or_none()
                
                if not wallet:
                    wallet = SmartWallet(wallet_address=wallet_address)
                    db.add(wallet)
                
                # Update metrics
                wallet.total_trades += 1
                if trade_result.get('profitable', False):
                    wallet.profitable_trades += 1
                
                wallet.win_rate = wallet.profitable_trades / wallet.total_trades
                wallet.last_activity = datetime.now()
                
                await db.commit()
                
            except Exception as e:
                print(f"Error updating wallet metrics: {e}")
                await db.rollback()