import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "runs.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    with get_connection() as conn:
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
        conn.commit()


def get_all_seen_startup_names() -> list:
    """
    Returns a list of all startup names ever analyzed.
    Used to tell the researcher what to skip.
    """
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
                       (run_id, name, website_url, sector, founders,
                        hq_location, score, recommendation,
                        one_line_summary, full_profile_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                        json.dumps(s)
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
    """Wipe all history. Called from UI reset button."""
    with get_connection() as conn:
        conn.execute("DELETE FROM startups")
        conn.execute("DELETE FROM runs")
        conn.commit()