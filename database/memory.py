import os
import hashlib
from datetime import datetime

from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError
from bson import ObjectId


# ── CONNECTION ────────────────────────────────────────────

_client = None


def get_db():
    """
    Returns MongoDB database object.
    Uses explicit TLS config to fix SSL handshake
    failures on Streamlit Cloud Python 3.11.
    """
    global _client
    uri = os.environ.get("MONGO_URI", "")
    if not uri:
        raise ValueError(
            "MONGO_URI not set. Add it to your .env file "
            "and Streamlit secrets."
        )
    if _client is None:
        _client = MongoClient(
            uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=20000,
            tls=True,
            tlsAllowInvalidCertificates=False,
        )
    return _client["together_fund"]


# ── INIT ──────────────────────────────────────────────────

def initialize_db():
    """
    Creates indexes on first run.
    Safe to call on every app startup.
    MongoDB ignores indexes that already exist.
    """
    try:
        db = get_db()
        db.users.create_index("username", unique=True)
        db.startups.create_index("user_id")
        db.runs.create_index("user_id")
        db.startups.create_index(
            [("user_id", 1), ("name_lower", 1)],
            unique=True
        )
    except Exception as e:
        print(f"[DB] initialize_db: {e}")


# ── AUTH ──────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(
    username: str,
    password: str,
    full_name: str
) -> bool:
    """
    Creates a new user account.
    Returns True on success, False if username already taken.
    """
    try:
        db = get_db()
        db.users.insert_one({
            "username": username.lower().strip(),
            "password_hash": hash_password(password),
            "full_name": full_name,
            "created_at": datetime.now().isoformat()
        })
        return True
    except DuplicateKeyError:
        return False
    except Exception as e:
        print(f"[DB] create_user error: {e}")
        return False


def verify_user(username: str, password: str):
    """
    Returns user dict if credentials are valid.
    Returns None if invalid.
    Converts ObjectId to string for session storage.
    """
    try:
        db = get_db()
        user = db.users.find_one({
            "username": username.lower().strip(),
            "password_hash": hash_password(password)
        })
        if user:
            user["id"] = str(user["_id"])
            user["_id"] = str(user["_id"])
            return user
        return None
    except Exception as e:
        print(f"[DB] verify_user error: {e}")
        return None


# ── MEMORY — all functions take user_id ───────────────────

def get_all_seen_startup_names(user_id) -> list:
    """
    Returns names of startups this user has already analyzed.
    The agent uses this list to skip previously seen startups.
    Accepts both int and string user_id safely.
    """
    try:
        db = get_db()
        docs = db.startups.find(
            {"user_id": str(user_id)},
            {"name": 1, "_id": 0}
        ).sort("_id", DESCENDING)
        return [doc["name"] for doc in docs]
    except Exception as e:
        print(f"[DB] get_all_seen_startup_names error: {e}")
        return []


def save_run(
    sector: str,
    stage: str,
    geo: str,
    memo: str,
    startups: list,
    user_id
) -> str:
    """
    Saves a completed run and all its startups to MongoDB.
    Returns the run_id as a string.
    Silently skips duplicate startups for the same user.
    Accepts both int and string user_id safely.
    """
    try:
        db = get_db()

        run_doc = {
            "user_id": str(user_id),
            "run_timestamp": datetime.now().isoformat(),
            "sector_filter": sector,
            "stage_filter": stage,
            "geo_filter": geo,
            "raw_memo": memo,
            "total_startups_found": len(startups)
        }
        run_result = db.runs.insert_one(run_doc)
        run_id = str(run_result.inserted_id)

        for s in startups:
            try:
                db.startups.insert_one({
                    "user_id": str(user_id),
                    "run_id": run_id,
                    "name": s.get("name", ""),
                    "name_lower": (
                        s.get("name", "").lower().strip()
                    ),
                    "website_url": s.get("website_url", ""),
                    "sector": s.get("sector", ""),
                    "founders": s.get("founders", ""),
                    "hq_location": s.get("hq_location", ""),
                    "founded_year": s.get("founded_year", ""),
                    "score": s.get("score", 0.0),
                    "recommendation": s.get("recommendation", ""),
                    "one_line_summary": s.get(
                        "one_line_summary", ""
                    ),
                    "ai_architecture": s.get(
                        "ai_architecture", ""
                    ),
                    "competitors": s.get("competitors", ""),
                    "confidence_score": s.get(
                        "confidence_score", 0.0
                    ),
                    "confidence_breakdown": s.get(
                        "confidence_breakdown", ""
                    ),
                    "user_rating": None,
                    "created_at": datetime.now().isoformat()
                })
            except DuplicateKeyError:
                print(
                    f"[DB] Skipping duplicate startup "
                    f"for this user: {s.get('name')}"
                )
            except Exception as e:
                print(f"[DB] Error saving startup: {e}")

        return run_id

    except Exception as e:
        print(f"[DB] save_run error: {e}")
        return ""


def get_all_runs(user_id) -> list:
    """
    Returns this user's run history newest first.
    Each dict has an 'id' key for use in Streamlit keys.
    """
    try:
        db = get_db()
        docs = db.runs.find(
            {"user_id": str(user_id)}
        ).sort("run_timestamp", DESCENDING).limit(20)

        result = []
        for doc in docs:
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
            result.append(doc)
        return result

    except Exception as e:
        print(f"[DB] get_all_runs error: {e}")
        return []


def get_all_startups(user_id) -> list:
    """
    Returns this user's startups highest score first.
    Each dict has an 'id' key for use in Streamlit keys.
    """
    try:
        db = get_db()
        docs = db.startups.find(
            {"user_id": str(user_id)}
        ).sort("score", DESCENDING)

        result = []
        for doc in docs:
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
            result.append(doc)
        return result

    except Exception as e:
        print(f"[DB] get_all_startups error: {e}")
        return []


def startup_already_analyzed(name: str, user_id) -> bool:
    """
    Returns True if this user has already analyzed
    a startup with this name.
    """
    try:
        db = get_db()
        result = db.startups.find_one({
            "user_id": str(user_id),
            "name_lower": name.lower().strip()
        })
        return result is not None
    except Exception as e:
        print(f"[DB] startup_already_analyzed error: {e}")
        return False


def clear_memory(user_id) -> None:
    """
    Wipes only this user's startups and runs.
    Never touches other users' data.
    """
    try:
        db = get_db()
        db.startups.delete_many({"user_id": str(user_id)})
        db.runs.delete_many({"user_id": str(user_id)})
    except Exception as e:
        print(f"[DB] clear_memory error: {e}")


def update_user_rating(
    startup_id,
    rating: int,
    user_id
) -> None:
    """
    Updates this user's rating for one startup.
    The user_id check ensures users can only rate
    their own startups.
    """
    try:
        db = get_db()
        db.startups.update_one(
            {
                "_id": ObjectId(str(startup_id)),
                "user_id": str(user_id)
            },
            {"$set": {"user_rating": rating}}
        )
    except Exception as e:
        print(f"[DB] update_user_rating error: {e}")