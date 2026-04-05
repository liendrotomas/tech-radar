"""
RSS ingestion module for Tech Radar.

- Fetch articles from multiple RSS feeds using feedparser
- Return flat list of articles with deduplication
- Includes error handling and timeout management
"""

from typing import List, Dict
from datetime import datetime
import feedparser
import json, re, os
import requests
from utils.logger import get_logger
from utils.formatting import html_clean_summary
from src.templates.outputs import feed_template

logger = get_logger("ingestion.rss")

# Create mapping of common feed sources to a html cleanup function
CLEANUP_FUNCTIONS = {
    "Hacker News": html_clean_summary,
    # Add more sources and their specific cleanup functions as needed
}


def is_valid_url(url: str) -> bool:
    try:
        r = requests.head(url, allow_redirects=True, timeout=5)
        return r.status_code < 400  # Consider 4xx and 5xx responses as invalid
    except Exception:
        return False


def fetch_rss_articles(
    urls: List[str], max_items: int = 50, update_db: bool = False, is_mock: bool = False
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
    articles = []
    if is_mock:
        max_id = 0
        existing_urls = set()
    else:
        # Read the feeds database and get the existing urls to avoid duplicates
        articles_database_file = os.path.join("outputs", "feeds.json")
        os.makedirs(os.path.dirname(articles_database_file), exist_ok=True)

        if not os.path.exists(articles_database_file):
            with open(articles_database_file, "w") as f:
                json.dump([], f)
        try:
            with open(articles_database_file, "r+") as f:
                database = json.load(f)
        except FileNotFoundError:
            database = []

        existing_urls = set(entry["link"] for entry in database)
        # Get max id from existing database to assign new ids to new feeds
        max_id = max([entry["id"] for entry in database], default=0)

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
                if link in existing_urls or not link or not is_valid_url(link):
                    continue
                max_id += 1
                # Parse published date
                published_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6]).isoformat()
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published_at = datetime(*entry.updated_parsed[:6]).isoformat()
                else:
                    published_at = datetime.utcnow().isoformat()

                # Create a new article dict based on the feed_template
                article = feed_template.copy()
                article["id"] = max_id
                article["title"] = entry.get("title", "Untitled")
                article["link"] = link
                article["summary"] = CLEANUP_FUNCTIONS.get(
                    source_name, html_clean_summary
                )(entry.get("summary", ""))
                article["published_at"] = published_at
                article["source"] = source_name
                # Get keywords.terms or tags or keywords if available, else empty list
                article["keywords"] = []
                if "keywords" in entry and isinstance(entry["keywords"], list):
                    article["keywords"] = [
                        kw.get("term", "") for kw in entry["keywords"]
                    ]
                elif "tags" in entry and isinstance(entry["tags"], list):
                    article["keywords"] = [tag.get("term", "") for tag in entry["tags"]]
                elif "keywords" in entry and isinstance(entry["keywords"], str):
                    article["keywords"] = re.split(r"[,\s]+", entry["keywords"])

                if article["keywords"] == []:
                    logger.info(f"Error occurred while fetching keywords for {link}.")

                articles.append(article)

                if len(articles) >= max_items:
                    logger.info(f"Reached max_items limit: {max_items}")
                    if update_db and not is_mock:
                        logger.info("Updating feed database with new articles.")
                        if database is []:
                            database = articles
                        else:
                            database.extend(articles)
                        with open(articles_database_file, "r+") as f:
                            json.dump(database, f, indent=2)
                    return articles

        except Exception as exc:
            logger.error(f"Error fetching {feed_url}: {exc}")
            continue

    seen = set()
    unique_articles = []

    for article in articles:
        if article["link"] not in seen:
            seen.add(article["link"])
            unique_articles.append(article)

    logger.info(
        f"Fetched {len(unique_articles)} unique articles from {len(urls)} feeds with max_items={max_items}"
    )
    return unique_articles
