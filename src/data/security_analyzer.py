import aiohttp
from typing import Dict, Optional

class SecurityAnalyzer:
    """
    Analyzer for fetching token security data from GoPlus Security API.
    """
    def __init__(self, api_key: str, session: aiohttp.ClientSession):
        self.api_key = api_key
        self.base_url = "https://api.gopluslabs.io/api/v1"
        self.session = session
        self.headers = {"Authorization": api_key} if api_key else {}
        self.chain_map = {
            1: "1",      # Ethereum
            56: "56",    # BSC
            137: "137",  # Polygon
            42161: "42161", # Arbitrum
            8453: "8453", # Base
            10: "10"     # Optimism
        }

    async def get_token_security(self, token_address: str, chain_id: int) -> Dict:
        """
        Fetches comprehensive security data for a given token.
        """
        if not self.api_key or chain_id not in self.chain_map:
            return self._get_default_security_data()

        chain_id_str = self.chain_map[chain_id]
        url = f"{self.base_url}/token_security/{chain_id_str}?contract_addresses={token_address}"

        try:
            async with self.session.get(url, headers=self.headers, timeout=15) as response:
                if response.status != 200:
                    print(f"GoPlus API Error: Status {response.status}")
                    return self._get_default_security_data()
                
                data = await response.json()
                if not data or data.get('code') != 1:
                    print(f"GoPlus API Error: {data.get('message', 'Unknown error')}")
                    return self._get_default_security_data()

                result = data.get('result', {}).get(token_address.lower(), {})
                return self._parse_security_data(result)

        except Exception as e:
            print(f"Error fetching GoPlus security data: {e}")
            return self._get_default_security_data()

    def _parse_security_data(self, result: Dict) -> Dict:
        """
        Parses the raw API response into a structured dictionary.
        """
        if not result:
            return self._get_default_security_data()

        return {
            'is_honeypot': result.get('is_honeypot') == '1',
            'buy_tax': float(result.get('buy_tax', 100)),
            'sell_tax': float(result.get('sell_tax', 100)),
            'cannot_sell_all': result.get('cannot_sell_all') == '1',
            'is_open_source': result.get('is_open_source') == '1',
            'owner_address': result.get('owner_address'),
            'is_proxy': result.get('is_proxy') == '1',
            'is_mintable': result.get('is_mintable') == '1',
            'goplus_security_data': True
        }

    def _get_default_security_data(self) -> Dict:
        """
        Returns a default dictionary when API call fails or data is unavailable.
        """
        return {
            'is_honeypot': True,
            'buy_tax': 100.0,
            'sell_tax': 100.0,
            'cannot_sell_all': True,
            'is_open_source': False,
            'owner_address': None,
            'is_proxy': False,
            'is_mintable': False,
            'goplus_security_data': False
        }