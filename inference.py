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

    # --- THE FIX: EXPONENTIAL BACKOFF & RETRY LOGIC ---
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
            # If we hit a rate limit, wait and try again
            if attempt < max_retries - 1:
                sleep_time = 5 * (attempt + 1)  # Waits 5s, then 10s
                time.sleep(sleep_time)
            else:
                # If we are totally out of credits, fail gracefully so the grader doesn't crash
                return Action(
                    action_taken="ESCALATE", 
                    confidence=0.0, 
                    insight=f"API Limit Reached. Graceful fallback."
                )

if __name__ == "__main__":
    # --- STRICT GRADER LOGGING (START / STEP / END) ---
    print("START")
    
    env = FraudTriageEnv()
    obs = env.reset()
    done = False
    
    while not done:
        print("STEP")
        print(f"[SCENARIO]: {obs.payload}")
        
        action = agent_policy(obs)
        print(f"[BLUE TEAM ACTION]: {action.action_taken} (Confidence: {action.confidence})")
        
        obs, reward, done, info = env.step(action)
        print(f"[REWARD ISSUED]: {reward}")
        
        # THE FIX: Pacing the requests to prevent hitting the limit in the first place
        if not done:
            time.sleep(1.5)
        
    print("END")
    print(f"Final Asymmetric Reward Score: {env.state.total_reward}")
    
