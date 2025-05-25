import sqlite3

conn = sqlite3.connect("memory.db")
c = conn.cursor()


def init_db():
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        message TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS roles (
        user_id INTEGER PRIMARY KEY,
        role TEXT
    )""")
    conn.commit()


def save_message(user_id, role, message):
    c.execute("INSERT INTO messages (user_id, role, message) VALUES (?, ?, ?)",
              (user_id, role, message))
    conn.commit()


def get_role(user_id):
    c.execute("SELECT role FROM roles WHERE user_id = ?", (user_id, ))
    row = c.fetchone()
    return row[0] if row else None


def assign_role(user_id, role):
    c.execute("REPLACE INTO roles (user_id, role) VALUES (?, ?)",
              (user_id, role))
    conn.commit()


def get_last_messages(user_id, limit=10):
    c.execute(
        "SELECT message FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit))
    return [row[0] for row in c.fetchall()][::-1]


def get_partner_summary(role):
    opposite = "wife" if role == "husband" else "husband"
    c.execute(
        "SELECT message FROM messages WHERE role = ? ORDER BY id DESC LIMIT 20",
        (opposite, ))
    messages = [row[0] for row in c.fetchall()][::-1]
    return "\n".join(messages)


def get_user_summary(user_id, limit=20):
    c.execute(
        "SELECT message FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit))
    messages = [row[0] for row in c.fetchall()][::-1]
    return "\n".join(messages)
