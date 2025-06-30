class ScamDetector:
    def __init__(self):
        self.blacklist = set()

    async def quick_check(self, token_address, chain_id):
        return token_address in self.blacklist

    async def deep_check(self, onchain, social, docs, github):
        risk = 0
        if social.get("bot_score", 1) > 0.5: risk += 1
        if docs.get("plagiarized"): risk += 1
        if not docs.get("team_doxxed"): risk += 1
        if github.get("forked_from_scam"): risk += 1
        return risk > 1
