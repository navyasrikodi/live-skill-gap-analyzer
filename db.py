import sqlite3

DB_PATH = "analyzer.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS inputs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resume_text TEXT NOT NULL,
        target_role TEXT NOT NULL,
        city TEXT NOT NULL,
        hours_per_week INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS postings (
        id TEXT PRIMARY KEY,
        input_id INTEGER,
        title TEXT,
        company TEXT,
        city TEXT,
        source TEXT,
        url TEXT,
        description TEXT,
        dedup_key TEXT,
        retrieved_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS skill_counts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        input_id INTEGER,
        skill TEXT,
        posting_count INTEGER,
        posting_ids TEXT
    );

    CREATE TABLE IF NOT EXISTS gaps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        input_id INTEGER,
        skill TEXT,
        status TEXT,
        resume_evidence TEXT,
        reason TEXT
    );

    CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_id TEXT UNIQUE,
        input_id INTEGER,
        proposed_change TEXT,
        approval_status TEXT,
        approved_version TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        kind TEXT,
        is_live INTEGER,
        status_code INTEGER,
        checked_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS test_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_case TEXT,
        input_desc TEXT,
        expected TEXT,
        actual TEXT,
        evidence TEXT,
        passed INTEGER,
        run_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    conn = get_conn()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    conn.close()
    print("Tables created:")
    for t in tables:
        print(" -", t["name"])