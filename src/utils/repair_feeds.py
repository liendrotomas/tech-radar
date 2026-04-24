import json
from pathlib import Path
from typing import Any

# Define the Feed and FounderFeed structures
FEED_FIELDS = {
    "id",
    "title",
    "link",
    "summary",
    "published_at",
    "source",
    "keywords",
}

FOUNDER_FEED_FIELDS = {
    "feed_id",
    "founder_name",
    "signal_score",
    "noise_score",
    "is_noise",
    "processing_metadata",
    "enriched",
    "processed",
}


def extract_feed_fields(item: dict[str, Any]) -> dict[str, Any]:
    """Extract only Feed fields from an item."""
    return {field: item[field] for field in FEED_FIELDS if field in item}


def extract_founder_feed_fields(item: dict[str, Any]) -> dict[str, Any]:
    """Extract only FounderFeed fields from an item."""
    return {field: item[field] for field in FOUNDER_FEED_FIELDS if field in item}


def repair_feeds():
    """Read feeds.json, reorganize fields, and export as structured JSONs."""
    input_path = Path("outputs/feeds.json")
    output_dir = Path("outputs")

    # Read the input file
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    feeds = []
    founder_feeds = []

    # Process each item
    for item in data if isinstance(data, list) else [data]:
        # Extract Feed fields
        feed = extract_feed_fields(item)
        feeds.append(feed)

    # Export the reorganized data
    with open(output_dir / "feeds_repaired.json", "w", encoding="utf-8") as f:
        json.dump(feeds, f, indent=2)

    if founder_feeds:
        with open(
            output_dir / "founder_feeds_repaired.json", "w", encoding="utf-8"
        ) as f:
            json.dump(founder_feeds, f, indent=2)

    print(f"✓ Repaired {len(feeds)} feeds")


if __name__ == "__main__":
    repair_feeds()
