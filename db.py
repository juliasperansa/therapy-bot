import sqlite3
import datetime
import os

# Автоматическое создание БД, если она по какой-то причине улетела в ад
DB_PATH = "memory.db"
should_init = not os.path.exists(DB_PATH)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

if should_init:
    print("[DB] Создаём новую базу данных, старую не нашли.")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        pair_id INTEGER,
        role TEXT,
        message TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS roles (
        user_id INTEGER PRIMARY KEY,
        role TEXT,
        pair_id INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS invites (
        invite_code TEXT PRIMARY KEY,
        inviter_id INTEGER,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS pairs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_id INTEGER,
        invitee_id INTEGER
    )""")
    conn.commit()


def init_db():
    # На всякий случай вручную вызвать можно, но чаще уже не надо
    pass


def save_message(user_id, pair_id, role, message):
    c.execute(
        "INSERT INTO messages (user_id, pair_id, role, message) VALUES (?, ?, ?, ?)",
        (user_id, pair_id, role, message)
    )
    conn.commit()


def get_role(user_id):
    c.execute("SELECT role FROM roles WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    return row[0] if row else None


def get_pair_id(user_id):
    c.execute("SELECT pair_id FROM roles WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    return row[0] if row else None


def assign_role(user_id, role, pair_id):
    c.execute(
        "REPLACE INTO roles (user_id, role, pair_id) VALUES (?, ?, ?)",
        (user_id, role, pair_id)
    )
    conn.commit()


def create_invite(invite_code, inviter_id):
    now = datetime.datetime.utcnow().isoformat()
    c.execute("INSERT INTO invites (invite_code, inviter_id, created_at) VALUES (?, ?, ?)",
              (invite_code, inviter_id, now))
    conn.commit()


def use_invite(invite_code, user_id):
    c.execute("SELECT inviter_id FROM invites WHERE invite_code = ?", (invite_code,))
    row = c.fetchone()
    if not row:
        return None
    inviter_id = row[0]

    c.execute("INSERT INTO pairs (inviter_id, invitee_id) VALUES (?, ?)", (inviter_id, user_id))
    conn.commit()

    c.execute("SELECT id FROM pairs WHERE inviter_id = ? AND invitee_id = ?", (inviter_id, user_id))
    row = c.fetchone()
    if row:
        pair_id = row[0]
        assign_pair_id_to_inviter(inviter_id, pair_id)
        c.execute("DELETE FROM invites WHERE invite_code = ?", (invite_code,))
        conn.commit()
        return pair_id
    return None


def assign_pair_id_to_inviter(user_id, pair_id):
    c.execute("UPDATE roles SET pair_id = ? WHERE user_id = ?", (pair_id, user_id))
    conn.commit()


def get_last_messages(pair_id, limit=10):
    c.execute("SELECT message FROM messages WHERE pair_id = ? ORDER BY id DESC LIMIT ?", (pair_id, limit))
    return [row[0] for row in c.fetchall()][::-1]


def get_partner_summary(role, pair_id):
    opposite = "wife" if role == "husband" else "husband"
    c.execute("SELECT message FROM messages WHERE role = ? AND pair_id = ? ORDER BY id DESC LIMIT 20", (opposite, pair_id))
    messages = [row[0] for row in c.fetchall()][::-1]
    return "\n".join(messages)


def get_user_summary(user_id, limit=20):
    c.execute("SELECT message FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    messages = [row[0] for row in c.fetchall()][::-1]
    return "\n".join(messages)


def get_pending_invites_older_than(hours):
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(hours=hours)).isoformat()
    c.execute("SELECT inviter_id, invite_code FROM invites WHERE created_at <= ?", (cutoff,))
    return c.fetchall()
