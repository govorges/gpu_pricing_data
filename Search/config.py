"""Configuration builder for the Search implementation."""
import json
from os import path

SEARCH_DIR = path.dirname(path.realpath(__file__))
CONFIG_DIR = path.join(SEARCH_DIR, "..", "Config")

def load_configuration() -> dict:
    """json.loads() frogscraper/Config/search.json into a dict"""
    with open(path.join(CONFIG_DIR, "search.json"), "r") as config_file:
        loaded_config_data = json.loads(config_file.read())

    return loaded_config_data

