import pandas as pd
import numpy as np
from typing import Dict, Any, List
from loguru import logger

class FeatureEngineer:
    def __init__(self):
        self.feature_names = []
    
    def extract_features(self, token_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from token data for ML model"""
        features = {}
        
        # Basic token metrics
        features['liquidity_usd'] = token_data.get('liquidity_usd', 0)
        features['holder_count'] = token_data.get('holder_count', 0)
        features['total_supply'] = token_data.get('total_supply', 0)
        features['market_cap'] = token_data.get('market_cap', 0)
        
        # Contract features
        features['is_verified'] = float(token_data.get('is_verified', False))
        features['has_honeypot'] = float(token_data.get('has_honeypot', False))
        features['buy_tax'] = token_data.get('buy_tax', 0)
        features['sell_tax'] = token_data.get('sell_tax', 0)
        
        # Liquidity features
        features['liquidity_locked'] = float(token_data.get('liquidity_locked', False))
        features['liquidity_lock_duration'] = token_data.get('liquidity_lock_duration', 0)
        
        # Holder distribution features
        top_10_percent = token_data.get('top_10_holders_percent', 0)
        features['top_10_concentration'] = top_10_percent
        features['whale_concentration'] = float(top_10_percent > 50)
        
        # Social features
        features['twitter_followers'] = token_data.get('twitter_followers', 0)
        features['telegram_members'] = token_data.get('telegram_members', 0)
        features['github_commits'] = token_data.get('github_commits', 0)
        
        # Trading features
        features['volume_24h'] = token_data.get('volume_24h', 0)
        features['price_change_24h'] = token_data.get('price_change_24h', 0)
        features['trades_24h'] = token_data.get('trades_24h', 0)
        
        # Derived features
        if features['total_supply'] > 0:
            features['market_cap_to_supply_ratio'] = features['market_cap'] / features['total_supply']
        else:
            features['market_cap_to_supply_ratio'] = 0
        
        if features['holder_count'] > 0:
            features['market_cap_per_holder'] = features['market_cap'] / features['holder_count']
        else:
            features['market_cap_per_holder'] = 0
        
        # Risk indicators
        features['high_tax'] = float(features['buy_tax'] > 10 or features['sell_tax'] > 10)
        features['low_liquidity'] = float(features['liquidity_usd'] < 10000)
        features['few_holders'] = float(features['holder_count'] < 50)
        
        self.feature_names = list(features.keys())
        return features
    
    def create_feature_vector(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dict to numpy array"""
        return np.array([features.get(name, 0) for name in self.feature_names])
    
    def get_feature_importance(self, model, feature_names: List[str] = None) -> Dict[str, float]:
        """Get feature importance from trained model"""
        if feature_names is None:
            feature_names = self.feature_names
        
        if hasattr(model, 'feature_importances_'):
            importance_dict = {}
            for name, importance in zip(feature_names, model.feature_importances_):
                importance_dict[name] = importance
            return importance_dict
        else:
            logger.warning("Model does not have feature_importances_ attribute")
            return {}
    
    def normalize_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """Apply basic normalization to features"""
        normalized = features.copy()
        
        # Log transform for highly skewed features
        log_features = ['liquidity_usd', 'market_cap', 'volume_24h', 'total_supply']
        for feature in log_features:
            if feature in normalized and normalized[feature] > 0:
                normalized[feature] = np.log1p(normalized[feature])
        
        # Cap outliers
        cap_features = ['buy_tax', 'sell_tax', 'price_change_24h']
        for feature in cap_features:
            if feature in normalized:
                normalized[feature] = np.clip(normalized[feature], -100, 100)
        
        return normalized
