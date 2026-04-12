"""
RSS ingestion module for Tech Radar.

- Fetch articles from multiple RSS feeds using feedparser
- Return flat list of articles with deduplication
- Includes error handling and timeout management
"""

import os
from typing import List
from datetime import datetime
from dotenv import load_dotenv
import feedparser
import re
import requests

from src.database.database import Database, Feed
from src.utils.logger import get_logger
from src.utils.formatting import html_clean_summary

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
    urls: List[str],
    max_items: int = 50,
    db_hndlr: Database = None,
) -> List[Feed]:
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

    existing_articles = db_hndlr.retrieve_items(Feed)
    existing_urls = {
        article.link for article in existing_articles if getattr(article, "link", None)
    }
    max_id = max((article.id or 0 for article in existing_articles), default=0)
    new_articles: List[Feed] = []

    for feed_url in urls:
        try:
            logger.info(f"Fetching RSS from {feed_url}")
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                logger.warning(f"Feed warning for {feed_url}: {feed.bozo_exception}")

            source_name = feed.feed.get("title", feed_url)
            new_entries = 0
            for entry in feed.entries:
                # Skip if we've already seen this link
                link = entry.get("link", "")
                if link in existing_urls or not link or not is_valid_url(link):
                    continue

                new_entries += 1
                logger.info(f"Adding new article. Count: {new_entries} / {max_items}")
                existing_urls.add(link)
                max_id += 1
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6]).isoformat()
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published_at = datetime(*entry.updated_parsed[:6]).isoformat()
                else:
                    published_at = datetime.utcnow().isoformat()

                article = Feed(
                    id=max_id,
                    title=entry.get("title", "Untitled"),
                    link=link,
                    summary=CLEANUP_FUNCTIONS.get(source_name, html_clean_summary)(
                        entry.get("summary", "")
                    ),
                    published_at=published_at,
                    source=source_name,
                    keywords=[],
                )

                if "keywords" in entry and isinstance(entry["keywords"], list):
                    article.keywords = [kw.get("term", "") for kw in entry["keywords"]]
                elif "tags" in entry and isinstance(entry["tags"], list):
                    article.keywords = [tag.get("term", "") for tag in entry["tags"]]
                elif "keywords" in entry and isinstance(entry["keywords"], str):
                    article.keywords = re.split(r"[,\s]+", entry["keywords"])

                if article.keywords == []:
                    logger.info(f"Error occurred while fetching keywords for {link}.")

                db_hndlr.add_item(article)
                new_articles.append(article)

                if new_entries >= max_items:
                    logger.info(f"Reached max_items limit: {max_items}")
                    return new_articles

        except Exception as exc:
            logger.error(f"Error fetching {feed_url}: {exc}")
            continue

    return new_articles

def fetch_scraping_articles(urls: List[str], max_items: int = 50, db_hndlr: Database = None, cfg=None) -> List[Feed]:
    pass
    
    
def fetch_query_articles(urls: List[str], max_items: int = 50, db_hndlr: Database = None, cfg=None) -> List[Feed]:
    # Placeholder function for query-based ingestion
    pass

def fetch_sns_articles(users: List[str], max_items: int = 1, db_hndlr: Database = None, cfg=None) -> List[Feed]:

    X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
    if X_BEARER_TOKEN is None:
        logger.error("X_BEARER_TOKEN not found in config. Cannot fetch SNS articles.")
        return

    def get_user_tweets(user_id: str, max_items: int) -> List[dict]:
        headers = {
            "Authorization": f"Bearer {X_BEARER_TOKEN}"
        }
        tweets = requests.get(
            f"https://api.twitter.com/2/users/{user_id}/tweets",
            headers=headers,
            params={"max_results": max_items}
        ).json()
        cleaned_tweets = []
        for t in tweets.get("data", []):
            if "text" in t and t["text"].strip():
                cleaned_tweets.append(t["text"].strip())
        return cleaned_tweets
    
    # Extract user_id from username from the yaml
    user_ids = []
    for user in users:
        user_info = user.get(list(user.keys())[0], {})
        user_id = user_info.get("user_id")
        if user_id:
            user_ids.append(user_id)
        else:
            logger.warning(f"No user_id found for {user} in config. Skipping.")

    tweets = [t for user_id in user_ids for t in get_user_tweets(user_id, max_items)]
    max_id = max((article.id or 0 for article in db_hndlr.retrieve_items(Feed)), default=0)
    for tweet in tweets:
        max_id += 1
        article = Feed(
            id=max_id,
            title=tweet[:50] + "..." if len(tweet) > 50 else tweet,
            link="",
            summary=tweet,
            published_at=datetime.utcnow().isoformat(),
            source="Twitter",
            keywords=[],
        )
        db_hndlr.add_item(article)
