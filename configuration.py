import json
import os

DEFAULTS = {
    'github_user': '',
    'github_password': '',
}

def get(key):
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
    fh = open('config.json', 'w')
    fh.write(json.dumps(cfg, indent=4))
    return cfg[key]
