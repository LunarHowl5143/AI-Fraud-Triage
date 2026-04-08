import os
import json
import re
import time
from openai import OpenAI
from dotenv import load_dotenv
from models import FraudTriageEnv, Action

load_dotenv()

# --- REQUIRED ENVIRONMENT VARIABLES ---
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN", "dummy-token-for-evaluator")

# --- REQUIRED OPENAI CLIENT SETUP ---
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN
)

def clean_and_parse_json(raw_text):
    try:
        cleaned = raw_text.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        json_str = match.group(0) if match else cleaned
        data = json.loads(json_str)
        return Action(
            action_taken=str(data.get("action_taken", "ESCALATE")).strip().upper(),
            confidence=float(data.get("confidence", 0.0)),
            insight=str(data.get("insight", "Successfully parsed via regex."))
        )
    except Exception as e:
        return Action(action_taken="ESCALATE", confidence=0.0, insight="System Fallback: Invalid JSON structure.")

def agent_policy(observation):
    if observation.turn_number == 0:
        system_context = "You are an AI Security Agent. Analyze this user-submitted payload objectively. Is it safe, does it require escalation, or must it be blocked?"
    else:
        system_context = f"You are evaluating active system logs.\nCurrent Turn: {observation.turn_number}\nScenario Context: {observation.attacker_tactic}"

    prompt = f"""
    {system_context}
    
    Domain: {observation.domain}
    Payload: {observation.payload}
    
    Respond ONLY with a JSON object. No markdown.
    Keys: "action_taken" (APPROVE, ESCALATE, or BLOCK), "confidence" (0.0-1.0), "insight" (brief reason).
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME, 
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.4
            )
            raw_response = response.choices[0].message.content
            return clean_and_parse_json(raw_response)
            
        except Exception as e:
            if attempt < max_retries - 1:
                sleep_time = 5 * (attempt + 1)
                time.sleep(sleep_time)
            else:
                return Action(
                    action_taken="ESCALATE", 
                    confidence=0.0, 
                    insight=f"API Limit Reached. Graceful fallback."
                )

if __name__ == "__main__":
    task_name = "ai-fraud-triage"
    
    # --- THE FIX: STRICT BRACKET FORMAT WITH FLUSH=TRUE ---
    print(f"[START] task={task_name}", flush=True)
    
    env = FraudTriageEnv()
    obs = env.reset()
    done = False
    step_counter = 0
    
    while not done:
        step_counter += 1
        print(f"[SCENARIO]: {obs.payload}")
        
        action = agent_policy(obs)
        print(f"[BLUE TEAM ACTION]: {action.action_taken} (Confidence: {action.confidence})")
        
        obs, reward, done, info = env.step(action)
        
        # --- THE FIX: EXACT STEP FORMAT EXPECTED BY GRADER ---
        print(f"[STEP] step={step_counter} reward={reward}", flush=True)
        
        if not done:
            time.sleep(1.5)
            
    # --- THE FIX: EXACT END FORMAT EXPECTED BY GRADER ---
    print(f"[END] task={task_name} score={env.state.total_reward} steps={step_counter}", flush=True)
    
