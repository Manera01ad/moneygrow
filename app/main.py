from fastapi import FastAPI, Request
from pydantic import BaseModel
from .agent_logic import run_agent
from .logger import setup_logger

app = FastAPI()
logger = setup_logger()

class AgentRequest(BaseModel):
    token_address: str
    chain_id: int
    scan_depth: int = 7

@app.post("/run-agent")
async def analyze_token(request: AgentRequest, req: Request):
    output, log_data = await run_agent(request.dict())
    return output
