#!/usr/bin/env python3
import sqlite3
from threading import Lock


class BotDB:
    def __init__(self, path):
        self._lock = Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)

    def __del__(self):
        self._conn.close()

    def create_tables(self):
        with self._lock:
            if self._conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone() is not None:
                return
            self._conn.execute('CREATE TABLE IF NOT EXISTS users (id int, name str, PRIMARY KEY (id));')
            self._conn.execute('CREATE TABLE IF NOT EXISTS submissions (id int, reviewer int, PRIMARY KEY (id), FOREIGN KEY (reviewer) REFERENCES users(id));')
            self._conn.execute('CREATE INDEX IF NOT EXISTS idx_reviewer ON submissions(reviewer);')
            self._conn.commit()

    def add_user(self, uid, name):
        with self._lock:
            self._conn.execute('INSERT OR IGNORE INTO users(id, name) VALUES (?, ?)', (uid, name))

    def add_submission(self, sub_id, uid):
        with self._lock:
            self._conn.execute('INSERT OR IGNORE INTO submissions(id, reviewer) VALUES (?, ?)', (sub_id, uid))

    def commit(self):
        with self._lock:
            self._conn.commit()


def main():
    """Create DB from old messages.

    Two files are needed (generated by other means):
    - `users.json`. Stores a dict of { abbrev_name: [id, full_name] }.
    - `msgcat.txt`. Contains concatenated messages (joined with newlines).
    """

    import json
    import re
    from pathlib import Path

    cwd = Path.cwd().resolve()
    db_path = cwd/'caos.db'
    db = BotDB(db_path)
    db.create_tables()

    user_file = cwd/'users.json'
    msg_file = cwd/'msgcat.txt'

    if not user_file.exists():
        print('users.json is not found')
        return
    if not msg_file.exists():
        print('msgcat.txt is not found')
        return

    with open(user_file) as f:
        users = json.load(f)

    for uid, name in users.values():
        db.add_user(uid, name)
    db.commit()

    with open(msg_file) as f:
        lines = f.read().split('\n')

    for line in lines:
        m = re.search(r'\[.+?\] (\d+) - .* \[(.+?)\]', line)
        if not m:
            continue
        sub_id, user = m.groups()
        if user not in users:
            continue
        db.add_submission(sub_id, users[user][0])
    db.commit()


if __name__ == '__main__':
    main()
