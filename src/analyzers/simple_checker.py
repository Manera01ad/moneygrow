class SimpleRiskChecker:
    def check_basic_risks(self, token_data: dict) -> dict:
        risks = []
        
        # Add simple checks
        if token_data.get('holder_count', 0) < 50:
            risks.append("Too few holders")
            
        risk_score = len(risks) * 0.25  # Simple scoring
        
        return {
            "risks": risks,
            "risk_score": min(risk_score, 1.0)
        }
