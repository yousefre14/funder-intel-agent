"""
Connection Path Agent.

Orchestrates connection research and produces
an analyzed, ranked set of introduction paths.
"""
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel

from tools.llm import call_llm
from tools.connection_search import research_connections, format_connection_data
from tools.org_knowledge import get_full_context
from prompts.connections import CONNECTION_SYSTEM_PROMPT, CONNECTION_PROMPT
import config

console = Console()

def find_connection_paths(
    target_name: str,
    target_ein: str = None,
    our_org_name: str = "Rural Opportunity Institute",
    our_known_funders: list = None,
    funder_profile: str = None,
) -> dict:
    """
    Complete connection path research and analysis.
    
    Args:
        target_name: Who we want to connect with
        target_ein: Their EIN if known
        our_org_name: Our org name
        our_known_funders: Our current funders list
        funder_profile: Optional — existing profile from research agent
    
    Returns:
        Dict with raw data, analyzed paths, and metadata
    """
    console.print(Panel.fit(
        f"[bold blue]Connection Path Research: {target_name}[/bold blue]",
        border_style="blue"
    ))
    
    start_time = datetime.now()
    
    # Default known funders
    if our_known_funders is None:
        our_known_funders = [
            "Appalachian Regional Commission",
            "Benedum Foundation",
            "Sisters of Charity Foundation",
        ]
    
    # Step 1: Gathering raw connection data 
    console.print("\n[bold]Stage 1: Gathering Connection Data[/bold]")
    
    raw_connections = research_connections(
        target_name=target_name,
        target_ein=target_ein,
        our_org_name=our_org_name,
        our_known_funders=our_known_funders,
    )
    
    connection_text = format_connection_data(raw_connections)
    
    # Step 2: Getting our org's relationship info
    console.print("\n[bold]Stage 2: Loading Our Network Info[/bold]")
    
    org_context = get_full_context()
    
    # Extract just the relationship-relevant parts
    our_relationships = _extract_relationship_info(org_context, our_known_funders)
    
    # Step 3: LLM Analysis
    console.print("\n[bold]Stage 3: AI Analysis of Connection Paths[/bold]")
    
    prompt = CONNECTION_PROMPT.format(
        target_name=target_name,
        our_org_name=our_org_name,
        connection_data=connection_text[:10000],
        our_relationships=our_relationships[:4000],
    )
    
    console.print("  [dim]Analyzing paths and ranking connections...[/dim]")
    
    analysis = call_llm(
        prompt=prompt,
        system_prompt=CONNECTION_SYSTEM_PROMPT,
        provider="gemini",
    )
    
    # Step 4: Package results
    elapsed = (datetime.now() - start_time).total_seconds()
    
    result = {
        "success": True,
        "target_name": target_name,
        "connection_analysis": analysis,
        "raw_data": connection_text,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "our_funders_searched": our_known_funders,
            "data_sources": [
                "ProPublica 990 (board members)",
                "Tavily Web Search (leadership, events, publications)",
                "Organization Knowledge Base (our relationships)",
            ],
        },
    }
    
    # Save
    _save_connections(target_name, result)
    
    console.print(Panel.fit(
        f"[bold green]Connection analysis complete[/bold green]\n"
        f"Time: {elapsed:.1f} seconds",
        border_style="green"
    ))
    
    return result


def _extract_relationship_info(org_context: str, known_funders: list) -> str:
    """
    Extract relationship-relevant information from org knowledge.
    
    WHY not send the full org context?
    The connection agent needs to know about our RELATIONSHIPS,
    not all our program details. Focused context = better analysis.
    """
    
    info = "=== OUR KNOWN RELATIONSHIPS ===\n\n"
    
    info += "Current Funders:\n"
    for funder in known_funders:
        info += f"  • {funder}\n"
    
    info += f"\nFull org context (for additional relationship signals):\n"
    info += org_context[:3000]
    
    return info


def _save_connections(target_name: str, result: dict):
    """Save connection analysis to file"""
    
    safe_name = target_name.lower().replace(" ", "_")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
    
    output_dir = "data/output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save analysis
    filepath = os.path.join(output_dir, f"{safe_name}_connections.md")
    with open(filepath, "w") as f:
        f.write(f"# Connection Paths: {target_name}\n")
        f.write(f"Generated: {result['metadata']['timestamp']}\n")
        f.write(f"Sources: {', '.join(result['metadata']['data_sources'])}\n\n")
        f.write("---\n\n")
        f.write(result["connection_analysis"])
    
    console.print(f"  [dim]Saved: {filepath}[/dim]")
    
    # Save raw data
    raw_path = os.path.join(output_dir, f"{safe_name}_connections_raw.txt")
    with open(raw_path, "w") as f:
        f.write(result["raw_data"])
    
    console.print(f"  [dim]Raw data: {raw_path}[/dim]")


