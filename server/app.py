from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import sys
import uvicorn

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import FraudTriageEnv, Observation
from inference import agent_policy

app = FastAPI()
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

env = FraudTriageEnv()
obs = env.reset()

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    with open(os.path.join(os.path.dirname(__file__), "static", "index.html"), "r") as f:
        return f.read()

@app.post("/api/next-turn")
async def next_turn():
    global obs, env
    if env.state.is_done: return {"status": "complete", "message": "Simulation finished."}

    current_attack = {"domain": obs.domain, "payload": obs.payload, "tactic": obs.attacker_tactic, "turn": obs.turn_number}
    try:
        action = agent_policy(obs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    next_obs, reward, done, info = env.step(action)
    obs = next_obs 
    
    return {
        "status": "success",
        "turn": current_attack["turn"],
        "red_team": current_attack,
        "blue_team": {
            "action_taken": action.action_taken,
            "confidence": action.confidence,
            "insight": action.insight,
            "outcome": info.get("outcome", "")
        },
        "reward": reward,
        "is_done": done
    }

@app.post("/api/reset")
async def reset_simulation():
    global obs, env
    obs = env.reset()
    return {"status": "reset", "message": "Environment purged. Back to Turn 1."}

class CustomPayload(BaseModel):
    domain: str
    content: str

@app.post("/api/custom-inject")
async def custom_inject(payload: CustomPayload):
    """Stateless sandbox that outputs the AI's verdict without penalizing it."""
    sandbox_obs = Observation(
        domain=payload.domain,
        payload=payload.content,
        attacker_tactic="Manual Sandbox Injection",
        turn_number=0 
    )
    
    try:
        action = agent_policy(sandbox_obs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    if action.action_taken in ["BLOCK", "ESCALATE"]:
        ai_verdict = "MALICIOUS THREAT DETECTED"
    else:
        ai_verdict = "GENUINE USER ACTIVITY"
        
    return {
        "status": "success",
        "action_taken": action.action_taken,
        "confidence": action.confidence,
        "insight": action.insight,
        "verdict": ai_verdict
    }

# --- DEPLOYMENT FIX: Required by Hugging Face Spaces to auto-start the server ---
def main():
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()