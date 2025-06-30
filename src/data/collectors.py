import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from web3 import Web3
import json

from ..config.settings import settings
from ..utils.cache import cache
from .dex_integrations import MultiDEXAggregator
from .security_analyzer import SecurityAnalyzer

class DataCollector:
    """Collect comprehensive token data from multiple sources"""
    def __init__(self):
        self.settings = settings
        self.session = None
        self.web3_connections = self._init_web3_connections()
        self.dex_aggregator = MultiDEXAggregator(self.settings)
        if self.session:
            self.security_analyzer = SecurityAnalyzer(self.settings.GOPLUS_API_KEY, self.session)
        else:
            self.security_analyzer = None
    
    def _init_web3_connections(self) -> Dict:
        return {
            1: Web3(Web3.HTTPProvider(self.settings.ETH_RPC)),
            56: Web3(Web3.HTTPProvider(self.settings.BSC_RPC)),
            137: Web3(Web3.HTTPProvider(self.settings.POLYGON_RPC)),
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.security_analyzer = SecurityAnalyzer(self.settings.GOPLUS_API_KEY, self.session)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def collect_all_data(self, token_address: str, chain_id: int) -> Dict:
        """Collect all available data for a token"""
        cache_key = f"{chain_id}:{token_address}"
        cached_data = cache.get(cache_key)
        if cached_data:
            print(f"Returning cached data for {token_address}")
            return cached_data
        if not self.session:
            self.session = aiohttp.ClientSession()
        tasks = [
            self.collect_dex_data(token_address, chain_id),
            self.collect_etherscan_data(token_address, chain_id),
            self.collect_holder_data(token_address, chain_id),
            self.collect_contract_data(token_address, chain_id),
            self.collect_security_data(token_address, chain_id),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        token_data = {
            'address': token_address,
            'chain_id': chain_id,
            'timestamp': datetime.now()
        }
        for result in results:
            if isinstance(result, dict):
                token_data.update(result)
            else:
                print(f"Error collecting data: {result}")
        token_data = self._calculate_additional_metrics(token_data)
        cache.set(cache_key, token_data, ttl=60)
        return token_data
    
    async def collect_dex_data(self, token_address: str, chain_id: int) -> Dict:
        """Collects DEX data using the MultiDEXAggregator."""
        try:
            dex_data = await self.dex_aggregator.get_aggregated_data(token_address, chain_id)
            if not dex_data:
                return self._get_default_dex_data()
            
            # The aggregator now returns a more comprehensive dictionary.
            # We can add any additional processing here if needed, but for now,
            # we will return the aggregated data directly.
            return dex_data
        except Exception as e:
            print(f"DEX data collection error: {e}")
            return self._get_default_dex_data()
    
    async def collect_etherscan_data(self, token_address: str, chain_id: int) -> Dict:
        if chain_id == 1:
            api_key = self.settings.ETHERSCAN_API_KEY
            base_url = "https://api.etherscan.io/api"
        elif chain_id == 56:
            api_key = self.settings.BSCSCAN_API_KEY
            base_url = "https://api.bscscan.com/api"
        else:
            return {}
        if not api_key:
            return {}
        try:
            supply_params = {
                "module": "stats",
                "action": "tokensupply",
                "contractaddress": token_address,
                "apikey": api_key
            }
            async with self.session.get(base_url, params=supply_params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == '1':
                        total_supply = float(data.get('result', 0))
                    else:
                        total_supply = 0
            contract_params = {
                "module": "contract",
                "action": "getsourcecode",
                "address": token_address,
                "apikey": api_key
            }
            async with self.session.get(base_url, params=contract_params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == '1' and data.get('result'):
                        contract_info = data['result'][0]
                        source_code = contract_info.get('SourceCode', '')
                        return {
                            'contract_verified': len(source_code) > 0,
                            'contract_name': contract_info.get('ContractName', ''),
                            'compiler_version': contract_info.get('CompilerVersion', ''),
                            'optimization_used': contract_info.get('OptimizationUsed', '0') == '1',
                            'is_proxy': 'proxy' in source_code.lower() if source_code else False,
                            'has_mint_function': 'mint' in source_code.lower() if source_code else False,
                            'has_pause_function': 'pause' in source_code.lower() if source_code else False,
                            'ownership_renounced': self._check_ownership_renounced(source_code),
                            'total_supply_etherscan': total_supply
                        }
            return {'contract_verified': False}
        except Exception as e:
            print(f"Etherscan error: {e}")
            return {'contract_verified': False}
    
    async def collect_holder_data(self, token_address: str, chain_id: int) -> Dict:
        if chain_id == 1:
            api_key = self.settings.ETHERSCAN_API_KEY
            base_url = "https://api.etherscan.io/api"
        elif chain_id == 56:
            api_key = self.settings.BSCSCAN_API_KEY
            base_url = "https://api.bscscan.com/api"
        else:
            return self._get_default_holder_data()
        if not api_key:
            return self._get_default_holder_data()
        try:
            params = {
                "module": "token",
                "action": "tokenholderlist",
                "contractaddress": token_address,
                "page": "1",
                "offset": "100",
                "apikey": api_key
            }
            async with self.session.get(base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == '1' and data.get('result'):
                        holders = data['result']
                        total_holders = len(holders)
                        if total_holders > 0:
                            total_supply = sum(float(h.get('TokenHolderQuantity', 0)) for h in holders)
                            holders.sort(key=lambda x: float(x.get('TokenHolderQuantity', 0)), reverse=True)
                            top_holder_balance = float(holders[0].get('TokenHolderQuantity', 0))
                            top10_balance = sum(float(h.get('TokenHolderQuantity', 0)) for h in holders[:10])
                            return {
                                'holder_count': total_holders,
                                'top_holder_percent': (top_holder_balance / total_supply * 100) if total_supply > 0 else 0,
                                'top10_holders_percent': (top10_balance / total_supply * 100) if total_supply > 0 else 0,
                                'holder_addresses': [h.get('TokenHolderAddress') for h in holders[:20]]
                            }
            return self._get_default_holder_data()
        except Exception as e:
            print(f"Holder data error: {e}")
            return self._get_default_holder_data()
    
    async def collect_contract_data(self, token_address: str, chain_id: int) -> Dict:
        try:
            web3 = self.web3_connections.get(chain_id)
            if not web3:
                return {}
            latest_block = web3.eth.block_number
            blocks_per_day = 6500 if chain_id == 1 else 28800
            contract_age_days = 30
            return {
                'contract_created_at': datetime.now() - timedelta(days=contract_age_days),
                'latest_block': latest_block,
                'contract_age_estimate': True
            }
        except Exception as e:
            print(f"Web3 error: {e}")
            return {'contract_created_at': datetime.now() - timedelta(days=30)}
    
    async def collect_security_data(self, token_address: str, chain_id: int) -> Dict:
        """Collects security data using the SecurityAnalyzer."""
        if not self.security_analyzer:
            return {}
        try:
            security_data = await self.security_analyzer.get_token_security(token_address, chain_id)
            return security_data
        except Exception as e:
            print(f"Security data collection error: {e}")
            return {}

    def _calculate_additional_metrics(self, token_data: Dict) -> Dict:
        volume = token_data.get('volume_24h', 0)
        liquidity = token_data.get('liquidity_usd', 1)
        token_data['volume_liquidity_ratio'] = volume / liquidity if liquidity > 0 else 0
        market_cap = token_data.get('market_cap', 1)
        token_data['liquidity_market_cap_ratio'] = liquidity / market_cap if market_cap > 0 else 0
        
        # These are now fetched from GoPlus, but we can add fallbacks
        token_data.setdefault('can_sell', not token_data.get('cannot_sell_all', True))
        token_data.setdefault('sell_tax', token_data.get('sell_tax', 100.0))
        token_data.setdefault('buy_tax', token_data.get('buy_tax', 100.0))

        # Mocked data that still needs real implementation
        token_data['buys_24h'] = 100
        token_data['sells_24h'] = 80
        token_data['unique_buyers_24h'] = 50
        token_data['unique_sellers_24h'] = 40
        return token_data
    
    def _check_ownership_renounced(self, source_code: str) -> bool:
        if not source_code:
            return False
        renounce_indicators = [
            'renounceOwnership',
            'owner = address(0)',
            'owner = 0x0000000000000000000000000000000000000000'
        ]
        return any(indicator in source_code for indicator in renounce_indicators)
    
    def _get_default_dex_data(self) -> Dict:
        return {
            'liquidity_usd': 0,
            'volume_24h': 0,
            'price_usd': 0,
            'price_change_24h_percent': 0,
            'market_cap': 0,
            'pool_count': 0
        }
    
    def _get_default_holder_data(self) -> Dict:
        return {
            'holder_count': 0,
            'top_holder_percent': 100,
            'top10_holders_percent': 100,
            'holder_addresses': []
        }
