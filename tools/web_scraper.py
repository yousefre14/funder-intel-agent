import config
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from rich.console import Console
import re
import time

console = Console()

# Pretend to be a normal browser (some sites block scripts)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def scrape_page(url:str,timeout:int=10)-> dict:
    """Scrape a single webpage and extract clean text
    Args:
    url: the url to scrape
    timeout:requests timeout in 10 secounds

    output:
    dict with title , text, headers, links and metadata 
    """
    console.print(f"  [dim]Scraping: {url[:70]}...[/dim]")
    try:
        response= requests.get(url, headers=HEADERS,timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        console.print(f"  [red]Failed to fetch {url}: {e}[/red]")
        return {
            "url": url,
            "success": False,
            "error": str(e),
            "title": "",
            "text": "",
            "links": [],
        }
    # using soup to extract data from html
    soup = BeautifulSoup(response.text, "html.parser")

    #remove unwanted parts : script ,footer,
    for element in soup.find_all([
        "script", "style", "nav", "footer", "header",
        "iframe", "noscript", "svg", "form"
    ]):
        element.decompose()
    
    #let's remove the ad and pop ups
    for element in soup.find_all(attrs={
        "class": re.compile(
            r"cookie|popup|modal|banner|advertisement|sidebar|menu|nav",
            re.IGNORECASE
        )
    }):
        element.decompose()

    #get the titile
    title=""
    if soup.title:
        title=soup.title.string or ""
        title.strip()
    text = _extract_clean_text(soup)
    links = _extract_links(soup, url)

    return {
        "url": url,
        "success": True,
        "error": None,
        "title": title,
        "text": text,
        "links": links,
        "word_count": len(text.split()),
    }
def _extract_clean_text(soup: BeautifulSoup) -> str:
    """
    Extract readable text from HTML.
    Focuses on main content, removes boilerplate.
    """
    
    # Try to find the main content area first
    main_content = (
        soup.find("main") or
        soup.find("article") or
        soup.find(attrs={"role": "main"}) or
        soup.find(attrs={"id": re.compile(r"content|main", re.IGNORECASE)}) or
        soup.find(attrs={"class": re.compile(r"content|main|body", re.IGNORECASE)}) or
        soup.body or
        soup
    )
    # Get the important human readble text , headres(h1,h2), links (a), etc... 
    lines = []
    for element in main_content.find_all([
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "li", "td", "th", "blockquote",
        "div", "span", "a"
    ]):
        text = element.get_text(strip=True)
        #reduce noises and removes empty tags and small entities
        if not text or len(text) < 3:
            continue
        
    # Add heading markers for structure/ a dot for bullet points
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(element.name[1])
            prefix = "#" * level
            lines.append(f"\n{prefix} {text}\n")
        elif element.name == "li":
            lines.append(f"  • {text}")
        else:
            # Avoid duplicating text from nested elements
            if text not in "\n".join(lines[-3:]) if lines else "":
                lines.append(text)
    
    # Join and clean up
    full_text = "\n".join(lines)
    
    # Remove excessive whitespace
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    full_text = re.sub(r" {2,}", " ", full_text)
    
    return full_text.strip()

def _extract_links(soup: BeautifulSoup, base_url: str) -> list:
    """Extract and categorize links from the page"""
    links = []
    seen_urls = set()
    base_domain = urlparse(base_url).netloc

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = a_tag.get_text(strip=True)
        
        # Build absolute URL
        full_url = urljoin(base_url, href)
        
        # Skip anchors, javascript, mailto, etc
        if any(full_url.startswith(prefix) for prefix in [
            "javascript:", "mailto:", "tel:", "#"
        ]):
            continue

        # Skip if we've seen this URL

        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        
        # Determine if internal or external
        link_domain = urlparse(full_url).netloc
        is_internal = link_domain == base_domain
        
        links.append({
            "url": full_url,
            "text": text[:100] if text else "",
            "is_internal": is_internal,
        })
    
    return links
# go to important pages the about and the contract to ssave time 
def find_key_pages(links: list) -> dict:
    """
    From a list of links, identify pages likely to contain
    important funder information.
    """
    
    key_patterns = {
        "about": r"about|who-we-are|our-story|mission",
        "programs": r"program|initiative|what-we-do|our-work|focus-area|grant",
        "grants": r"grant|funding|apply|rfp|request-for-proposal|grantee",
        "team": r"team|staff|people|leadership|board|director",
        "strategy": r"strateg|theory-of-change|approach|impact|annual-report",
        "news": r"news|blog|press|announcement|update|stories",
        "contact": r"contact|connect|reach",
    }
    
    found_pages = {}

    for link in links:
        #incase sensitivity
        url_lower = link["url"].lower()
        text_lower = link["text"].lower()

        for category, pattern in key_patterns.items():
            if re.search(pattern, url_lower) or re.search(pattern, text_lower):
                if category not in found_pages:
                    found_pages[category] = []
                found_pages[category].append(link)
    
    return found_pages

def scrape_funder_website(base_url: str, max_pages: int = 10) -> dict:
    """
    Comprehensive scrape of a funder's website.
    
    Strategy:
    1. Scrape the homepage
    2. Identify key pages (about, programs, grants, team)
    3. Scrape those key pages
    4. Return all content organized by category
    
    Args:
        base_url: The funder's website URL
        max_pages: Maximum number of pages to scrape (be professional)
    
    Returns:
        Dict with organized content from all scraped pages
    """
    
    console.print(f"\n[bold]Scraping funder website: {base_url}[/bold]")
    # Step 1: Scrape homepage
    console.print("[dim]Step 1: Homepage...[/dim]")
    homepage = scrape_page(base_url)
    
    if not homepage["success"]:
        return {
            "base_url": base_url,
            "success": False,
            "error": homepage["error"],
            "pages": {},
        }
    # Step 2: Find key pages
    console.print("[dim]Step 2: Finding key pages...[/dim]")
    internal_links = [l for l in homepage["links"] if l["is_internal"]]
    key_pages = find_key_pages(internal_links)

      # Show what we found

    for category, pages in key_pages.items():
        console.print(f"  [dim]Found {len(pages)} {category} page(s)[/dim]")
    # Step 3: Scrape key pages (up to max_pages)

    console.print(f"[dim]Step 3: Scraping key pages (max {max_pages})...[/dim]")
    
    scraped_pages = {"homepage": homepage}
    pages_scraped = 1

    # Priority order for scraping
    priority_categories = [
        "about", "programs", "grants", "strategy", "team", "news"
    ]
    
    for category in priority_categories:
        if pages_scraped >= max_pages:
            break
        
        if category not in key_pages:
            continue
          # Scrape first page in each category
        page_link = key_pages[category][0]
        
        # Don't re-scrape the homepage
        if page_link["url"] == base_url:
            continue
        
        # Be polite — wait between requests
        time.sleep(1)
        
        page_data = scrape_page(page_link["url"])
        if page_data["success"]:
            scraped_pages[category] = page_data
            pages_scraped += 1

        # Step 4: Compile results
    result = {
        "base_url": base_url,
        "success": True,
        "pages_scraped": pages_scraped,
        "pages": scraped_pages,
        "key_pages_found": {
            cat: [p["url"] for p in pages]
            for cat, pages in key_pages.items()
        },
        "all_internal_links": len(internal_links),
    }
    
    console.print(f"[green]✓ Scraped {pages_scraped} pages from {base_url}[/green]")
    
    return result
def format_website_content(data: dict) -> str:
    """
    Format all scraped website content into a single string
    for LLM consumption.
    """
    
    if not data.get("success"):
        return f"Failed to scrape website: {data.get('error', 'Unknown error')}"
    
    text = f"=== WEBSITE CONTENT: {data['base_url']} ===\n"
    text += f"Pages scraped: {data['pages_scraped']}\n"
    
    for category, page in data["pages"].items():
        text += f"\n\n{'=' * 50}\n"
        text += f"PAGE: {category.upper()}\n"
        text += f"URL: {page['url']}\n"
        text += f"Title: {page['title']}\n"
        text += f"Words: {page.get('word_count', 'N/A')}\n"
        text += f"{'=' * 50}\n\n"
        text += page["text"][:3000]  # Limit per page to manage token costs
        
        if len(page["text"]) > 3000:
            text += f"\n\n[... truncated, {len(page['text'])} chars total ...]"
    
    # List pages we found but didn't scrape
    text += f"\n\n{'=' * 50}\n"
    text += "OTHER KEY PAGES FOUND (not scraped):\n"
    for category, urls in data.get("key_pages_found", {}).items():
        if category not in data["pages"]:
            for url in urls[:2]:
                text += f"  {category}: {url}\n"
    
    return text