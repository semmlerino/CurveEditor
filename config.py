#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
from typing import Dict, Any

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_config.json')

def load_config() -> Dict[str, Any]:
    """Load application configuration from file."""
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Config file doesn't exist, return empty config
        return {}
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in config file: {str(e)}")
        return {}
    except IOError as e:
        print(f"Error reading config file: {str(e)}")
        return {}

def save_config(config: Dict[str, Any]) -> bool:
    """Save application configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except IOError as e:
        print(f"Error writing to config file: {str(e)}")
        return False
    except json.JSONEncodeError as e:
        print(f"Error encoding config to JSON: {str(e)}")
        return False

def get_last_file_path() -> str:
    """Get the last loaded file path from config."""
    config = load_config()
    return config.get('last_file_path', '')

def set_last_file_path(file_path: str) -> bool:
    """Save the last loaded file path to config."""
    config = load_config()
    config['last_file_path'] = file_path
    return save_config(config)

def get_last_folder_path() -> str:
    """Get the last used folder path from config."""
    config = load_config()
    return config.get('last_folder_path', '')

def set_last_folder_path(folder_path: str) -> bool:
    """Save the last used folder path to config."""
    config = load_config()
    config['last_folder_path'] = folder_path
    return save_config(config)

def get_last_image_sequence_path() -> str:
    """Get the last loaded image sequence path from config."""
    config = load_config()
    return config.get('last_image_sequence_path', '')

def set_last_image_sequence_path(sequence_path: str) -> bool:
    """Save the last loaded image sequence path to config."""
    config = load_config()
    config['last_image_sequence_path'] = sequence_path
    return save_config(config)
