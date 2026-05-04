import sys
import os
import re

from google import genai
import config

try:
    from rich.console import Console
    console = Console()
except ImportError:
    class FallbackConsole:
        """Fallback when rich isn't installed (e.g., Streamlit Cloud)."""
        def print(self, msg="", *args, **kwargs):
            # Strip rich markup like [yellow]...[/yellow]
            clean = re.sub(r"$$/?[a-zA-Z0-9 _#]+$$", "", str(msg))
            print(clean)
    console = FallbackConsole()


def call_llm(prompt: str, system_prompt: str = "", provider: str = "gemini") -> str:
    """
    Call an LLM provider.

    Args:
        prompt: The user message.
        system_prompt: System instructions.
        provider: Currently only "gemini" is supported.

    Returns:
        The LLM's response text.

    Raises:
        ValueError: If an unsupported provider is passed.
        RuntimeError: If the LLM call fails.
    """
    if provider == "gemini":
        try:
            return _call_gemini(prompt, system_prompt)
        except Exception as e:
            console.print(f"[red]✗ Gemini call failed: {e}[/red]")
            raise RuntimeError(f"Gemini call failed: {e}") from e

    raise ValueError(f"Unknown provider: {provider!r}. Supported: 'gemini'.")


def _call_gemini(prompt: str, system_prompt: str = "") -> str:
    """Call the Google Gemini API."""
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"

    response = client.models.generate_content(
        model=config.GEMINI_Model,
        contents=full_prompt,
    )

    config.track_usage("gemini")
    return response.text