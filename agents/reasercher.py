"""
Funder Research Agent
Takes a funder name → gathers data from all sources → produces structured profile

This is the CORE agent. Everything else builds on its output.
"""
import json
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from tools.llm import call_llm
from tools.web_search import search_funder, format_search_results
from tools.irs900 import research_funder_990, format_990_data
from tools.web_scraper import scrape_funder_website, format_website_content
from prompts.reaserch import FUNDER_PROFILE_SYSTEM_PROMPT, FUNDER_PROFILE_PROMPT
import config

console = Console()

def research_funder(funder_name: str, website_url: str = None) -> dict:
    """
    Complete funder research pipeline.
    
    Args:
        funder_name: Name of the foundation/fund/person
        website_url: Optional — their website URL. If not provided,
                     we'll try to find it from search results.
    
    Returns:
        Dict with raw data, synthesized profile, and metadata
    """
    console.print(Panel.fit(
        f"[bold blue]Researching: {funder_name}[/bold blue]",
        border_style="blue"
    ))
    ## to start with the latest possible dates
    start_time = datetime.now()

    # step 1: gathering data from our resources

    #1. web search
    console.print("\n[bold]Step 1/4: Web Search[/bold]")
    search_results = search_funder(funder_name)
    web_search_text = format_search_results(search_results)
    console.print(f"[green]✓ Web search complete[/green]")
    
    #2. irs990
    console.print("\n[bold]Step 2/4: IRS 990 Data[/bold]")
    irs_data = research_funder_990(funder_name)
    irs_text = format_990_data(irs_data)
    console.print(f"[green]✓ 990 data complete[/green]")

    #3. website scraping 
    console.print("\n[bold]Step 3/4: Website Scraping[/bold]")
    
    if not website_url:
    # Try to find website from search results
        website_url = _find_website_url(funder_name, search_results)
    
    website_data = {}
    website_text = "No website data available."
    
    if website_url:
        website_data = scrape_funder_website(website_url, max_pages=10)
        website_text = format_website_content(website_data)
        console.print(f"[green]✓ Website scrape complete[/green]")
    else:
        console.print("[yellow]⚠ No website URL found. Skipping website scrape.[/yellow]")

    #STEP 2 synthesis with llm

    console.print("\n[bold]Step 4/4: AI Analysis & Profile Generation[/bold]")

    # Build the prompt with all our data
    prompt = FUNDER_PROFILE_PROMPT.format(
        funder_name=funder_name,
        web_search_data=web_search_text[:8000],  
        irs_990_data=irs_text[:3000],
        website_data=website_text[:8000],
    )
    
    console.print("  [dim]Sending to LLM for synthesis...[/dim]")
    
    profile = call_llm(
        prompt=prompt,
        system_prompt=FUNDER_PROFILE_SYSTEM_PROMPT,
        provider="gemini",  
    )
    
    console.print(f"[green]✓ Profile generated[/green]")

#step 3 packing the results
    elapsed = (datetime.now() - start_time).total_seconds()
    
    result = {
        "funder_name": funder_name,
        "website_url": website_url,
        "profile": profile,
        "raw_data": {
            "web_search": web_search_text,
            "irs_990": irs_text,
            "website": website_text,
        },
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "sources_used": [
                "Tavily Web Search",
                "ProPublica Nonprofit Explorer",
                f"Website: {website_url}" if website_url else "No website",
            ],
        },
    }
    
    # Save to file
    _save_results(funder_name, result)
    
    console.print(Panel.fit(
        f"[bold green]Research complete for {funder_name}[/bold green]\n"
        f"Time: {elapsed:.1f} seconds\n"
        f"Profile saved to data/output/",
        border_style="green"
    ))
    
    return result


def _find_website_url(funder_name: str, search_results: dict) -> str:
    """Try to identify the funder's main website from search results"""
    
    # Common patterns for foundation websites
    funder_words = funder_name.lower().split()
    
    all_urls = []
    for category, results in search_results.items():
        for r in results:
            all_urls.append(r["url"])
    
    # Look for URLs that contain the funder's name
    for url in all_urls:
        url_lower = url.lower()
        # Check if most words from funder name appear in URL
        matches = sum(1 for word in funder_words if word in url_lower)
        if matches >= len(funder_words) * 0.5:  # At least half the words match
            # Extract base domain
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            console.print(f"  [dim]Found website: {base_url}[/dim]")
            return base_url
    
    return None

def _save_results(funder_name: str, result: dict):
    """Save research results to files"""
    
    # Create safe filename
    safe_name = funder_name.lower().replace(" ", "_")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
    
    output_dir = "data/output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the profile (main output)
    profile_path = os.path.join(output_dir, f"{safe_name}_profile.md")
    with open(profile_path, "w") as f:
        f.write(f"# Funder Profile: {funder_name}\n")
        f.write(f"Generated: {result['metadata']['timestamp']}\n")
        f.write(f"Sources: {', '.join(result['metadata']['sources_used'])}\n")
        f.write(f"\n---\n\n")
        f.write(result["profile"])
    
    console.print(f"  [dim]Profile saved: {profile_path}[/dim]")
    
    # Save raw data (for debugging/reference)
    raw_path = os.path.join(output_dir, f"{safe_name}_raw_data.txt")
    with open(raw_path, "w") as f:
        f.write(f"RAW RESEARCH DATA: {funder_name}\n")
        f.write(f"Generated: {result['metadata']['timestamp']}\n")
        f.write(f"\n{'=' * 60}\n")
        f.write(result["raw_data"]["web_search"])
        f.write(f"\n{'=' * 60}\n")
        f.write(result["raw_data"]["irs_990"])
        f.write(f"\n{'=' * 60}\n")
        f.write(result["raw_data"]["website"])
    
    console.print(f"  [dim]Raw data saved: {raw_path}[/dim]")


if __name__ == "__main__":
    console.print(Panel.fit(
        "[bold blue]Funder Intelligence Agent[/bold blue]\n"
        "Phase 1: Research & Profiling",
        border_style="blue"
    ))
    
    # Get funder name from user
    funder_name = input("\nEnter funder name: ").strip()
    
    if not funder_name:
        funder_name = NameError
        console.print(f"[dim]Using default: {funder_name}[/dim]")
    
    # Optional: provide website URL
    website_url = input("Enter website URL (or press Enter to auto-detect): ").strip()
    if not website_url:
        website_url = None
    
    # Run the research
    result = research_funder(funder_name, website_url)
    
    # Display the profile
    console.print("\n")
    console.print(Panel(
        result["profile"],
        title=f"[bold]Funder Profile: {funder_name}[/bold]",
        border_style="green",
        expand=False,
    ))
    
    # Usage stats
    config.print_usage()

    



