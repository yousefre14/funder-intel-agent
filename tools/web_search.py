
from tavily import TavilyClient
import config

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()
except ImportError:
    class FallbackConsole:
        """Fallback when rich is not installed (e.g., Streamlit Cloud)"""
        def print(self, msg="", *args, **kwargs):
            import re as _re
            clean = _re.sub(r"\$$.*?\$$", "", str(msg))
            print(clean)
    class FallbackPanel:
        @staticmethod
        def fit(msg, **kwargs):
            return msg
    console = FallbackConsole()
    Panel = FallbackPanel
    Table = None


console= Console() 

def search_funder(funder_name:str,max_results:int=5)-> dict:

        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        
        queries = {
            "overview": f"{funder_name} foundation mission priorities about",
            "recent_grants": f"{funder_name} recent grants awarded 2024 2025",
            "leadership": f"{funder_name} foundation leadership staff program officer",
            "news": f"{funder_name} foundation news announcement",
            "strategy": f"{funder_name} foundation strategy theory of change focus areas",
        }
        
        all_results = {}
        for category, query in queries.items():
            console.print(f"  [dim]Searching: {query[:50]}...[/dim]")
            try:
                response = client.search(
                    query=query,
                    max_results=max_results,
                    search_depth="basic", 
                )
                
                results = []
                for r in response.get("results", []):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", ""),
                        "score": r.get("score", 0),
                    })
                
                all_results[category] = results
                config.track_usage("tavily")
                
            except Exception as e:
                console.print(f"  [red]Search failed for {category}: {e}[/red]")
                all_results[category] = []
        
        return all_results

def format_search_results(results:dict)-> str:
     #converting search results into readble format to feed it to the llm

    formatted = ""
    
    for category, items in results.items():
        formatted += f"\n\n=== {category.upper().replace('_', ' ')} ===\n"
        
        if not items:
            formatted += "No results found.\n"
            continue
        
        for item in items:
            formatted += f"\nSource: {item['title']}\n"
            formatted += f"URL: {item['url']}\n"
            formatted += f"Content: {item['content'][:500]}\n"
            formatted += "-" * 40 + "\n"
    
    return formatted
