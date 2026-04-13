import os
from dotenv import load_dotenv

load_dotenv()

#API Keys
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")
GROQ_API_KEY=os.getenv("GROQ_API_KEY")
TAVILY_API_KEY=os.getenv("TAVILY_API_KEY")

GEMINI_Model= "gemini-2.0-flash"
GROQ_MODEL = "llama-3.3-70b-versatile" 
MAX_TOKENS = 4096


## cost tracking in case we use paid APIs in the future, for now we just want to track usage to stay within free tiers

TOTAL_REQUESTS = {"gemini": 0, "groq": 0, "tavily": 0}

def track_usage(provider):
    """Track API usage so we stay within free tiers"""
    TOTAL_REQUESTS[provider] = TOTAL_REQUESTS.get(provider, 0) + 1
    return TOTAL_REQUESTS[provider]

def print_usage():
    """Print current usage stats"""
    print("\n--- API Usage ---")
    for provider, count in TOTAL_REQUESTS.items():
        print(f"  {provider}: {count} requests")
    print("-----------------")


