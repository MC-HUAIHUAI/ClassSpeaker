# -*- coding: utf-8 -*-
"""数据存储（sqlite3，标准库）。

两张表：
  users    教师 / 管理员账号，含审批状态
  messages 教师发出的消息及"确认收到"状态
"""
import sqlite3
import threading

from . import paths, util


class Store(object):
    def __init__(self, db_path=None):
        paths.ensure_dirs()
        self.path = db_path or paths.DB_PATH
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        self._create_tables()

    # ---------- 建表 ----------
    def _create_tables(self):
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT    NOT NULL UNIQUE,
                    display_name  TEXT    NOT NULL DEFAULT '',
                    role          TEXT    NOT NULL DEFAULT 'teacher',
                    status        TEXT    NOT NULL DEFAULT 'pending',
                    salt          TEXT    NOT NULL,
                    password_hash TEXT    NOT NULL,
                    created_at    TEXT    NOT NULL DEFAULT '',
                    approved_at   TEXT    NOT NULL DEFAULT '',
                    approved_by   TEXT    NOT NULL DEFAULT '',
                    last_login    TEXT    NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id    INTEGER NOT NULL DEFAULT 0,
                    sender_name  TEXT    NOT NULL DEFAULT '',
                    content      TEXT    NOT NULL DEFAULT '',
                    created_at   TEXT    NOT NULL DEFAULT '',
                    status       TEXT    NOT NULL DEFAULT 'pending',
                    received_at  TEXT    NOT NULL DEFAULT '',
                    received_by  TEXT    NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
                CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
                """
            )
            self._conn.commit()

    # ---------- 内部 ----------
    def _exec(self, sql, args=()):
        with self._lock:
            cur = self._conn.execute(sql, args)
            self._conn.commit()
            return cur

    def _query(self, sql, args=()):
        with self._lock:
            cur = self._conn.execute(sql, args)
            return [dict(row) for row in cur.fetchall()]

    def _query_one(self, sql, args=()):
        rows = self._query(sql, args)
        return rows[0] if rows else None

    # ---------- 用户 ----------
    def create_user(self, username, salt, password_hash, display_name="",
                    role="teacher", status="pending", approved_by=""):
        now = util.now_str()
        approved_at = now if status == "approved" else ""
        cur = self._exec(
            """INSERT INTO users
               (username, display_name, role, status, salt, password_hash,
                created_at, approved_at, approved_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (username, display_name or username, role, status, salt,
             password_hash, now, approved_at, approved_by),
        )
        return cur.lastrowid

    def get_user(self, user_id):
        return self._query_one("SELECT * FROM users WHERE id = ?", (int(user_id),))

    def get_user_by_name(self, username):
        return self._query_one(
            "SELECT * FROM users WHERE lower(username) = lower(?)", (username or "",)
        )

    def list_users(self, status=None):
        if status:
            return self._query(
                "SELECT * FROM users WHERE status = ? ORDER BY id ASC", (status,)
            )
        return self._query("SELECT * FROM users ORDER BY id ASC")

    def count_users(self, status=None):
        row = self._query_one(
            "SELECT COUNT(*) AS n FROM users WHERE status = ?"
            if status else "SELECT COUNT(*) AS n FROM users",
            (status,) if status else (),
        )
        return int(row["n"]) if row else 0

    def set_user_status(self, user_id, status, approved_by=""):
        self._exec(
            """UPDATE users SET status = ?, approved_at = ?, approved_by = ?
               WHERE id = ?""",
            (status, util.now_str(), approved_by, int(user_id)),
        )

    def set_user_password(self, user_id, salt, password_hash):
        self._exec(
            "UPDATE users SET salt = ?, password_hash = ? WHERE id = ?",
            (salt, password_hash, int(user_id)),
        )

    def set_user_display_name(self, user_id, display_name):
        self._exec(
            "UPDATE users SET display_name = ? WHERE id = ?",
            (display_name or "", int(user_id)),
        )

    def touch_login(self, user_id):
        self._exec("UPDATE users SET last_login = ? WHERE id = ?",
                   (util.now_str(), int(user_id)))

    def delete_user(self, user_id):
        self._exec("DELETE FROM users WHERE id = ?", (int(user_id),))

    # ---------- 消息 ----------
    def add_message(self, sender_id, sender_name, content):
        cur = self._exec(
            """INSERT INTO messages (sender_id, sender_name, content, created_at,
                                     status, received_at, received_by)
               VALUES (?, ?, ?, ?, 'pending', '', '')""",
            (int(sender_id or 0), sender_name or "", content or "", util.now_str()),
        )
        return self.get_message(cur.lastrowid)

    def get_message(self, message_id):
        return self._query_one("SELECT * FROM messages WHERE id = ?", (int(message_id),))

    def list_messages(self, sender_id=None, limit=100):
        limit = max(1, min(1000, int(limit)))
        if sender_id is None:
            return self._query(
                "SELECT * FROM messages ORDER BY id DESC LIMIT ?", (limit,)
            )
        return self._query(
            "SELECT * FROM messages WHERE sender_id = ? ORDER BY id DESC LIMIT ?",
            (int(sender_id), limit),
        )

    def mark_received(self, message_id, received_by=""):
        self._exec(
            """UPDATE messages
               SET status = 'received', received_at = ?, received_by = ?
               WHERE id = ? AND status <> 'received'""",
            (util.now_str(), received_by, int(message_id)),
        )
        return self.get_message(message_id)

    def list_pending(self, since_hours=None, limit=50):
        """未被确认的消息，按时间正序（用于程序重启后补弹）。"""
        limit = max(1, min(500, int(limit)))
        if since_hours:
            return self._query(
                "SELECT * FROM messages WHERE status = 'pending' "
                "AND created_at >= datetime('now', 'localtime', ?) "
                "ORDER BY id ASC LIMIT ?",
                ("-{} hours".format(int(since_hours)), limit),
            )
        return self._query(
            "SELECT * FROM messages WHERE status = 'pending' "
            "ORDER BY id ASC LIMIT ?",
            (limit,),
        )

    def count_pending(self, sender_id=None):
        if sender_id is None:
            row = self._query_one(
                "SELECT COUNT(*) AS n FROM messages WHERE status = 'pending'"
            )
        else:
            row = self._query_one(
                "SELECT COUNT(*) AS n FROM messages WHERE status = 'pending' "
                "AND sender_id = ?",
                (int(sender_id),),
            )
        return int(row["n"]) if row else 0

    def purge_old(self, keep_days=30):
        keep_days = max(1, int(keep_days))
        self._exec(
            "DELETE FROM messages WHERE created_at < datetime('now', 'localtime', ?)",
            ("-{} days".format(keep_days),),
        )

    def close(self):
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass
