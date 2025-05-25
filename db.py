import sqlite3

conn = sqlite3.connect("memory.db")
c = conn.cursor()

def init_db():
    c.execute("""CREATE TABLE IF NOT EXISTS pairs (
        pair_id INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_id INTEGER,
        invitee_id INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pair_id INTEGER,
        user_id INTEGER,
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
        inviter_id INTEGER
    )""")

    conn.commit()

def save_message(user_id, pair_id, role, message):
    c.execute("INSERT INTO messages (pair_id, user_id, role, message) VALUES (?, ?, ?, ?)",
              (pair_id, user_id, role, message))
    conn.commit()

def get_role(user_id):
    c.execute("SELECT role, pair_id FROM roles WHERE user_id = ?", (user_id, ))
    row = c.fetchone()
    return (row[0], row[1]) if row else (None, None)

def assign_role(user_id, role, pair_id):
    c.execute("REPLACE INTO roles (user_id, role, pair_id) VALUES (?, ?, ?)",
              (user_id, role, pair_id))
    conn.commit()

def create_invite(user_id, invite_code):
    c.execute("INSERT OR REPLACE INTO invites (invite_code, inviter_id) VALUES (?, ?)",
              (invite_code, user_id))
    conn.commit()

def accept_invite(user_id, invite_code):
    c.execute("SELECT inviter_id FROM invites WHERE invite_code = ?", (invite_code,))
    row = c.fetchone()
    if not row:
        return None

    inviter_id = row[0]
    c.execute("INSERT INTO pairs (inviter_id, invitee_id) VALUES (?, ?)", (inviter_id, user_id))
    conn.commit()
    c.execute("DELETE FROM invites WHERE invite_code = ?", (invite_code,))
    conn.commit()

    c.execute("SELECT pair_id FROM pairs WHERE inviter_id = ? AND invitee_id = ?", (inviter_id, user_id))
    row = c.fetchone()
    return row[0] if row else None

def get_last_messages(pair_id, limit=10):
    c.execute("SELECT message FROM messages WHERE pair_id = ? ORDER BY id DESC LIMIT ?",
              (pair_id, limit))
    return [row[0] for row in c.fetchall()][::-1]

def get_partner_summary(role, pair_id):
    opposite = "wife" if role == "husband" else "husband"
    c.execute("SELECT message FROM messages WHERE role = ? AND pair_id = ? ORDER BY id DESC LIMIT 20",
              (opposite, pair_id))
    messages = [row[0] for row in c.fetchall()][::-1]
    return "\n".join(messages)

def get_user_summary(user_id, limit=20):
    c.execute("SELECT message FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
              (user_id, limit))
    messages = [row[0] for row in c.fetchall()][::-1]
    return "\n".join(messages)
