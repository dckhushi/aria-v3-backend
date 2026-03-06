# tools/web_research.py
# Deep web research: DuckDuckGo search + scrape top 10 pages + summarize

import requests
from bs4 import BeautifulSoup
import time
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def search_duckduckgo(query: str, max_results: int = 10) -> list[dict]:
    """Search DuckDuckGo and return top N results with title, url, snippet."""
    try:
        # DuckDuckGo HTML search (no API key needed)
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")

        results = []
        for result in soup.select(".result__body")[:max_results]:
            title_el   = result.select_one(".result__title")
            url_el     = result.select_one(".result__url")
            snippet_el = result.select_one(".result__snippet")

            title   = title_el.get_text(strip=True)   if title_el   else ""
            raw_url = url_el.get_text(strip=True)      if url_el     else ""
            snippet = snippet_el.get_text(strip=True)  if snippet_el else ""

            # Clean URL
            if raw_url and not raw_url.startswith("http"):
                raw_url = "https://" + raw_url

            if title and raw_url:
                results.append({"title": title, "url": raw_url, "snippet": snippet})

        return results[:max_results]

    except Exception as e:
        print(f"[WebSearch] Error: {e}")
        return []


def scrape_page(url: str, max_chars: int = 2000) -> str:
    """Scrape readable text content from a URL."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return ""

        soup = BeautifulSoup(resp.text, "lxml")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "form", "iframe", "noscript"]):
            tag.decompose()

        # Try to get main content
        main = (soup.find("article") or soup.find("main") or
                soup.find(id=re.compile(r"content|main|article", re.I)) or
                soup.find("body"))

        if not main:
            return ""

        text = main.get_text(separator=" ", strip=True)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]

    except Exception as e:
        print(f"[Scraper] {url} → {e}")
        return ""


def deep_research(query: str, max_results: int = 10) -> dict:
    """
    Full deep research pipeline:
    1. Search DuckDuckGo for top N results
    2. Scrape each page
    3. Return structured data for the AI to analyze
    """
    print(f"[DeepResearch] Query: {query}")

    # Step 1: Search
    results = search_duckduckgo(query, max_results)
    print(f"[DeepResearch] Found {len(results)} results")

    # Step 2: Scrape each page
    enriched = []
    for i, r in enumerate(results):
        print(f"[DeepResearch] Scraping {i+1}/{len(results)}: {r['url'][:60]}")
        content = scrape_page(r["url"])
        enriched.append({
            "rank":    i + 1,
            "title":   r["title"],
            "url":     r["url"],
            "snippet": r["snippet"],
            "content": content or r["snippet"]  # fallback to snippet
        })
        time.sleep(0.3)  # polite delay

    return {
        "query":   query,
        "count":   len(enriched),
        "results": enriched
    }


def format_for_llm(research_data: dict, max_per_page: int = 400) -> str:
    """Format research data into a compact string for the LLM prompt."""
    lines = [f"DEEP RESEARCH: '{research_data['query']}' — {research_data['count']} sources\n"]
    for r in research_data["results"]:
        lines.append(
            f"[{r['rank']}] {r['title']}\n"
            f"URL: {r['url']}\n"
            f"Content: {r['content'][:max_per_page]}\n"
        )
    return "\n".join(lines)
