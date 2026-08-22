import json
import os
from datetime import date

DATA_FILE = "visitor_data.json"


def _load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "date": str(date.today()),
            "today": 0,
            "total": 0
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if data.get("date") != str(date.today()):
            data["date"] = str(date.today())
            data["today"] = 0

        return data

    except Exception:
        return {
            "date": str(date.today()),
            "today": 0,
            "total": 0
        }


def _save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def add_visit():
    data = _load_data()

    data["today"] += 1
    data["total"] += 1

    _save_data(data)

    return data


def get_visits():
    data = _load_data()

    _save_data(data)

    return {
        "today": data["today"],
        "total": data["total"]
    }
