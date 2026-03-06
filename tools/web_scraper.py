"""
ARIA v3 — Web Scraper & Search Tool
- DuckDuckGo search (free, no key)
- Top 10 URL fetcher
- Content extractor
"""
import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import quote_plus, urljoin


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def search_duckduckgo(query: str, max_results: int = 10) -> list:
    """
    Search DuckDuckGo and return top results.
    Returns list of {title, url, snippet}
    """
    results = []

    # DuckDuckGo HTML search (no API key needed)
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        for result in soup.select(".result")[:max_results]:
            title_el   = result.select_one(".result__title")
            url_el     = result.select_one(".result__url")
            snippet_el = result.select_one(".result__snippet")

            if not title_el:
                continue

            title   = title_el.get_text(strip=True)
            url_raw = url_el.get_text(strip=True) if url_el else ""
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            # Build full URL
            link_el = result.select_one(".result__title a")
            href = link_el["href"] if link_el and link_el.get("href") else ""
            if href.startswith("//duckduckgo.com/l/?"):
                # Extract actual URL from DDG redirect
                import urllib.parse as up
                parsed = up.parse_qs(up.urlparse(href).query)
                href = parsed.get("uddg", [href])[0]

            if title and href:
                results.append({
                    "title":   title,
                    "url":     href,
                    "snippet": snippet
                })

        if results:
            return results[:max_results]
    except Exception as e:
        print(f"DDG HTML search error: {e}")

    # Fallback: DuckDuckGo Instant Answer API
    try:
        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()

        if data.get("AbstractText"):
            results.append({
                "title":   data.get("Heading", query),
                "url":     data.get("AbstractURL", ""),
                "snippet": data["AbstractText"]
            })

        for topic in data.get("RelatedTopics", [])[:8]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title":   topic.get("Text", "")[:80],
                    "url":     topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", "")
                })
    except Exception as e:
        print(f"DDG API fallback error: {e}")

    return results[:max_results]


def scrape_page(url: str, max_chars: int = 3000) -> dict:
    """
    Scrape a single page and extract clean text content.
    Returns {url, title, content, success}
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove junk tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                          "form", "noscript", "iframe", "ads", "advertisement"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title else url

        # Try to get main content area
        main = (soup.find("article") or soup.find("main") or
                soup.find(id="content") or soup.find(class_="content") or
                soup.find("body"))

        if main:
            text = main.get_text(separator=" ", strip=True)
        else:
            text = soup.get_text(separator=" ", strip=True)

        # Clean up whitespace
        import re
        text = re.sub(r"\s+", " ", text).strip()

        return {
            "url":     url,
            "title":   title,
            "content": text[:max_chars],
            "success": True
        }

    except Exception as e:
        return {
            "url":     url,
            "title":   url,
            "content": f"Could not scrape: {e}",
            "success": False
        }


def search_and_scrape(query: str, num_results: int = 10, scrape_top: int = 5) -> dict:
    """
    Full pipeline:
    1. Search DuckDuckGo for query
    2. Get top num_results URLs
    3. Scrape top scrape_top pages
    Returns structured data ready for AI analysis
    """
    print(f"🔍 Searching: {query}")
    search_results = search_duckduckgo(query, max_results=num_results)

    scraped = []
    for i, result in enumerate(search_results[:scrape_top]):
        if result["url"] and result["url"].startswith("http"):
            print(f"  📄 Scraping [{i+1}/{scrape_top}]: {result['url'][:60]}...")
            page = scrape_page(result["url"])
            scraped.append({**result, **page})
            time.sleep(0.3)  # polite delay
        else:
            scraped.append({**result, "content": result["snippet"], "success": False})

    return {
        "query":          query,
        "total_found":    len(search_results),
        "all_results":    search_results,       # all 10 (title + url + snippet)
        "scraped_pages":  scraped,              # top 5 with full content
    }
