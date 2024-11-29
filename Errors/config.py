"""Configuration handler for the Errors implementation."""
import json
import datetime
from os import path

ERRORS_DIR = path.dirname(path.realpath(__file__))
CONFIG_DIR = path.join(ERRORS_DIR, "..", "Config")

value_map = {
    "purge": {
        "type": bool,
        "default": False
    }
}

def load_configuration() -> dict:
    """json.loads() frogscraper/Config/errors.json into a dict"""
    with open(path.join(CONFIG_DIR, "errors.json"), "r") as config_file:
        loaded_config_data = json.loads(config_file.read())

    built_config = {}

    for key in value_map.keys():
        expected_type = value_map[key]['type']
        default = value_map[key].get("default")

        value = loaded_config_data.get(key, default)

        assert isinstance(value, expected_type), \
            f"Config/errors.json ; `{key}` was expected to be {expected_type}"

        built_config[key] = value

    return built_config

