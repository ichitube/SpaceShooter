import json
import os

DATA_DIR = "data"
HS_FILE = os.path.join(DATA_DIR, "highscore.json")

def load_highscore() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(HS_FILE):
        save_highscore(0)
        return 0
    try:
        with open(HS_FILE, "r", encoding="utf-8") as f:
            return int(json.load(f).get("highscore", 0))
    except Exception:
        return 0

def save_highscore(value: int) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HS_FILE, "w", encoding="utf-8") as f:
        json.dump({"highscore": int(value)}, f, ensure_ascii=False, indent=2)
