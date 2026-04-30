"""
Outreach Drafting Agent.

The final stage of the intelligence pipeline.
Takes all previous analysis and produces ready-to-edit
outreach communications.

Pipeline position:
  Research → Alignment → Connections → THIS (Drafting)

Output: Email drafts that the co-CEO reviews and edits.
The agent NEVER sends anything directly.
"""

import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from tools.path import get_output_dir, get_safe_name


from tools.llm import call_llm
from tools.org_knowledge import get_full_context
from prompts.outreach import (
    OUTREACH_SYSTEM_PROMPT,
    INITIAL_EMAIL_PROMPT,
    CONNECTOR_EMAIL_PROMPT,
    FOLLOWUP_EMAIL_PROMPT,
)
import config

console = Console()


def draft_initial_outreach(
    funder_name: str,
    funder_profile: str,
    alignment_brief: str,
    connection_paths: str = "No connection path data available.",
) -> dict:
    """
    Draft initial outreach emails to a funder.
    
    Produces 3 versions with different angles so the
    co-CEO can pick the one that feels right.
    
    WHY 3 VERSIONS?
    - Different funders respond to different approaches
    - The co-CEO knows nuances the AI doesn't
    - Having options lets them mix and match
    - It's faster to edit a draft than write from scratch
    
    Args:
        funder_name: Target funder
        funder_profile: From research agent
        alignment_brief: From alignment agent  
        connection_paths: From connection agent
    
    Returns:
        Dict with drafts and metadata
    """
    
    console.print(Panel.fit(
        f"[bold blue]Drafting Outreach: {funder_name}[/bold blue]",
        border_style="blue"
    ))
    
    start_time = datetime.now()
    
    # Get org context for voice/tone reference
    console.print("[dim]Loading org context...[/dim]")
    org_context = get_full_context()
    
    # Build prompt with all our intelligence
    prompt = INITIAL_EMAIL_PROMPT.format(
        funder_profile=funder_profile[:4000],
        alignment_brief=alignment_brief[:4000],
        connection_paths=connection_paths[:3000],
        org_context=org_context[:3000],
    )
    
    console.print("[dim]Generating outreach drafts...[/dim]")
    
    drafts = call_llm(
        prompt=prompt,
        system_prompt=OUTREACH_SYSTEM_PROMPT,
        provider="groq",
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    result = {
        "success": True,
        "type": "initial_outreach",
        "funder_name": funder_name,
        "drafts": drafts,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 1),
        },
    }
    
    _save_drafts(funder_name, "outreach", result)
    
    console.print(Panel.fit(
        f"[bold green]Outreach drafts complete[/bold green]\n"
        f"Time: {elapsed:.1f}s | 3 versions generated",
        border_style="green"
    ))
    
    return result


def draft_connector_email(
    funder_name: str,
    connector_name: str,
    connection_context: str,
    alignment_summary: str,
) -> dict:
    """
    Draft an email asking a mutual connection for an introduction.
    
    This is often MORE important than the direct outreach email
    because warm intros have 10x the response rate.
    """
    
    console.print(Panel.fit(
        f"[bold blue]Drafting Connector Email[/bold blue]\n"
        f"Ask {connector_name} to introduce us to {funder_name}",
        border_style="blue"
    ))
    
    prompt = CONNECTOR_EMAIL_PROMPT.format(
        connector_name=connector_name,
        target_name=funder_name,
        connection_context=connection_context[:2000],
        alignment_summary=alignment_summary[:2000],
    )
    
    draft = call_llm(
        prompt=prompt,
        system_prompt=OUTREACH_SYSTEM_PROMPT,
        provider="groq",
    )
    
    result = {
        "success": True,
        "type": "connector_email",
        "funder_name": funder_name,
        "connector_name": connector_name,
        "drafts": draft,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
        },
    }
    
    _save_drafts(funder_name, "connector", result)
    
    return result


def draft_followup(
    funder_name: str,
    funder_profile: str,
    original_angle: str,
    days_since: int = 14,
) -> dict:
    """
    Draft a follow-up email when the first outreach got no response.
    
    WHY FOLLOW-UPS MATTER:
    80% of successful outreach requires at least 2-3 touches.
    Program officers are busy. No response usually means
    "I haven't gotten to it" not "I'm not interested."
    """
    
    console.print(Panel.fit(
        f"[bold blue]Drafting Follow-up: {funder_name}[/bold blue]",
        border_style="blue"
    ))
    
    prompt = FOLLOWUP_EMAIL_PROMPT.format(
        days_since=days_since,
        original_angle=original_angle[:1000],
        funder_profile=funder_profile[:3000],
    )
    
    draft = call_llm(
        prompt=prompt,
        system_prompt=OUTREACH_SYSTEM_PROMPT,
        provider="groq",
    )
    
    result = {
        "success": True,
        "type": "followup",
        "funder_name": funder_name,
        "drafts": draft,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "days_since_original": days_since,
        },
    }
    
    _save_drafts(funder_name, "followup", result)
    
    return result


