import sys
import os

from google import genai
from groq import Groq
import config
from rich.console import Console

console = Console()

def call_llm(prompt:str , system_prompt:str="", provider:str="gemini" )-> str:
    """
    Call an LLM with automatic fallback.
    
    Args:
        prompt: The user message
        system_prompt: System instructions (how the LLM should behave)
        provider: "gemini" or "groq" — defaults to gemini
    
    Returns:
        The LLM's response text
    """

    ## primary provider

    if provider == "groq":
            try:
                return _call_groq(prompt, system_prompt)
            except Exception as e:
                console.print(f"[yellow]⚠ Groq failed: {e}[/yellow]")
                console.print("[yellow]  Trying Gemini fallback...[/yellow]")
                return _call_gemini(prompt, system_prompt)
        
    elif provider == "gemini":
            try:
                return _call_gemini(prompt, system_prompt)
            except Exception as e:
                console.print(f"[yellow]⚠ Gemini failed: {e}[/yellow]")
                console.print("[yellow]  Trying Groq fallback...[/yellow]")
                return _call_groq(prompt, system_prompt)
        
    else:
            raise ValueError(f"Unknown provider: {provider}")


def _call_gemini(prompt:str, system_prompt:str="")-> str:
    "call google gemini api"
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    # Build the full prompt
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n---\n\n{full_prompt}"
    
    response = client.models.generate_content(
        model=config.GEMINI_Model,
        contents=full_prompt,
    )
    
    config.track_usage("gemini")
    return response.text

def _call_groq(prompt: str, system_prompt: str = "") -> str:
    """Call Groq API (Llama 3.3 70B)"""
    client = Groq(api_key=config.GROQ_API_KEY)
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=messages,
        max_tokens=config.MAX_TOKENS,
        temperature=0.3,  # more factual
    )
    
    config.track_usage("groq")
    return response.choices[0].message.content