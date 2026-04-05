---
title: Fraud Triage Env Environment Server
emoji: 🎯
colorFrom: green
colorTo: yellow
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
---

# Fraud Triage Env Environment

An advanced, interactive Reinforcement Learning (RL) environment built for the OpenEnv Hackathon. This project simulates an active cyber warfare scenario, pitting an AI Security Agent (Blue Team) against a procedurally generated attacker (Red Team) to triage incoming emails, transactions, and account logins.

## Quick Start

The simplest way to interact with the Fraud Triage environment is through the built-in Cyberpunk UI Dashboard, or programmatically via the `FraudTriageEnv` class:

```python
from models import FraudTriageEnv, Action

try:
    # Initialize the Red vs Blue Environment
    env = FraudTriageEnv()

    # Reset to draw a new Shuffled Deck scenario
    obs = env.reset()
    print(f"Turn {obs.turn_number}: Red Team Injects -> {obs.payload}")

    # Agent evaluates the threat
    action = Action(
        action_taken="BLOCK", 
        confidence=0.95, 
        insight="Suspicious Tor exit node detected."
    )
    
    # Step the environment
    next_obs, reward, done, info = env.step(action)
    
    print(f"Outcome: {info['outcome']}")
    print(f"Reward Issued: {reward}")

except Exception as e:
    print(f"Simulation Error: {e}")
Building the Docker Image
Before deploying the environment, you can test the Docker build locally:

BASH 

# From project root
docker build -t fraud_triage_env-env:latest -f Dockerfile .
Deploying to Hugging Face Spaces
You can easily deploy your OpenEnv environment to Hugging Face Spaces using the openenv push command:

Bash
# From the environment directory (where openenv.yaml is located)
openenv push

# Or specify options
openenv push --namespace my-org --private
The openenv push command will:
Validate that the directory is an OpenEnv environment (checks for openenv.yaml)
Prepare a custom build for Hugging Face Docker space(enables web interface)
Upload to Hugging Face (ensuring you're logged in)

PREREQUISITES :
Authenticate with Hugging Face: The command will prompt for login if not already authenticated.

Ensure your HF_TOKEN is added to your Space's repository secrets after deployment for the AI inference to function.

Environment Details :

ACTION
Action: Contains the Blue Team agent's decision logic.
action_taken (str) - Must be "APPROVE", "ESCALATE", or "BLOCK"
confidence (float) - The agent's confidence score (0.0 to 1.0)
insight (str) - The agent's reasoning for the decision

OBSERVATION :
Observation: Contains the Red Team's generated threat payload.
domain (str) - "EMAIL", "TRANSACTION", or "ACCOUNT"
payload (str) - The actual data string to be analyzed
attacker_tactic (str) - Context of the scenario (e.g., "Spear Phishing", "Normal Traffic")
turn_number (int) - Current step in the 5-round simulation

REWARD :
The reward utilizes an asymmetric grading scale compliant with OpenEnv's 0.0 to 1.0 normalization:
Catching a Hacker / Approving a Genuine User → reward: 1.0
Escalating safely for human review → reward: 0.5
FALSE POSITIVE (Blocking a real user) → reward: 0.0
FALSE NEGATIVE (Letting a hacker through) → reward: 0.0

Advanced Usage:

THE SHUFFLED DECK ARCHIETECTURE
Unlike static baselines, this environment utilizes a procedural Shuffled Deck Generator. Every time the environment is reset, it dynamically builds a unique 5-round gauntlet. The deck guarantees a mix of routine traffic, brute-force attacks, and advanced exploits, alongside carefully engineered "Bait" scenarios designed to trick the AI into False Positives or False Negatives.

STATELESS SANDBOX RADAR
The included FastAPI server features a /api/custom-inject endpoint. This allows security analysts to manually inject payloads "off-the-record" to test the AI's reasoning without disrupting the official baseline state machine or turn counter.

DEVELOPMENT AND TESTING 
Running Locally
Run the FastAPI server locally for development to access the Interactive Dashboard:

Bash
uvicorn server.app:app --reload
Navigate to http://localhost:8000 to interact with the environment.

Project Structure

Plaintext
fraud_triage_env/
├── .dockerignore          # Docker build exclusions
├── README.md              # This file
├── openenv.yaml           # OpenEnv manifest
├── pyproject.toml         # Project metadata and dependencies
├── requirements.txt       # Cloud dependencies
├── uv.lock                # Locked dependencies (generated)
├── models.py              # Environment State Machine & Pydantic Models
├── inference.py           # Hugging Face Router & Qwen AI Agent Policy
└── server/
    ├── app.py             # FastAPI application and bridging logic
    └── static/
        └── index.html     # Cyberpunk Telemetry UI Dashboard
