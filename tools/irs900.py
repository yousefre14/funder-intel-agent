"""
IRS 990 data from ProPublica Nonprofit Explorer.
Free, no API key needed.
Gets: financials, grants, officers, filing history.
"""

import requests
from rich.console import Console

console = Console()

BASE_URL = "https://projects.propublica.org/nonprofits/api/v2"


def search_nonprofit(name: str, state: str = None) -> list:
    """Search for a nonprofit by name"""
    params = {"q": name}
    if state:
        params["state[id]"] = state
    
    response = requests.get(f"{BASE_URL}/search.json", params=params)
    data = response.json()
    return data.get("organizations", [])


def get_nonprofit_details(ein: str) -> dict:
    """Get detailed info for a nonprofit by EIN"""
    response = requests.get(f"{BASE_URL}/organizations/{ein}.json")
    if response.status_code != 200:
        return {}
    return response.json().get("organization", {})


def get_nonprofit_filings(ein: str) -> list:
    """Get 990 filing history"""
    response = requests.get(f"{BASE_URL}/organizations/{ein}.json")
    if response.status_code != 200:
        return []
    return response.json().get("filings_with_data", [])


def research_funder_990(funder_name: str) -> dict:
    """
    Complete 990 research for a funder.
    Returns structured data about the organization.
    """
    console.print(f"  [dim]Searching ProPublica for {funder_name}...[/dim]")
    
    # Search for the org
    orgs = search_nonprofit(funder_name)
    
    if not orgs:
        console.print(f"  [yellow]No 990 data found for {funder_name}[/yellow]")
        return {"found": False, "name": funder_name}
    
    # Take the best match (first result)
    org = orgs[0]
    ein = str(org.get("ein", ""))
    
    console.print(f"  [dim]Found: {org.get('name')} (EIN: {ein})[/dim]")
    
    details = get_nonprofit_details(ein)
    filings = get_nonprofit_filings(ein)
    
    result = {
        "found": True,
        "name": org.get("name", ""),
        "ein": ein,
        "city": org.get("city", ""),
        "state": org.get("state", ""),
        "ntee_code": org.get("ntee_code", ""),
        "subsection_code": org.get("subsection_code", ""),
        "total_revenue": details.get("total_revenue", 0),
        "total_expenses": details.get("total_expenses", 0),
        "total_assets": details.get("total_assets", 0),
        "tax_period": details.get("tax_period", ""),
        "num_filings": len(filings),
        "recent_filings": [],
    }
    
    # Get recent filings summary
    for filing in filings[:3]:  # Last 3 years
        result["recent_filings"].append({
            "tax_period": filing.get("tax_prd_yr", ""),
            "total_revenue": filing.get("totrevenue", 0),
            "total_expenses": filing.get("totfuncexpns", 0),
            "total_assets": filing.get("totassetsend", 0),
            "pdf_url": filing.get("pdf_url", ""),
        })
    
    return result


def format_990_data(data: dict) -> str:
    """Format 990 data into readable text for LLM"""
    
    if not data.get("found"):
        return f"No IRS 990 data found for {data.get('name', 'unknown')}."
    
    text = f"""
=== IRS 990 DATA ===
Organization: {data['name']}
EIN: {data['ein']}
Location: {data['city']}, {data['state']}
NTEE Code: {data['ntee_code']}

Filing History ({data['num_filings']} filings found):
"""
    
    for filing in data.get("recent_filings", []):
        text += f"""
  Year {filing['tax_period']}:
    Revenue:  ${filing['total_revenue']:,.0f}
    Expenses: ${filing['total_expenses']:,.0f}
    Assets:   ${filing['total_assets']:,.0f}
"""
    
    return text
