from src.database.database import Database, Feed
from src.utils.logger import get_logger

logger = get_logger("database.tools")


def import_from_csv(file_path, args):
    """Import data from a CSV file and return a list of dictionaries."""
    import csv

    with open(file_path, mode="r", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        feed_data = [row for row in reader]

    db_hndlr = Database(
        args.database_file,
        recreate_on_schema_change=getattr(args, "recreate_on_schema_change", False),
    )
    existing_articles = db_hndlr.retrieve_items(Feed)
    max_id = max((article.id or 0 for article in existing_articles), default=0) + 1
    existing_urls = {
        article.link for article in existing_articles if getattr(article, "link", None)
    }
    for row in feed_data:
        # Get urls from existing articles to avoid duplicates
        if row.get("Link", "") in existing_urls:
            logger.info(f"Skipping duplicate article with link: {row.get('Link', '')}")
            continue
        article = Feed(
            id=max_id,
            title=row.get("Title", "Untitled"),
            link=row.get("Link", ""),
            summary=row.get("Abstract", ""),
            published_at=row.get("Date", ""),
            source=row.get("Source", ""),
            keywords=(
                row.get("Industries", "").split(",") if row.get("Industries") else []
            ),
        )
        db_hndlr.add_item(article)
        max_id += 1
