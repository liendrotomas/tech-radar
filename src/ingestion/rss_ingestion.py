"""
Simple RSS ingestion module.

- Fetch articles from a list of RSS URLs
- Return a list of dicts with: title, link, summary
- Keep it simple and synchronous
"""

from typing import List, Dict


def ingest_rss_feeds(feed_urls: List[str]) -> List[Dict]:
    # Placeholder for actual RSS feed parsing logic
    # In a real implementation, you would use a library like feedparser
    articles = []
    for url in feed_urls:
        articles.append(
            {
                "title": f"Sample article from {url}",
                "link": url,
                "summary": "This is a summary of the article.",
                "published_at": "2024-06-01T12:00:00Z",
                "keywords": ["AI"],
            }
        )
    return articles


# implement fetch_rss_articles(urls: list[str]) -> list[dict] that calls ingest_rss_feeds and returns the articles
def fetch_rss_articles(urls: List[str], max_items: int = 10) -> List[Dict]:
    articles = ingest_rss_feeds(urls)
    return articles[:max_items]
