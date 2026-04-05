from pydantic import BaseModel, Field
import random

class Action(BaseModel):
    action_taken: str = Field(description="APPROVE, ESCALATE, or BLOCK")
    confidence: float = Field(description="Agent's confidence score (0.0 to 1.0)")
    insight: str = Field(description="Brief reasoning for the action")

class Observation(BaseModel):
    domain: str = Field(description="EMAIL, TRANSACTION, or ACCOUNT")
    payload: str = Field(description="The actual data to be analyzed")
    attacker_tactic: str = Field(description="Scenario Context")
    turn_number: int = Field(description="Current step in the simulation")

class State(BaseModel):
    current_turn: int = 1
    total_reward: float = 0.0
    is_done: bool = False

class RedTeamGenerator:
    @staticmethod
    def generate_scenario(category):
        if category == "NORMAL":
            scenarios = [
                {"domain": "TRANSACTION", "payload": "Routine $45.20 payment to 'Uber Eats' from the user's primary registered device.", "is_malicious": False, "tactic": "Normal Traffic"},
                {"domain": "ACCOUNT", "payload": "Successful login from the user's home IP address in Chicago. No failed attempts prior.", "is_malicious": False, "tactic": "Normal Traffic"},
                {"domain": "EMAIL", "payload": "Weekly newsletter from Spotify regarding new releases this Friday.", "is_malicious": False, "tactic": "Normal Traffic"}
            ]
        elif category == "ATTACK_BASIC":
            scenarios = [
                {"domain": "EMAIL", "payload": "URGENT: Your account will be suspended in 24 hours. Click here: http://secure-update-account.info/login", "is_malicious": True, "tactic": "Mass Phishing"},
                {"domain": "ACCOUNT", "payload": "15 failed login attempts in 2 minutes from an IP address in North Korea.", "is_malicious": True, "tactic": "Brute Force"}
            ]
        elif category == "ATTACK_ADVANCED":
            scenarios = [
                {"domain": "TRANSACTION", "payload": "API request to transfer $10,000 to an offshore account. The authentication token lacks the standard MFA signature.", "is_malicious": True, "tactic": "Session Hijacking"},
                {"domain": "MESSAGE", "payload": "Hey, it's IT support. We are pushing a silent patch. Please run the attached 'update_v2.exe' with admin rights.", "is_malicious": True, "tactic": "Malware Distribution"}
            ]
        elif category == "AMBIGUOUS_GENUINE": 
            scenarios = [
                {"domain": "ACCOUNT", "payload": "Login from a known Tor Exit Node. However, the user profile indicates they are a privacy researcher who exclusively uses Tor. 2FA was successfully completed.", "is_malicious": False, "tactic": "Privacy Obfuscation (Genuine)"},
                {"domain": "TRANSACTION", "payload": "User bought $5,000 in Bitcoin. Flagged as high risk, but user has a 5-year history of buying $5,000 in crypto on the 1st of every month.", "is_malicious": False, "tactic": "Anomalous but Historical"}
            ]
        else: # STEALTH_MALICIOUS
            scenarios = [
                {"domain": "EMAIL", "payload": "Hi team, please find attached the Q3 financial report for your review. - Sent from John's iPhone.", "is_malicious": True, "tactic": "Compromised Internal Account"},
                {"domain": "TRANSACTION", "payload": "Payment of $1.00 to 'Test Merchant'. IP address matches user's city, but device fingerprint is a headless Linux server.", "is_malicious": True, "tactic": "Card Testing Bot"}
            ]
        return random.choice(scenarios)

class FraudTriageEnv:
    def __init__(self):
        self.state = State()
        self.deck = []
        self.current_task = None

    def reset(self) -> Observation:
        self.state = State(current_turn=1, total_reward=0.0, is_done=False)
        
        self.deck = [
            "NORMAL", 
            "ATTACK_BASIC", 
            "ATTACK_ADVANCED", 
            "AMBIGUOUS_GENUINE", 
            "STEALTH_MALICIOUS"
        ]
        random.shuffle(self.deck)
        
        self.current_task = RedTeamGenerator.generate_scenario(self.deck.pop())
        
        return Observation(
            domain=self.current_task["domain"], 
            payload=self.current_task["payload"], 
            attacker_tactic=self.current_task["tactic"], 
            turn_number=self.state.current_turn
        )

    def step(self, action: Action) -> tuple[Observation, float, bool, dict]:
        if self.state.is_done:
            raise Exception("Environment is finished. Call reset().")

        reward = 0.0
        is_malicious = self.current_task["is_malicious"]
        outcome_tag = ""

        # THE FIX: strict 0.0 to 1.0 grading scale required by OpenEnv grader
        if is_malicious:
            if action.action_taken == "BLOCK":
                reward = 1.0  
                outcome_tag = "CAUGHT_HACKER"
            elif action.action_taken == "ESCALATE":
                reward = 0.5  
                outcome_tag = "ESCALATED_SAFELY"
            else:
                reward = 0.0 
                outcome_tag = "MISSED_HACKER"
        else:
            if action.action_taken == "APPROVE":
                reward = 1.0  
                outcome_tag = "APPROVED_USER"
            else:
                reward = 0.0 
                outcome_tag = "FALSE_POSITIVE"

        self.state.total_reward += reward
        self.state.current_turn += 1

        if self.state.current_turn > 5:
            self.state.is_done = True
            return None, reward, True, {"final_score": self.state.total_reward, "outcome": outcome_tag}

        self.current_task = RedTeamGenerator.generate_scenario(self.deck.pop())
        
        next_obs = Observation(
            domain=self.current_task["domain"], 
            payload=self.current_task["payload"], 
            attacker_tactic=self.current_task["tactic"], 
            turn_number=self.state.current_turn
        )

        return next_obs, reward, self.state.is_done, {"insight": action.insight, "outcome": outcome_tag}