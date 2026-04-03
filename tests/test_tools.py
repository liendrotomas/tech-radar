from src.config.config import load_config, get_config_value


def test_load_config():
    cfg = load_config(config_path="tests/regression_config.yaml")
    rss_urls = get_config_value(cfg, "ingestion.rss.urls", [])
    max_items = get_config_value(cfg, "ingestion.rss.max_items", 50)

    assert isinstance(cfg, dict), "Config should be a dictionary"
    assert isinstance(rss_urls, list), "RSS URLs should be a list"
    assert isinstance(max_items, int), "Max items should be an integer"
    assert len(rss_urls) == 5, "There should be 5 RSS URLs in the config"
    assert max_items == 10, "Max items should be 10"
