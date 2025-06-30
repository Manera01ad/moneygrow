from typing import Dict, List
from datetime import datetime

class CryptoClassifier:
    """
    Analyzes crypto coins to classify them as meme or naive based on social and market data.
    """
    
    def __init__(self):
        self.meme_keywords = ['meme', 'doge', 'shiba', 'elon', 'to the moon']
        self.naive_keywords = ['technology', 'blockchain', 'utility', 'enterprise']
    
    def classify_by_social_patterns(self, social_data: List[Dict]) -> str:
        """
        Classifies coin based on social media patterns and keywords.
        Returns 'meme' or 'naive'
        """
        meme_score = 0
        naive_score = 0
        
        for post in social_data:
            text = post.get('text', '').lower()
            
            if any(keyword in text for keyword in self.meme_keywords):
                meme_score += 1
            elif any(keyword in text for keyword in self.naive_keywords):
                naive_score += 1
        
        return 'meme' if meme_score > naive_score else 'naive'
    
    def classify_by_market_behavior(self, price_data: Dict) -> str:
        """
        Classifies coin based on market behavior patterns.
        Returns 'meme' or 'naive'
        """
        # TODO: Implement market behavior analysis
        return 'naive'
    
    def get_combined_classification(self, social_data: List[Dict], price_data: Dict) -> str:
        """
        Returns final classification combining social and market analysis.
        """
        social_class = self.classify_by_social_patterns(social_data)
        market_class = self.classify_by_market_behavior(price_data)
        
        # Simple majority voting for now
        return social_class if social_class == market_class else 'naive'