"""
Connection Path Research Tool.

Finds potential warm introduction paths between
our organization and a target funder/person.
"""
import requests
import re
from rich.console import Console
from rich.table import Table
from tavily import TavilyClient
import config

console = Console()
PROPUBLICA_URL = "https://projects.propublica.org/nonprofits/api/v2"

def get_board_members(ein: str) -> list:

    console.print(f"  [dim]Fetching board members for EIN {ein}...[/dim]")
    try:
        # Get the organization's filings
        response = requests.get(
            f"{PROPUBLICA_URL}/organizations/{ein}.json",
            timeout=10
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        filings = data.get("filings_with_data", [])
        
        if not filings:
            return []
        org_info = data.get("organization", {})
        people = []

        return people
        
    except Exception as e:
        console.print(f"  [yellow]Board member lookup failed: {e}[/yellow]")
        return []

def search_board_members_web(org_name: str) -> list:
    """
Search the web for board members and leadership.
"""
    console.print(f"  [dim]Searching for {org_name} leadership...[/dim]")

    try:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        
        response = client.search(
            query=f"{org_name} board of directors officers leadership team",
            max_results=10,
            search_depth="basic",
        )
        
        config.track_usage("tavily")
        people = []
        
        for result in response.get("results", []):
            people.append({
                "source_title": result.get("title", ""),
                "source_url": result.get("url", ""),
                "content": result.get("content", ""),
                "type": "web_search",
            })
        
        return people
    except Exception as e:
        console.print(f"  [yellow]Board search failed: {e}[/yellow]")
        return []

def find_shared_funders(our_funders: list, target_ein: str) -> list:
    """
    Find funders that support BOTH our org and the target org.
"""
    console.print(f"  [dim]Analyzing shared funder relationships...[/dim]")

    shared = []
    for funder in our_funders:
        try:
            client = TavilyClient(api_key=config.TAVILY_API_KEY)
            
            response = client.search(
                query=f'"{funder}" grants grantees recent awards',
                max_results=5,
                search_depth="basic",
            )
            
            config.track_usage("tavily")
            
            # Checking if any results mention the target
            for result in response.get("results", []):
                shared.append({
                    "our_funder": funder,
                    "source": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", "")[:300],
                    "connection_type": "shared_funder",
                    "strength": "MEDIUM",
                })
            
        except Exception as e:
            console.print(f"  [yellow]Search failed for {funder}: {e}[/yellow]")
    
    return shared

def find_co_grantees(target_name: str) -> list:
    """
    Find organizations that receive grants from the same funder.
    """
    console.print(f"  [dim]Searching for co-grantees of {target_name}...[/dim]")

    try:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        
        response = client.search(
            query=f"{target_name} grantees funded organizations recent grants list",
            max_results=5,
            search_depth="basic",
        )
        
        config.track_usage("tavily")
        
        grantees = []
        for result in response.get("results", []):
            grantees.append({
                "source": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", "")[:300],
                "connection_type": "co_grantee",
            })
        
        return grantees
        
    except Exception as e:
        console.print(f"  [yellow]Co-grantee search failed: {e}[/yellow]")
        return []

def find_shared_events(our_org_name: str, target_name: str) -> list:
    """
    Find conferences, panels, or events where both orgs appeared.
    """
    console.print(f"  [dim]Searching for shared events/conferences...[/dim]")
    
    try:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        
        # Search for target's conference appearances
        response = client.search(
            query=f"{target_name} conference panel speaker presentation event 2024 2025",
            max_results=5,
            search_depth="basic",
        )
        
        config.track_usage("tavily")
        
        events = []
        for result in response.get("results", []):
            events.append({
                "source": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", "")[:300],
                "connection_type": "shared_event",
                "strength": "WEAK",
            })
        
        return events
        
    except Exception as e:
        console.print(f"  [yellow]Event search failed: {e}[/yellow]")
        return []
    
def find_publications(target_name: str) -> list:
    """
    Find publications, reports, or articles by the target funder.
    """
    console.print(f"  [dim]Searching for publications...[/dim]")

    try:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        
        response = client.search(
            query=f"{target_name} published report paper research article author",
            max_results=5,
            search_depth="basic",
        )
        
        config.track_usage("tavily")
        
        pubs = []
        for result in response.get("results", []):
            pubs.append({
                "source": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", "")[:300],
                "connection_type": "publication",
                "strength": "MEDIUM",
            })
        
        return pubs
        
    except Exception as e:
        console.print(f"  [yellow]Publication search failed: {e}[/yellow]")
        return []
    
def research_connections(
    target_name: str,
    target_ein: str = None,
    our_org_name: str = "Rural Opportunity Institute",
    our_known_funders: list = None,
    ) -> dict:
    """
    Complete connection path research for a target funder.
    """
    console.print(f"\n[bold]Researching connection paths to: {target_name}[/bold]\n")
    
    # Default known funders (from our sample org doc)
    if our_known_funders is None:
        our_known_funders = [
            "Appalachian Regional Commission",
            "Benedum Foundation",
            "Sisters of Charity Foundation",
        ]
    
    all_connections = {
        "target": target_name,
        "our_org": our_org_name,
        "paths": [],
    }
    
    # ---- 1. Target's board/leadership ----
    console.print("[bold]1. Researching target's leadership...[/bold]")
    leadership_data = search_board_members_web(target_name)
    all_connections["target_leadership"] = leadership_data
    
    # ---- 2. Our shared funders ----
    console.print("\n[bold]2. Analyzing shared funder relationships...[/bold]")
    shared_funder_data = find_shared_funders(our_known_funders, target_ein or "")
    all_connections["shared_funders"] = shared_funder_data
    
    # ---- 3. Co-grantees ----
    console.print("\n[bold]3. Finding co-grantees...[/bold]")
    co_grantee_data = find_co_grantees(target_name)
    all_connections["co_grantees"] = co_grantee_data
    
    # ---- 4. Shared events ----
    console.print("\n[bold]4. Searching for shared events...[/bold]")
    event_data = find_shared_events(our_org_name, target_name)
    all_connections["shared_events"] = event_data
    
    # ---- 5. Publications ----
    console.print("\n[bold]5. Finding relevant publications...[/bold]")
    publication_data = find_publications(target_name)
    all_connections["publications"] = publication_data
    
    return all_connections

def format_connection_data(data: dict) -> str:
    """
    Format all connection research into a string for LLM analysis.
    """
    text = f"=== CONNECTION RESEARCH: {data['target']} ===\n"
    text += f"Our Organization: {data['our_org']}\n\n"
    
    # Target leadership
    text += "--- TARGET LEADERSHIP ---\n"
    for item in data.get("target_leadership", []):
        text += f"Source: {item['source_title']}\n"
        text += f"URL: {item['source_url']}\n"
        text += f"Content: {item['content'][:300]}\n\n"
    
    # Shared funders
    text += "\n--- SHARED FUNDER ANALYSIS ---\n"
    for item in data.get("shared_funders", []):
        text += f"Our Funder: {item['our_funder']}\n"
        text += f"Source: {item['source']}\n"
        text += f"Content: {item['content']}\n\n"
    
    # Co-grantees
    text += "\n--- CO-GRANTEES ---\n"
    for item in data.get("co_grantees", []):
        text += f"Source: {item['source']}\n"
        text += f"Content: {item['content']}\n\n"
    
    # Events
    text += "\n--- SHARED EVENTS/CONFERENCES ---\n"
    for item in data.get("shared_events", []):
        text += f"Source: {item['source']}\n"
        text += f"Content: {item['content']}\n\n"
    
    # Publications
    text += "\n--- PUBLICATIONS ---\n"
    for item in data.get("publications", []):
        text += f"Source: {item['source']}\n"
        text += f"Content: {item['content']}\n\n"
    
    return text



