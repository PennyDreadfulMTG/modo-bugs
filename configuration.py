import json
import os

DEFAULTS = {
    'github_user': '',
    'github_password': '',
}

def get(key: str) -> str:
    "Retrieves values from config.json"
    try:
        cfg = json.load(open('config.json'))
    except FileNotFoundError:
        cfg = {}
    if key in cfg:
        return cfg[key]
    elif key in os.environ:
        cfg[key] = os.environ[key]
    else:
        # Lock in the default value if we use it.
        cfg[key] = DEFAULTS[key]
    print("CONFIG: {0}={1}".format(key, cfg[key]))
    config_file = open('config.json', 'w')
    config_file.write(json.dumps(cfg, indent=4))
    return cfg[key]
