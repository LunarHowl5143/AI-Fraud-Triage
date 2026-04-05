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
        # 1. ROUTINE TRAFFIC (1000+ Permutations)
        if category == "NORMAL":
            domain = random.choice(["TRANSACTION", "ACCOUNT", "EMAIL"])
            if domain == "TRANSACTION":
                merchant = random.choice(["Uber Eats", "Amazon", "Netflix", "Spotify", "Local Grocery", "Steam"])
                device = random.choice(["primary registered iPhone", "home Desktop PC", "registered Android phone"])
                payload = f"Routine ${random.randint(12, 150)}.{random.randint(10, 99)} payment to '{merchant}' from the user's {device}."
            elif domain == "ACCOUNT":
                city = random.choice(["Chicago", "Seattle", "Austin", "New York", "London", "Toronto"])
                payload = f"Successful login from the user's home IP address in {city}. No failed attempts prior."
            else:
                service = random.choice(["Spotify", "LinkedIn", "GitHub", "Medium"])
                topic = random.choice(["new releases this Friday", "your weekly network updates", "dependabot security alerts"])
                payload = f"Automated notification from {service} regarding {topic}."
            return {"domain": domain, "payload": payload, "is_malicious": False, "tactic": "Normal Traffic"}

        # 2. BASIC ATTACKS (1000+ Permutations)
        elif category == "ATTACK_BASIC":
            domain = random.choice(["EMAIL", "ACCOUNT"])
            if domain == "EMAIL":
                fake_url = random.choice(["secure-update-account.info", "paypal-auth-verify.net", "apple-id-recovery.com"])
                time = random.choice(["24", "12", "48"])
                payload = f"URGENT: Your account will be suspended in {time} hours. Click here: http://{fake_url}/login"
            else:
                country = random.choice(["North Korea", "Russia", "Iran", "unknown proxy locations"])
                attempts = random.randint(15, 80)
                payload = f"{attempts} failed login attempts in 2 minutes from an IP address in {country}."
            return {"domain": domain, "payload": payload, "is_malicious": True, "tactic": "Brute Force / Phishing"}

        # 3. ADVANCED ATTACKS (1000+ Permutations)
        elif category == "ATTACK_ADVANCED":
            domain = random.choice(["TRANSACTION", "MESSAGE"])
            if domain == "TRANSACTION":
                offshore = random.choice(["the Cayman Islands", "Cyprus", "Panama", "Belize"])
                auth = random.choice(["MFA signature", "device fingerprint", "session cookie validation"])
                payload = f"API request to transfer ${random.randint(5000, 85000)} to an offshore account in {offshore}. The authentication token lacks the standard {auth}."
            else:
                malware = random.choice(["update_v2.exe", "patch_critical.msi", "IT_audit_tool.bat"])
                dept = random.choice(["IT support", "HR", "SysAdmin"])
                payload = f"Hey, it's {dept}. We are pushing a silent patch. Please run the attached '{malware}' with admin rights."
            return {"domain": domain, "payload": payload, "is_malicious": True, "tactic": "Session Hijacking / Malware"}

        # 4. AMBIGUOUS GENUINE BAIT (Tricks AI into False Positives)
        elif category == "AMBIGUOUS_GENUINE": 
            domain = random.choice(["ACCOUNT", "TRANSACTION"])
            if domain == "ACCOUNT":
                tool = random.choice(["Tor Exit Node", "Commercial VPN", "Proxy Chain"])
                job = random.choice(["privacy researcher", "cybersecurity student", "remote contractor"])
                payload = f"Login from a known {tool}. However, the user profile indicates they are a {job} who exclusively uses this setup. 2FA was successfully completed."
            else:
                crypto = random.choice(["Bitcoin", "Ethereum", "Monero"])
                years = random.randint(2, 6)
                payload = f"User bought ${random.randint(2000, 5000)} in {crypto}. Flagged as high risk, but user has a {years}-year history of identical purchases on the 1st of every month."
            return {"domain": domain, "payload": payload, "is_malicious": False, "tactic": "Anomalous but Historical (Genuine)"}

        # 5. STEALTH MALICIOUS BAIT (Tricks AI into False Negatives)
        else: 
            domain = random.choice(["EMAIL", "TRANSACTION"])
            if domain == "EMAIL":
                doc = random.choice(["Q3 financial report", "updated employee roster", "client contract v2"])
                name = random.choice(["John", "Sarah", "Mike", "Emily"])
                device = random.choice(["iPhone", "iPad", "Android device"])
                payload = f"Hi team, please find attached the {doc} for your review. - Sent from {name}'s {device}."
            else:
                merchant = random.choice(["Test Merchant", "Stripe Verification", "AWS Auth"])
                bot = random.choice(["headless Linux server", "scripted browser instance", "known datacenter IP"])
                payload = f"Payment of $1.00 to '{merchant}'. IP address matches user's city, but device fingerprint is a {bot}."
            return {"domain": domain, "payload": payload, "is_malicious": True, "tactic": "Compromised Internal / Card Testing"}

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

        # OpenEnv Strict 0.0 to 1.0 Grading Scale
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
