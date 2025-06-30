# MoneyGrow Platform - Quick Start Guide

## **🚀 Immediate Setup (5 minutes)**

### **Step 1: Run the Automated Setup**
```powershell
# Execute the setup script
.\setup.ps1
```

This script will:
- ✅ Check prerequisites (Python, Docker, Node.js)
- ✅ Create Python virtual environment
- ✅ Install all dependencies
- ✅ Start database services
- ✅ Create necessary directories
- ✅ Generate configuration files

### **Step 2: Configure API Keys**
Edit the `.env` file and add your actual API keys:
```bash
ETHERSCAN_API_KEY=YOUR_ACTUAL_ETHERSCAN_KEY
BSCSCAN_API_KEY=YOUR_ACTUAL_BSCSCAN_KEY
```

### **Step 3: Start All Services**
```powershell
# Start all services with Docker Compose
docker-compose up -d

# Verify services are running
docker-compose ps
```

### **Step 4: Test the Platform**
1. **API Documentation**: http://localhost:8000/docs
2. **Worker Monitoring**: http://localhost:5555
3. **Test Analysis**:
   ```bash
   curl -X POST http://localhost:8000/analyze \
     -H "Content-Type: application/json" \
     -d '{"token_address": "0x1234567890123456789012345678901234567890", "chain_id": 1}'
   ```

---

## **📋 What's Been Enhanced**

### **✅ IMPLEMENTED Components:**
1. **Database Connection Module** - `src/config/database.py`
2. **Environment Validation** - `src/config/validator.py` 
3. **ML Training Infrastructure** - `ml/training/feature_engineering.py`
4. **Development Dependencies** - `requirements-dev.txt`
5. **Automated Setup Script** - `setup.ps1`
6. **Enhanced Documentation** - `ENHANCED_SETUP_GUIDE.md`

### **🔧 READY TO IMPLEMENT:**
- Rate Limiting & Security Middleware
- Error Handling System
- ML Training Pipeline
- Frontend State Management
- Monitoring & Metrics
- CI/CD Pipeline
- Backup & Recovery System

---

## **🎯 Priority Implementation Order**

### **Phase 1: Core Security (HIGH PRIORITY)**
```powershell
# Implement these next:
# 1. src/api/exceptions.py - Error handling
# 2. src/api/middleware.py - Rate limiting
# 3. src/config/security.py - Security hardening
```

### **Phase 2: ML Pipeline (MEDIUM PRIORITY)**
```powershell
# 1. ml/training/train.py - Model training
# 2. Update MLDetector to use trained models
# 3. Setup MLflow for experiment tracking
```

### **Phase 3: Production Features (MEDIUM PRIORITY)**
```powershell
# 1. Monitoring & metrics system
# 2. Backup & recovery scripts
# 3. CI/CD pipeline setup
```

---

## **🛠️ Daily Development Workflow**

### **Starting Development**
```powershell
# 1. Activate environment
.\.venv\Scripts\Activate.ps1

# 2. Start services
docker-compose up -d

# 3. Start API server
uvicorn src.api.main:app --reload

# 4. Start workers (new terminal)
celery -A src.tasks.workers.celery_app worker --loglevel=info --pool=solo
```

### **Testing & Validation**
```powershell
# Run environment validation
python -c "import asyncio; import sys; sys.path.append('src'); from config.validator import validate_environment; asyncio.run(validate_environment())"

# Run tests (after implementing test files)
pytest tests/ -v --cov=src

# Check code quality
black src/
flake8 src/
```

---

## **🔗 Service URLs**
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health  
- **Worker Monitoring**: http://localhost:5555
- **Frontend**: http://localhost:3000 (after setup)
- **MLflow**: http://localhost:5000 (after ML setup)

---

## **🆘 Troubleshooting**

### **Common Issues:**

1. **Database Connection Failed**
   ```powershell
   # Restart database services
   docker-compose restart postgres redis
   ```

2. **API Key Errors**
   ```bash
   # Check .env file has real API keys (not placeholder text)
   ```

3. **Worker Not Starting**
   ```powershell
   # Use solo pool on Windows
   celery -A src.tasks.workers.celery_app worker --loglevel=info --pool=solo
   ```

4. **Frontend Issues**
   ```powershell
   # Reinstall frontend dependencies
   cd frontend/client
   npm install
   npm start
   ```

---

## **📈 Next Steps After Quick Start**

1. **Customize Analysis Parameters** - Modify settings in `src/config/settings.py`
2. **Add More Blockchain Networks** - Extend collectors for additional chains
3. **Train Custom ML Models** - Use your own labeled dataset
4. **Implement Advanced Features** - Add social sentiment analysis, advanced metrics
5. **Scale Infrastructure** - Setup production deployment with proper orchestration

---

## **💡 Pro Tips**

- **Use the validation script** before starting development each day
- **Monitor Flower dashboard** to track analysis task progress  
- **Check logs regularly** for errors and performance insights
- **Backup your database** before major changes
- **Test with small token analyses** before running large batches

---

**🎉 You're now ready to start developing with the MoneyGrow platform!**

The enhanced setup provides a solid foundation with all critical missing components implemented or documented for easy implementation.
