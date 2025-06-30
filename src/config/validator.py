import os
import asyncio
from typing import List, Dict, Any
from loguru import logger
from .settings import settings
from .database import init_database

class ConfigValidator:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_api_keys(self) -> bool:
        """Validate required API keys"""
        required_keys = ['ETHERSCAN_API_KEY']
        optional_keys = ['BSCSCAN_API_KEY', 'POLYGONSCAN_API_KEY']
        
        for key in required_keys:
            if not getattr(settings, key, None):
                self.errors.append(f"Missing required API key: {key}")
        
        for key in optional_keys:
            if not getattr(settings, key, None):
                self.warnings.append(f"Optional API key not set: {key}")
        
        return len(self.errors) == 0
    
    def validate_security(self) -> bool:
        """Validate security configuration"""
        if len(settings.SECRET_KEY) < 32:
            self.errors.append("SECRET_KEY must be at least 32 characters")
        
        if settings.SECRET_KEY == "your-secret-key-here":
            self.errors.append("Please change the default SECRET_KEY")
        
        return len(self.errors) == 0
    
    async def validate_database(self) -> bool:
        """Test database connectivity"""
        return await init_database()
    
    async def validate_redis(self) -> bool:
        """Test Redis connectivity"""
        try:
            import redis.asyncio as redis
            r = redis.from_url(settings.REDIS_URL)
            await r.ping()
            await r.close()
            logger.info("Redis connection successful")
            return True
        except Exception as e:
            self.errors.append(f"Redis connection failed: {e}")
            return False
    
    async def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation checks"""
        results = {
            'api_keys': self.validate_api_keys(),
            'security': self.validate_security(),
            'database': await self.validate_database(),
            'redis': await self.validate_redis(),
            'errors': self.errors,
            'warnings': self.warnings
        }
        
        all_passed = all(results[key] for key in ['api_keys', 'security', 'database', 'redis'])
        results['overall'] = all_passed
        
        return results

async def validate_environment():
    """Main validation function"""
    validator = ConfigValidator()
    results = await validator.run_all_validations()
    
    if results['errors']:
        logger.error("Environment validation failed:")
        for error in results['errors']:
            logger.error(f"  ❌ {error}")
    
    if results['warnings']:
        logger.warning("Environment warnings:")
        for warning in results['warnings']:
            logger.warning(f"  ⚠️  {warning}")
    
    if results['overall']:
        logger.success("✅ Environment validation passed!")
    else:
        logger.error("❌ Environment validation failed!")
        exit(1)
    
    return results
