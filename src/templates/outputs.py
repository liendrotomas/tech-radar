opportunity_template = {
    "id": "int",
    "name": "str",
    "score": "int",
    "description": "str",
    "why_now": "str",
    "founder_fit": "str",
    "wedge": "str",
    "wedge_score": "int",
    "risk": "str",
    "required_insight": "str",
}

signal_template = {
    "id": "...",
    "title": "...",
    "url": "...",
    "date": "...",
    "tags": [...],
}

feed_template = {
    "id": "int",
    "title": "str",
    "link": "str",
    "summary": "str",
    "published_at": "str",
    "source": "str",
    "keywords": [],
}

# Enriched article template after LLM processing. Does not include the original fields in the feed template.
enriched_template = {
    "is_noise": "bool",
    "signal_score": "int",
    "noise_score": "int",
    "enriched": {"what": "...", "why": "...", "opportunity": "...", "tags": [...]},
    "processing metadata": {
        "last_processed": "2026-04-04",
        "version": "int",
        "model": "str",
        "threshold_signal": "float",
        "threshold_noise": "float",
        "categories": [...],
    },
}
