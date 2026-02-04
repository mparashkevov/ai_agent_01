import requests
from typing import List, Dict

def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Search the web for the given query using DuckDuckGo."""
    results = []
    try:
        from duckduckgo_search import DDGS
        # Attempt search with default params
        with DDGS() as ddgs:
            # Try to get results. Some versions of DDGS might require different params.
            # Using list() to consume the generator immediately.
            search_results = list(ddgs.text(query, max_results=max_results))
            for r in search_results:
                results.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", "")
                })
    except Exception as e:
        print(f"Error searching web: {e}")
        # Fallback: maybe try a simple requests-based search if DDGS fails?
        # For now, just return empty list as we have wttr.in fallback in weather_tool.
        return []
    return results

def read_url(url: str) -> str:
    """Fetch and extract text content from a URL."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text()
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:5000] # Limit content length
    except Exception as e:
        return f"Error reading URL {url}: {e}"
