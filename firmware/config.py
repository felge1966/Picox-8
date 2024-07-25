import json
import errno

def load():
  try:
    with open("config.json", "r") as f:
      return json.loads(f.read())
  except OSError as exc:
    if exc.errno == errno.ENOENT:
      return {}
    else:
      pass

def save():
  with open("config.json", "w") as f:
    f.write(json.dumps(config))

  
config = load()

def get(key):
  if key in config:
    return config[key]

def set(key, value):
  config[key] = value
  save()
