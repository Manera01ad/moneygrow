class AgentEvaluator:
    def evaluate_analysis(self, analysis):
        score = 0
        if analysis['onchain'].get('liquidity', 0) > 50000:
            score += 0.2
        if analysis['social'].get('bot_score', 1) < 0.3:
            score += 0.2
        if not analysis['docs'].get('plagiarized', True):
            score += 0.2
        if analysis['docs'].get('team_doxxed', False):
            score += 0.2
        if analysis['onchain'].get('ownership_renounced', False):
            score += 0.2
        return min(score, 1.0)
