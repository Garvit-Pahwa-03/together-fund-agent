import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "runs.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    with get_connection() as conn:
        # Original tables — unchanged
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_timestamp TEXT NOT NULL,
                sector_filter TEXT,
                stage_filter TEXT,
                geo_filter TEXT,
                raw_memo TEXT,
                total_startups_found INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS startups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                name TEXT NOT NULL,
                website_url TEXT,
                sector TEXT,
                founders TEXT,
                hq_location TEXT,
                score REAL,
                recommendation TEXT,
                one_line_summary TEXT,
                full_profile_json TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id),
                UNIQUE(name COLLATE NOCASE)
            )
        """)

        # Users table — new, only created if not exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

        # Safely add new columns to startups if they don't exist
        # ALTER TABLE only runs if column is missing — never breaks existing data
        new_columns = [
            ("founded_year", "TEXT"),
            ("ai_architecture", "TEXT"),
            ("competitors", "TEXT"),
            ("confidence_score", "REAL"),
            ("confidence_breakdown", "TEXT"),
            ("user_rating", "INTEGER"),
            ("user_id", "INTEGER"),
        ]
        existing = [
            row[1] for row in conn.execute(
                "PRAGMA table_info(startups)"
            ).fetchall()
        ]
        for col_name, col_type in new_columns:
            if col_name not in existing:
                conn.execute(
                    f"ALTER TABLE startups ADD COLUMN "
                    f"{col_name} {col_type}"
                )
        conn.commit()


# ── USER AUTH ─────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(
    username: str, password: str, full_name: str
) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO users
                   (username, password_hash, full_name, created_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    username.lower().strip(),
                    hash_password(password),
                    full_name,
                    datetime.now().isoformat()
                )
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def verify_user(username: str, password: str):
    """Returns user dict if valid, None if not."""
    with get_connection() as conn:
        row = conn.execute(
            """SELECT * FROM users
               WHERE username = ? AND password_hash = ?""",
            (
                username.lower().strip(),
                hash_password(password)
            )
        ).fetchone()
    return dict(row) if row else None


# ── ORIGINAL FUNCTIONS — completely unchanged ─────────────

def get_all_seen_startup_names() -> list:
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT name FROM startups ORDER BY id DESC"
            ).fetchall()
        return [row["name"] for row in rows]
    except Exception:
        return []


def save_run(sector, stage, geo, memo, startups) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO runs
               (run_timestamp, sector_filter, stage_filter,
                geo_filter, raw_memo, total_startups_found)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                sector, stage, geo, memo, len(startups)
            )
        )
        run_id = cursor.lastrowid

        for s in startups:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO startups
                       (run_id, name, website_url, sector,
                        founders, hq_location, score,
                        recommendation, one_line_summary,
                        full_profile_json, founded_year,
                        ai_architecture, competitors,
                        confidence_score, confidence_breakdown)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        run_id,
                        s.get("name", ""),
                        s.get("website_url", ""),
                        s.get("sector", ""),
                        s.get("founders", ""),
                        s.get("hq_location", ""),
                        s.get("score", 0.0),
                        s.get("recommendation", ""),
                        s.get("one_line_summary", ""),
                        json.dumps(s),
                        s.get("founded_year", ""),
                        s.get("ai_architecture", ""),
                        s.get("competitors", ""),
                        s.get("confidence_score", 0.0),
                        s.get("confidence_breakdown", ""),
                    )
                )
            except Exception as e:
                print(f"[DB] Skipping duplicate: {e}")

        conn.commit()
    return run_id


def get_all_runs() -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY run_timestamp DESC LIMIT 20"
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_startups() -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM startups ORDER BY score DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def startup_already_analyzed(name: str) -> bool:
    with get_connection() as conn:
        result = conn.execute(
            "SELECT id FROM startups WHERE LOWER(name) = LOWER(?)",
            (name,)
        ).fetchone()
    return result is not None


def clear_memory():
    with get_connection() as conn:
        conn.execute("DELETE FROM startups")
        conn.execute("DELETE FROM runs")
        conn.commit()


def update_user_rating(startup_id: int, rating: int):
    with get_connection() as conn:
        conn.execute(
            "UPDATE startups SET user_rating = ? WHERE id = ?",
            (rating, startup_id)
        )
        conn.commit()