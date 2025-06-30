import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import joblib
from datetime import datetime
from pathlib import Path
import os

from ..config.settings import settings

class MLScamDetector:
    """Machine Learning based scam detection"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.load_models()
        
    def load_models(self):
        """Load pre-trained models if they exist"""
        model_path = Path(settings.SCAM_MODEL_PATH)
        scaler_path = Path(settings.SCALER_PATH)
        
        if model_path.exists() and scaler_path.exists():
            try:
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                self.feature_names = self._get_feature_names()
                print("ML models loaded successfully")
            except Exception as e:
                print(f"Warning: Could not load ML models: {e}")
                self._use_simple_model()
        else:
            print("ML models not found, using simple heuristic model")
            self._use_simple_model()
    
    def _use_simple_model(self):
        """Use a simple heuristic model as fallback"""
        self.model = None
        self.feature_names = self._get_feature_names()
    
    def _get_feature_names(self) -> List[str]:
        """Get list of feature names"""
        return [
            'liquidity_usd_log',
            'volume_24h_log',
            'holder_count_log',
            'top10_holders_percent',
            'contract_age_hours',
            'contract_verified',
            'ownership_renounced',
            'has_mint_function',
            'liquidity_market_cap_ratio',
            'volume_liquidity_ratio',
            'price_change_24h_abs',
            'pool_count',
        ]
    
    async def predict_scam_probability(self, token_data: Dict) -> Dict:
        """Predict scam probability using ML model or heuristics"""
        try:
            # Extract features
            features = self.extract_features(token_data)
            
            if self.model is not None:
                # Use ML model
                feature_vector = [features.get(name, 0) for name in self.feature_names]
                X = np.array(feature_vector).reshape(1, -1)
                X_scaled = self.scaler.transform(X)
                
                scam_probability = self.model.predict_proba(X_scaled)[0][1]
                prediction = 'SCAM' if scam_probability > 0.5 else 'SAFE'
                confidence = abs(scam_probability - 0.5) * 2
                
            else:
                # Use heuristic scoring
                scam_probability = self._heuristic_scoring(features, token_data)
                prediction = 'SCAM' if scam_probability > 0.5 else 'SAFE'
                confidence = 0.7  # Fixed confidence for heuristic
            
            # Get top risk factors
            top_risk_factors = self._get_top_risk_factors(features, token_data)
            
            return {
                'scam_probability': float(scam_probability),
                'prediction': prediction,
                'confidence': float(confidence),
                'model_available': self.model is not None,
                'top_risk_factors': top_risk_factors
            }
            
        except Exception as e:
            print(f"ML prediction error: {e}")
            return {
                'scam_probability': 0.5,
                'confidence': 0.0,
                'model_available': False,
                'error': str(e),
                'top_risk_factors': []
            }
    
    def extract_features(self, token_data: Dict) -> Dict:
        """Extract ML features from token data"""
        features = {}
        
        # Liquidity features
        liquidity = token_data.get('liquidity_usd', 0)
        features['liquidity_usd_log'] = np.log1p(liquidity)
        
        # Volume features
        volume = token_data.get('volume_24h', 0)
        features['volume_24h_log'] = np.log1p(volume)
        features['volume_liquidity_ratio'] = volume / max(liquidity, 1)
        
        # Holder features
        features['holder_count_log'] = np.log1p(token_data.get('holder_count', 0))
        features['top10_holders_percent'] = token_data.get('top10_holders_percent', 100)
        
        # Contract features
        features['contract_verified'] = int(token_data.get('contract_verified', False))
        features['ownership_renounced'] = int(token_data.get('ownership_renounced', False))
        features['has_mint_function'] = int(token_data.get('has_mint_function', False))
        
        # Contract age
        created_at = token_data.get('contract_created_at')
        if isinstance(created_at, datetime):
            age_hours = (datetime.now() - created_at).total_seconds() / 3600
            features['contract_age_hours'] = min(age_hours, 720)  # Cap at 30 days
        else:
            features['contract_age_hours'] = 720  # Default to 30 days
        
        # Market metrics
        market_cap = token_data.get('market_cap', 1)
        features['liquidity_market_cap_ratio'] = liquidity / max(market_cap, 1)
        
        # Price features
        features['price_change_24h_abs'] = abs(token_data.get('price_change_24h_percent', 0))
        
        # DEX features
        features['pool_count'] = token_data.get('pool_count', 0)
        
        return features
    
    def _heuristic_scoring(self, features: Dict, token_data: Dict) -> float:
        """Simple heuristic scoring when ML model not available"""
        score = 0.0
        
        # Low liquidity
        if features['liquidity_usd_log'] < np.log1p(10000):
            score += 0.3
        
        # High holder concentration
        if features['top10_holders_percent'] > 70:
            score += 0.2
        
        # Unverified contract
        if not features['contract_verified']:
            score += 0.2
        
        # Has mint function
        if features['has_mint_function'] and not features['ownership_renounced']:
            score += 0.2
        
        # New contract
        if features['contract_age_hours'] < 168:  # Less than 1 week
            score += 0.1
        
        # Low volume/liquidity ratio
        if features['volume_liquidity_ratio'] < 0.1:
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_top_risk_factors(self, features: Dict, token_data: Dict) -> List[Dict]:
        """Identify top risk factors"""
        risk_factors = []
        
        # Check each risk factor
        if features['liquidity_usd_log'] < np.log1p(10000):
            risk_factors.append({
                'factor': 'Low Liquidity',
                'value': f"${token_data.get('liquidity_usd', 0):,.0f}",
                'risk_contribution': 0.3
            })
        
        if features['top10_holders_percent'] > 70:
            risk_factors.append({
                'factor': 'High Concentration',
                'value': f"{features['top10_holders_percent']:.1f}% in top 10",
                'risk_contribution': 0.2
            })
        
        if not features['contract_verified']:
            risk_factors.append({
                'factor': 'Unverified Contract',
                'value': 'Source code not verified',
                'risk_contribution': 0.2
            })
        
        if features['has_mint_function'] and not features['ownership_renounced']:
            risk_factors.append({
                'factor': 'Mint Risk',
                'value': 'Can create new tokens',
                'risk_contribution': 0.2
            })
        
        # Sort by risk contribution
        risk_factors.sort(key=lambda x: x['risk_contribution'], reverse=True)
        
        return risk_factors[:5]