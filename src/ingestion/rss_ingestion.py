"""
RSS ingestion module for Tech Radar.

- Fetch articles from multiple RSS feeds using feedparser
- Return flat list of articles with deduplication
- Includes error handling and timeout management
"""

from typing import List, Dict
from datetime import datetime
import feedparser
from utils.logger import get_logger

logger = get_logger("ingestion.rss")


def fetch_rss_articles(
    urls: List[str], 
    max_items: int = 50,
) -> List[Dict]:
    """
    Fetch articles from multiple RSS feeds.
    
    Args:
        urls: List of RSS feed URLs
        max_items: Maximum articles to return
        timeout: Request timeout in seconds
    
    Returns:
        Flat list of deduplicated articles with fields:
        - title, link, summary, published_at, source
    """
    seen_links = set()
    articles = []
    
    for feed_url in urls:
        try:
            logger.info(f"Fetching RSS from {feed_url}")
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                logger.warning(f"Feed warning for {feed_url}: {feed.bozo_exception}")
            
            source_name = feed.feed.get("title", feed_url)
            
            for entry in feed.entries:
                # Skip if we've already seen this link
                link = entry.get("link", "")
                if link in seen_links or not link:
                    continue
                
                seen_links.add(link)
                
                # Parse published date
                published_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6]).isoformat()
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published_at = datetime(*entry.updated_parsed[:6]).isoformat()
                else:
                    published_at = datetime.utcnow().isoformat()
                
                article = {
                    "title": entry.get("title", "Untitled"),
                    "link": link,
                    "summary": entry.get("summary", ""),
                    "published_at": published_at,
                    "source": source_name,
                    "keywords": [],  # Can be enriched later by enrichment agent
                }
                
                articles.append(article)
                
                if len(articles) >= max_items:
                    logger.info(f"Reached max_items limit: {max_items}")
                    return articles
        
        except Exception as exc:
            logger.error(f"Error fetching {feed_url}: {exc}")
            continue
    
    logger.info(f"Fetched {len(articles)} unique articles from {len(urls)} feeds")
    return articles

