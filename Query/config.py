"""Configuration builder for the Query implementation."""
import json
from os import path

QUERY_DIR = path.dirname(path.realpath(__file__))
CONFIG_DIR = path.join(QUERY_DIR, "..", "Config")

def load_configuration() -> dict:
    """json.loads() frogscraper/Config/query.json into a dict"""
    with open(path.join(CONFIG_DIR, "query.json"), "r") as config_file:
        loaded_config_data = json.loads(config_file.read())

    return loaded_config_data

 