def update_feed_database(feeds, output_file=None):
    """Save feed outputs in database as json."""
    import json, os
    from src.utils.logger import get_logger

    database_file = output_file or "data/feeds.json"
    # create the directory if it doesn't exist
    os.makedirs(os.path.dirname(database_file), exist_ok=True)

    if not os.path.exists(database_file):
        with open(database_file, "w") as f:
            json.dump([], f)

    with open(database_file, "r+") as f:
        database = json.load(f)

    existing_urls = set(entry["url"] for entry in database)
    # Add id number to each feed and filter out any feed that has same url as existing entries to avoid duplicates
    for i, feed in enumerate(feeds):
        feed["id"] = i + 1

    new_feeds = [feed for feed in feeds if feed.get("url") not in existing_urls]

    if not new_feeds:
        get_logger("database").info("No new feeds to add.")
        return

    database.extend(new_feeds)

    with open(database_file, "w") as f:
        json.dump(database, f, indent=2)

    get_logger("database").info(
        f"Database updated with {len(new_feeds)} new feeds. Total entries: {len(database)}"
    )


def update_opportunity_database(opportunities, output_file=None):
    """Save outputs in database as json from templates/outputs.py"""
    # Load templates
    from templates.outputs import opportunity_template
    import json, datetime, os
    from src.utils.logger import get_logger

    # Open database and load existing data if file exists else initialize empty database
    database_file = output_file
    # create the directory if it doesn't exist
    os.makedirs(os.path.dirname(database_file), exist_ok=True)
    if not os.path.exists(database_file):
        with open(database_file, "w") as f:
            json.dump([], f)

    with open(database_file, "r+") as f:
        database = json.load(f)

    # For the already existineg entries, filter out any entry that has similar name or description to the new opportunities to avoid duplicates
    existing_names = set(entry["name"] for entry in database)
    existing_descriptions = set(entry["description"] for entry in database)
    opportunities = [
        opp
        for opp in opportunities
        if opp.get("name") not in existing_names
        and opp["original"].get("description") not in existing_descriptions
    ]
    # Extract last id and increment for new entries
    last_id = max([entry["id"] for entry in database], default=0)
    for opp in opportunities:
        new_entry = opportunity_template.copy()
        last_id += 1
        new_entry["id"] = last_id
        new_entry["name"] = opp.get("name")
        new_entry["description"] = opp["original"].get("description")
        new_entry["score"] = opp.get("score")
        new_entry["why_now"] = opp["original"].get("why_now")
        new_entry["founder_fit"] = opp["original"].get("founder_fit")
        new_entry["wedge"] = opp["original"].get("wedge")
        new_entry["wedge_score"] = opp["original"].get("wedge_score")
        new_entry["risk"] = opp["original"].get("risk")
        new_entry["required_insight"] = opp["original"].get("required_insight")
        database.append(new_entry)

    # Append new entries to database file
    with open(database_file, "w") as f:
        json.dump(database, f, indent=2)

    get_logger("database").info(
        f"Database updated with {len(opportunities)} new opportunities. Total entries: {len(database)}"
    )


def log_pipeline_run(log_data, log_file=None):
    """Save pipeline run logs in database as json from templates/logs.py"""
    from templates.logs import log_pipeline_template
    import json, datetime, os
    from src.utils.logger import get_logger

    # Open database and load existing data if file exists else initialize empty database
    database_file = log_file
    # create the directory if it doesn't exist
    os.makedirs(os.path.dirname(database_file), exist_ok=True)
    if not os.path.exists(database_file):
        with open(database_file, "w") as f:
            json.dump([], f)

    with open(database_file, "r+") as f:
        database = json.load(f)

    new_log = log_pipeline_template.copy()
    new_log["date"] = datetime.datetime.now().isoformat()
    new_log["articles_count"] = log_data.get("articles_count", 0)
    new_log["filtered_count"] = log_data.get("filtered_count", 0)
    new_log["opportunities_count"] = log_data.get("opportunities_count", 0)

    database.append(new_log)

    # Append new log entry to database file
    with open(database_file, "w") as f:
        json.dump(database, f, indent=2)

    get_logger("database").info(
        f"Pipeline run logged. Total log entries: {len(database)}"
    )
