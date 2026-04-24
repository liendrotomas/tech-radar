"""Configuration module for Tech Radar."""

from pathlib import Path
from typing import Any, Dict
import yaml


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_file.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_config_value(config: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Get nested config value using dot notation (e.g., 'ingestion.rss.urls')."""
    keys = path.split(".")
    value = config

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value
