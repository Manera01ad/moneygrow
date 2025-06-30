import aiohttp
from ..config.settings import settings

class BasicDataCollector:
    async def get_token_info(self, token_address: str, chain_id: int):
        """Get basic token info from Etherscan"""
        # Simple Etherscan API call
        url = f"https://api.etherscan.io/api"
        params = {
            "module": "token",
            "action": "tokeninfo",
            "contractaddress": token_address,
            "apikey": settings.ETHERSCAN_API_KEY
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                return await response.json()
