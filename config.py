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


def get_secret(key: str) -> str:
    """
    Get a secret from either:
    1. Streamlit Cloud secrets (st.secrets)
    2. Environment variables (.env file)
    
    WHY both? 
    - Locally: .env file
    - On Streamlit Cloud: secrets are set in the dashboard
    """
    
    # Try Streamlit secrets first (cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    
    # Fall back to environment variables (local)
    return os.getenv(key, "")