import json
from pathlib import Path

USER_DIR = Path("data/users")
USER_DIR.mkdir(parents=True, exist_ok=True)

def load_user(username):
    path = USER_DIR / f"{username}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        profile = {
            "username": username,
            "xp": 0,
            "streak": 0,
            "question_progress": {}
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
        return profile

def save_user(profile):
    path = USER_DIR / f"{profile['username']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
