from langchain.tools import tool
import requests
from dotenv import load_dotenv
import os
from tavily import TavilyClient

from bs4 import BeautifulSoup
from readability import Document
import trafilatura
import re

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def _clean_text(soup) -> str:
    """Remove page clutter and return plain text."""
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text)


@tool
def web_search(query: str) -> str:
    """Search the web for recent and reliable information on a topic. Returns titles, URLs, and short snippets of the top results."""
    results = tavily.search(query=query, max_results=3, search_depth="basic")

    out = []
    for r in results["results"]:
        snippet = " ".join(r["content"].split())[:250]  # keep snippets short
        out.append(f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {snippet}\n")

    return "\n----\n".join(out)


@tool
def scrape_url(url: str) -> str:
    """
    Open a web page URL and return its main readable text.
    Use this after web_search when the snippets are not enough.
    Uses multiple extraction strategies for better reliability.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        if "html" not in response.headers.get("Content-Type", ""):
            return f"Skipped {url}: not an HTML page."

        html = response.text

        # Strategy 1: trafilatura (best for articles and blogs)
        extracted = trafilatura.extract(
            html, include_comments=False, include_tables=False
        )
        if extracted and len(extracted.strip()) > 200:
            return re.sub(r"\s+", " ", extracted)[:4000]

        # Strategy 2: readability picks the main block
        clean_html = Document(html).summary()
        text = _clean_text(BeautifulSoup(clean_html, "html.parser"))
        if len(text) > 200:
            return text[:4000]

        # Strategy 3: fallback to the full page
        text = _clean_text(BeautifulSoup(html, "html.parser"))
        if text:
            return text[:4000]

        return "Could not extract meaningful content from the page."

    except requests.exceptions.Timeout:
        return "Request timed out while scraping the URL."

    except requests.exceptions.HTTPError as e:
        return f"HTTP error occurred: {e}"

    except requests.exceptions.RequestException as e:
        return f"Could not reach the URL: {e}"

    except Exception as e:
        return f"Could not scrape URL: {e}"