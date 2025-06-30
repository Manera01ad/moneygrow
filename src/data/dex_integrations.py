import aiohttp
from typing import Dict, Optional, List
from abc import ABC, abstractmethod

class BaseDEXIntegration(ABC):
    """Base class for DEX integrations"""
    
    @abstractmethod
    async def get_token_data(self, token_address: str, chain_id: int) -> Dict:
        pass
    
    @abstractmethod
    def supports_chain(self, chain_id: int) -> bool:
        pass

class DexScreenerIntegration(BaseDEXIntegration):
    """DexScreener.com integration"""
    
    def __init__(self):
        self.base_url = "https://api.dexscreener.com/latest/dex"
        self.chain_map = {
            1: "ethereum",
            56: "bsc",
            137: "polygon",
            42161: "arbitrum",
            10: "optimism"
        }
    
    def supports_chain(self, chain_id: int) -> bool:
        return chain_id in self.chain_map
    
    async def get_token_data(self, token_address: str, chain_id: int) -> Dict:
        if not self.supports_chain(chain_id):
            return {}
        
        chain = self.chain_map[chain_id]
        url = f"{self.base_url}/tokens/{token_address}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get('pairs', [])
                        
                        if pairs:
                            # Aggregate data from all pairs
                            total_liquidity = sum(float(p.get('liquidity', {}).get('usd', 0)) for p in pairs)
                            total_volume = sum(float(p.get('volume', {}).get('h24', 0)) for p in pairs)
                            
                            # Get price from most liquid pair
                            pairs.sort(key=lambda x: float(x.get('liquidity', {}).get('usd', 0)), reverse=True)
                            main_pair = pairs[0]
                            
                            return {
                                'price_usd': float(main_pair.get('priceUsd', 0)),
                                'liquidity_usd': total_liquidity,
                                'volume_24h': total_volume,
                                'price_change_24h_percent': float(main_pair.get('priceChange', {}).get('h24', 0)),
                                'market_cap': float(main_pair.get('marketCap', 0)),
                                'pair_count': len(pairs),
                                'dex_source': 'dexscreener'
                            }
            except Exception as e:
                print(f"DexScreener error: {e}")
        
        return {}

class DEXToolsIntegration(BaseDEXIntegration):
    """DEXTools integration (requires API key)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.dextools.io/v1"
        self.chain_map = {
            1: "ether",
            56: "bsc",
            137: "polygon"
        }
    
    def supports_chain(self, chain_id: int) -> bool:
        return chain_id in self.chain_map and self.api_key
    
    async def get_token_data(self, token_address: str, chain_id: int) -> Dict:
        if not self.supports_chain(chain_id):
            return {}
        
        chain = self.chain_map[chain_id]
        url = f"{self.base_url}/token/{chain}/{token_address}"
        headers = {"X-API-Key": self.api_key}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return {
                            'price_usd': float(data.get('price', 0)),
                            'liquidity_usd': float(data.get('liquidity', 0)),
                            'volume_24h': float(data.get('volume24h', 0)),
                            'holders': int(data.get('holders', 0)),
                            'dex_source': 'dextools',
                            'audit_results': data.get('audit', {}),
                            'score': data.get('score', 0)
                        }
            except Exception as e:
                print(f"DEXTools error: {e}")
        
        return {}

class MultiDEXAggregator:
    """Aggregate data from multiple DEX sources"""
    
    def __init__(self, settings):
        self.integrations = [
            DexScreenerIntegration(),
        ]
        
        # Add DEXTools if API key available
        if settings.DEXTOOLS_API_KEY:
            self.integrations.append(DEXToolsIntegration(settings.DEXTOOLS_API_KEY))
    
    async def get_aggregated_data(self, token_address: str, chain_id: int) -> Dict:
        """Get data from all available DEX sources"""
        results = []
        
        for integration in self.integrations:
            if integration.supports_chain(chain_id):
                data = await integration.get_token_data(token_address, chain_id)
                if data:
                    results.append(data)
        
        if not results:
            return {}
        
        # Aggregate results
        aggregated = {
            'price_usd': 0,
            'liquidity_usd': 0,
            'volume_24h': 0,
            'price_change_24h_percent': 0,
            'market_cap': 0,
            'sources': []
        }

        # Find the result from the source with the highest liquidity
        if not results:
            return aggregated
            
        primary_source = max(results, key=lambda r: r.get('liquidity_usd', 0))

        # Use data from the primary source, then fill from others if needed
        aggregated['price_usd'] = primary_source.get('price_usd', 0)
        aggregated['price_change_24h_percent'] = primary_source.get('price_change_24h_percent', 0)
        aggregated['market_cap'] = primary_source.get('market_cap', 0)

        # Sum liquidity and volume from all sources
        aggregated['liquidity_usd'] = sum(r.get('liquidity_usd', 0) for r in results)
        aggregated['volume_24h'] = sum(r.get('volume_24h', 0) for r in results)
        aggregated['sources'] = [r.get('dex_source') for r in results if r.get('dex_source')]

        # Include additional data if available from any source
        for r in results:
            if 'audit_results' in r and 'audit_results' not in aggregated:
                aggregated['audit_results'] = r['audit_results']
            if 'score' in r and 'dextools_score' not in aggregated:
                aggregated['dextools_score'] = r['score']
        
        return aggregated