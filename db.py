# db.py - simple sqlite helpers
import sqlite3
from datetime import datetime

DB = "bot.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        banned INTEGER DEFAULT 0,
        free_redeem_used INTEGER DEFAULT 0,
        premium_until TEXT DEFAULT NULL,
        pending_action TEXT DEFAULT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS keys (
        key TEXT PRIMARY KEY,
        expires_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS redeem_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        details TEXT,
        created_at TEXT
    )""")
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def add_or_update_user(user_id, username, first_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if c.fetchone():
        c.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?", (username, first_name, user_id))
    else:
        c.execute("INSERT INTO users(user_id, username, first_name) VALUES (?, ?, ?)", (user_id, username, first_name))
    conn.commit()
    conn.close()

def set_pending(user_id, action):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET pending_action=? WHERE user_id=?", (action, user_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, banned, free_redeem_used, premium_until, pending_action FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "user_id": row[0],
        "username": row[1],
        "first_name": row[2],
        "banned": bool(row[3]),
        "free_redeem_used": row[4],
        "premium_until": row[5],
        "pending_action": row[6]
    }

def set_free_redeem_used(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET free_redeem_used=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def set_premium(user_id, until_iso):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET premium_until=? WHERE user_id=?", (until_iso, user_id))
    conn.commit()
    conn.close()

def add_key(key, expires_at_iso):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO keys(key, expires_at) VALUES (?, ?)", (key, expires_at_iso))
    conn.commit()
    conn.close()

def check_key(key):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT expires_at FROM keys WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    if not row: return None
    return row[0]  # iso string

def remove_key(key):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM keys WHERE key=?", (key,))
    conn.commit()
    conn.close()

def add_redeem_request(user_id, username, details):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("INSERT INTO redeem_requests(user_id, username, details, created_at) VALUES (?, ?, ?, ?)",
              (user_id, username, details, now))
    conn.commit()
    conn.close()

def set_ban(user_id, ban=1):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET banned=? WHERE user_id=?", (ban, user_id))
    conn.commit()
    conn.close()

def list_all_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows
