"""
ARIA v3 — Deep Research Agent
1. Searches DuckDuckGo for top 10 results
2. Scrapes top 5 pages
3. Uses Groq to analyze, compare, and summarize
4. Returns structured report
"""

from tools.web_scraper import search_and_scrape
from tools.groq_client import simple_chat
import json


def run_research(query: str, mode: str = "research") -> dict:
    """
    Full agentic research pipeline.
    mode: 'research' | 'compare' | 'factcheck' | 'shopping'
    """
    print(f"\n🧠 ARIA Research Agent Starting")
    print(f"   Query: {query}")
    print(f"   Mode:  {mode}")

    # ── STEP 1: Web Search + Scrape ───────────────────────────────────────────
    print("\n[1/3] Searching & scraping web...")
    web_data = search_and_scrape(query, num_results=10, scrape_top=5)

    all_results   = web_data["all_results"]     # 10 results (title+url+snippet)
    scraped_pages = web_data["scraped_pages"]   # 5 pages with full content

    # ── STEP 2: Build context for AI ─────────────────────────────────────────
    print("[2/3] Building AI context...")

    # Summaries from snippets (all 10)
    snippets_text = "\n".join([
        f"{i+1}. [{r['title']}]({r['url']})\n   {r['snippet']}"
        for i, r in enumerate(all_results[:10])
    ])

    # Full page content (top 5)
    pages_text = "\n\n---\n\n".join([
        f"SOURCE {i+1}: {p['title']}\nURL: {p['url']}\n\n{p['content']}"
        for i, p in enumerate(scraped_pages)
        if p.get("success") and p.get("content")
    ])

    # ── STEP 3: AI Analysis ───────────────────────────────────────────────────
    print("[3/3] AI analyzing & synthesizing...")

    mode_prompts = {
        "research": f"""You are ARIA, an expert research analyst. Analyze these web sources and write a comprehensive research report.

QUERY: {query}

TOP 10 SEARCH RESULTS:
{snippets_text}

FULL CONTENT FROM TOP 5 PAGES:
{pages_text[:6000]}

Write a detailed research report with these sections:
## Summary
(2-3 sentence overview)

## Key Findings
(5-7 bullet points of the most important facts)

## Detailed Analysis
(3-4 paragraphs of in-depth analysis)

## Sources Comparison
(How do the different sources agree or differ?)

## Conclusion
(Final verdict / recommendation)

Be factual, cite sources by number, and be thorough.""",

        "compare": f"""You are ARIA, a product/topic comparison analyst.

QUERY: {query}

SEARCH RESULTS:
{snippets_text}

DETAILED CONTENT:
{pages_text[:6000]}

Write a comparison report:
## Overview
## Side-by-Side Comparison
(use a table format if possible)
## Pros & Cons of Each
## Recommendation
## Sources""",

        "shopping": f"""You are ARIA, a shopping research assistant.

QUERY: {query}

SEARCH RESULTS (products/prices):
{snippets_text}

PRODUCT PAGES:
{pages_text[:6000]}

Write a shopping report:
## Best Options Found
## Price Comparison
## Feature Comparison
## Best Value Pick
## Where to Buy
(include URLs)""",

        "factcheck": f"""You are ARIA, a fact-checking agent.

CLAIM TO VERIFY: {query}

EVIDENCE FROM WEB:
{snippets_text}

FULL SOURCE CONTENT:
{pages_text[:6000]}

Write a fact-check report:
## Verdict (TRUE / FALSE / PARTIALLY TRUE / UNVERIFIED)
## Evidence For
## Evidence Against
## Source Analysis
## Conclusion"""
    }

    prompt = mode_prompts.get(mode, mode_prompts["research"])

    report = simple_chat(
        system="You are ARIA, an expert AI research agent. Write detailed, structured, factual reports.",
        user=prompt,
        temperature=0.3
    )

    # ── STEP 4: Return structured result ─────────────────────────────────────
    return {
        "query":         query,
        "mode":          mode,
        "report":        report,
        "sources":       all_results,        # all 10 results
        "scraped_count": len([p for p in scraped_pages if p.get("success")]),
        "total_results": len(all_results),
    }


def run_shopping_research(product: str, site: str = None) -> dict:
    """
    Specialized shopping research.
    """
    if site:
        query = f"{product} site:{site} price buy"
    else:
        query = f"{product} price buy online India"

    return run_research(query, mode="shopping")
