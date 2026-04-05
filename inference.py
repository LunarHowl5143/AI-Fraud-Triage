import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from models import FraudTriageEnv, Action

load_dotenv()
hf_token = os.environ.get("HF_TOKEN")

if not hf_token:
    raise ValueError("Missing HF_TOKEN! Add it to your .env file.")

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=hf_token
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

    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-72B-Instruct", 
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )
    
    raw_response = response.choices[0].message.content
    return clean_and_parse_json(raw_response)

if __name__ == "__main__":
    print("\n[SYS] INITIATING RED TEAM VS BLUE TEAM SIMULATION...\n")
    
    env = FraudTriageEnv()
    obs = env.reset()
    done = False
    
    while not done:
        print(f"--- TURN {obs.turn_number} ---")
        print(f"[SCENARIO]: {obs.payload} ({obs.attacker_tactic})")
        
        action = agent_policy(obs)
        print(f"[BLUE TEAM ACTION]: {action.action_taken} (Confidence: {action.confidence})")
        print(f"[INSIGHT]: {action.insight}")
        
        obs, reward, done, info = env.step(action)
        print(f"[REWARD ISSUED]: {reward}\n")
        
    print("=== SIMULATION COMPLETE ===")
    print(f"Final Asymmetric Reward Score: {env.state.total_reward}")