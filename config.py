#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_config.json')

def load_config():
    """Load application configuration from file."""
    if not os.path.exists(CONFIG_FILE):
        return {}
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return {}

def save_config(config):
    """Save application configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {str(e)}")
        return False

def get_last_file_path():
    """Get the last loaded file path from config."""
    config = load_config()
    return config.get('last_file_path', '')

def set_last_file_path(file_path):
    """Save the last loaded file path to config."""
    config = load_config()
    config['last_file_path'] = file_path
    return save_config(config)

def get_last_folder_path():
    """Get the last used folder path from config."""
    config = load_config()
    return config.get('last_folder_path', '')

def set_last_folder_path(folder_path):
    """Save the last used folder path to config."""
    config = load_config()
    config['last_folder_path'] = folder_path
    return save_config(config)

def get_last_image_sequence_path():
    """Get the last loaded image sequence path from config."""
    config = load_config()
    return config.get('last_image_sequence_path', '')

def set_last_image_sequence_path(sequence_path):
    """Save the last loaded image sequence path to config."""
    config = load_config()
    config['last_image_sequence_path'] = sequence_path
    return save_config(config)