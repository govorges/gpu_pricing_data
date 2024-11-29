"""Configuration handler for the Webdriver implementation."""

import json
from os import path

WEBDRIVER_DIR = path.dirname(path.realpath(__file__))
CONFIG_DIR = path.join(WEBDRIVER_DIR, "..", "Config")

value_map = {
    "engine": {
        "type": str,
        "allowed_values": [
            "firefox", "chromium", "webkit"
        ],
        "default": "firefox"
    },
    "headless": {
        "type": bool,
        "allowed_values": [True, False],
        "default": True
    }
}

def load_configuration() -> dict:
    """json.loads() frogscraper/Config/driver.json into a dict"""
    with open(path.join(CONFIG_DIR, "driver.json"), "r") as config_file:
        loaded_config_data = json.loads(config_file.read())
    
    built_config = {}

    for key in value_map.keys():
        expected_type = value_map[key]['type']
        allowed_values = value_map[key]['allowed_values']
        default = value_map[key].get("default")
        
        value = loaded_config_data.get(key, default)

        assert isinstance(value, expected_type), \
            f"Config/driver.json ; `{key}` was expected to be {expected_type}"
        
        assert value in allowed_values, \
            f"Config/driver.json ; `{key}` was set to a value not in allowed_values `{allowed_values}`. Provided `{value}`"

        built_config[key] = value

    return built_config

if __name__ == "__main__":
    print(load_configuration())