def _save_drafts(funder_name: str, draft_type: str, result: dict):
    """Save drafts to file"""
    
    safe_name = funder_name.lower().replace(" ", "_")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
    
    output_dir = get_output_dir()
    os.makedirs(output_dir, exist_ok=True)
    
    filepath = os.path.join(output_dir, f"{safe_name}_{draft_type}_drafts.md")
    with open(filepath, "w") as f:
        f.write(f"# {draft_type.title()} Drafts: {funder_name}\n")
        f.write(f"Generated: {result['metadata']['timestamp']}\n")
        f.write(f"Type: {result['type']}\n\n")
        f.write("---\n\n")
        f.write(result["drafts"])
        f.write("\n\n---\n")
        f.write("*These are drafts for review. Do not send without editing.*\n")
    
    console.print(f"  [dim]Saved: {filepath}[/dim]")


def full_pipeline(
    funder_name: str,
    website_url: str = None,
) -> dict:
    """
    THE COMPLETE AGENT PIPELINE.
    
    One command does everything:
      1. Research the funder
      2. Map alignment to our org
      3. Find connection paths
      4. Draft outreach emails
    
    This is the function that saves the co-CEO 5-10 hours per week.
    
    Input:  A funder name (and optionally their website)
    Output: Complete intelligence package + ready-to-edit drafts
    """
    
    from agents.reasercher import research_funder
    from agents.mapper import create_alignment_brief
    from agents.connector import find_connection_paths
    
    console.print(Panel.fit(
        "[bold blue]═══════════════════════════════════════[/bold blue]\n"
        "[bold blue]   FUNDER INTELLIGENCE AGENT[/bold blue]\n"
        "[bold blue]   Full Pipeline[/bold blue]\n"
        "[bold blue]═══════════════════════════════════════[/bold blue]\n"
        f"Target: {funder_name}",
        border_style="blue"
    ))
    
    pipeline_start = datetime.now()
    
    # ── STAGE 1: Research ──
    console.print("\n[bold]═══ STAGE 1/4: FUNDER RESEARCH ═══[/bold]\n")
    research_result = research_funder(funder_name, website_url)
    
    # ── STAGE 2: Alignment ──
    console.print("\n[bold]═══ STAGE 2/4: ALIGNMENT MAPPING ═══[/bold]\n")
    alignment_result = create_alignment_brief(
        funder_name=funder_name,
        funder_profile=research_result["profile"],
    )
    
    # ── STAGE 3: Connections ──
    console.print("\n[bold]═══ STAGE 3/4: CONNECTION PATHS ═══[/bold]\n")
    connection_result = find_connection_paths(target_name=funder_name)
    
    # ── STAGE 4: Outreach Drafts ──
    console.print("\n[bold]═══ STAGE 4/4: OUTREACH DRAFTS ═══[/bold]\n")
    outreach_result = draft_initial_outreach(
        funder_name=funder_name,
        funder_profile=research_result["profile"],
        alignment_brief=alignment_result.get("alignment_brief", ""),
        connection_paths=connection_result.get("connection_analysis", ""),
    )
    
    total_time = (datetime.now() - pipeline_start).total_seconds()
    
    console.print(Panel.fit(
        f"[bold green]═══ PIPELINE COMPLETE ═══[/bold green]\n\n"
        f"Funder: {funder_name}\n"
        f"Total Time: {total_time:.1f} seconds\n\n"
        f"Files Generated:\n"
        f"  Funder Profile (.md)\n"
        f"  Alignment Brief (.md)\n"
        f"  Connection Paths (.md)\n"
        f"  Outreach Drafts (.md)\n"
        f"  Raw Data (.txt)\n\n"
        f"All saved to: data/output/",
        border_style="green"
    ))
    
    return {
        "funder_name": funder_name,
        "research": research_result,
        "alignment": alignment_result,
        "connections": connection_result,
        "outreach": outreach_result,
        "total_time": total_time,
    }

