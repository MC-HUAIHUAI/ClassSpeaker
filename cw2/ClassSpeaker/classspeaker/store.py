# -*- coding: utf-8 -*-
"""数据存储：双后端（sqlite3 / JSON）。

为什么要双后端：Class Widgets 2 的 PyInstaller 打包里**没有 sqlite3 模块**
（它自己不用数据库），插件在里面 `import sqlite3` 会直接 ModuleNotFoundError。
所以这里做成本地存储可切换：

  * 有 sqlite3  → 用 `_SqliteStore`（独立版 / exe / CW1 插件，行为不变）
  * 没有        → 用 `_JsonStore`（CW2 插件；教室级的账号与消息量，JSON 完全够）

两张表的结构与语义完全一致：users / messages。
"""
import datetime
import json
import os
import threading

from . import paths, util

try:                      # CW2 的运行时没有 sqlite3
    import sqlite3
    HAS_SQLITE = True
except Exception:         # pragma: no cover - 取决于宿主环境
    sqlite3 = None
    HAS_SQLITE = False


# ======================================================================
# 公共字段说明（两个后端共用）
#   users:    id username display_name role status salt password_hash
#             created_at approved_at approved_by last_login
#   messages: id sender_id sender_name content created_at status
#             received_at received_by
# ======================================================================

USER_DEFAULTS = {
    "display_name": "",
    "role": "teacher",
    "status": "pending",
    "created_at": "",
    "approved_at": "",
    "approved_by": "",
    "last_login": "",
}

MESSAGE_DEFAULTS = {
    "sender_id": 0,
    "sender_name": "",
    "content": "",
    "created_at": "",
    "status": "pending",
    "received_at": "",
    "received_by": "",
}


def _parse_time(text):
    try:
        return datetime.datetime.strptime(text or "", "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


# ======================================================================
# SQLite 后端（原实现，行为保持不变）
# ======================================================================
class _SqliteStore(object):
    name = "sqlite"

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


# ======================================================================
# JSON 后端（CW2 用：宿主没有 sqlite3）
# ======================================================================
class _JsonStore(object):
    name = "json"

    def __init__(self, db_path=None):
        paths.ensure_dirs()
        base = db_path or paths.DB_PATH
        self.path = os.path.splitext(base)[0] + ".json"
        self._lock = threading.RLock()
        self._data = {"users": [], "messages": [],
                      "next_user_id": 1, "next_message_id": 1}
        self._load()

    # ---------- 落盘 ----------
    def _load(self):
        raw = util.read_json(self.path, {})
        if not isinstance(raw, dict):
            raw = {}
        users = raw.get("users")
        messages = raw.get("messages")
        self._data["users"] = list(users) if isinstance(users, list) else []
        self._data["messages"] = list(messages) if isinstance(messages, list) else []
        self._data["next_user_id"] = int(raw.get("next_user_id")
                                         or (max([u.get("id", 0) for u in self._data["users"]] or [0]) + 1))
        self._data["next_message_id"] = int(raw.get("next_message_id")
                                            or (max([m.get("id", 0) for m in self._data["messages"]] or [0]) + 1))

    def _save(self):
        try:
            util.write_json_atomic(self.path, self._data)
        except Exception as exc:
            util.LOG.warn("写入 JSON 存储失败：{}".format(exc))

    # ---------- 用户 ----------
    def create_user(self, username, salt, password_hash, display_name="",
                    role="teacher", status="pending", approved_by=""):
        with self._lock:
            user_id = int(self._data["next_user_id"])
            self._data["next_user_id"] = user_id + 1
            now = util.now_str()
            record = dict(USER_DEFAULTS)
            record.update({
                "id": user_id,
                "username": username,
                "display_name": display_name or username,
                "role": role,
                "status": status,
                "salt": salt,
                "password_hash": password_hash,
                "created_at": now,
                "approved_at": now if status == "approved" else "",
                "approved_by": approved_by,
            })
            self._data["users"].append(record)
            self._save()
            return user_id

    def _find_user(self, user_id):
        for user in self._data["users"]:
            if int(user.get("id", 0)) == int(user_id):
                return user
        return None

    def get_user(self, user_id):
        with self._lock:
            user = self._find_user(user_id)
            return dict(user) if user else None

    def get_user_by_name(self, username):
        with self._lock:
            target = (username or "").lower()
            for user in self._data["users"]:
                if (user.get("username") or "").lower() == target:
                    return dict(user)
            return None

    def list_users(self, status=None):
        with self._lock:
            rows = [dict(u) for u in self._data["users"]
                    if not status or u.get("status") == status]
            return sorted(rows, key=lambda u: int(u.get("id", 0)))

    def count_users(self, status=None):
        with self._lock:
            if not status:
                return len(self._data["users"])
            return len([u for u in self._data["users"] if u.get("status") == status])

    def set_user_status(self, user_id, status, approved_by=""):
        with self._lock:
            user = self._find_user(user_id)
            if user is None:
                return
            user["status"] = status
            user["approved_at"] = util.now_str()
            user["approved_by"] = approved_by
            self._save()

    def set_user_password(self, user_id, salt, password_hash):
        with self._lock:
            user = self._find_user(user_id)
            if user is None:
                return
            user["salt"] = salt
            user["password_hash"] = password_hash
            self._save()

    def set_user_display_name(self, user_id, display_name):
        with self._lock:
            user = self._find_user(user_id)
            if user is None:
                return
            user["display_name"] = display_name or ""
            self._save()

    def touch_login(self, user_id):
        with self._lock:
            user = self._find_user(user_id)
            if user is None:
                return
            user["last_login"] = util.now_str()
            self._save()

    def delete_user(self, user_id):
        with self._lock:
            self._data["users"] = [u for u in self._data["users"]
                                   if int(u.get("id", 0)) != int(user_id)]
            self._save()

    # ---------- 消息 ----------
    def add_message(self, sender_id, sender_name, content):
        with self._lock:
            message_id = int(self._data["next_message_id"])
            self._data["next_message_id"] = message_id + 1
            record = dict(MESSAGE_DEFAULTS)
            record.update({
                "id": message_id,
                "sender_id": int(sender_id or 0),
                "sender_name": sender_name or "",
                "content": content or "",
                "created_at": util.now_str(),
                "status": "pending",
            })
            self._data["messages"].append(record)
            self._save()
            return dict(record)

    def _find_message(self, message_id):
        for message in self._data["messages"]:
            if int(message.get("id", 0)) == int(message_id):
                return message
        return None

    def get_message(self, message_id):
        with self._lock:
            message = self._find_message(message_id)
            return dict(message) if message else None

    def list_messages(self, sender_id=None, limit=100):
        limit = max(1, min(1000, int(limit)))
        with self._lock:
            rows = [dict(m) for m in self._data["messages"]
                    if sender_id is None or int(m.get("sender_id", 0)) == int(sender_id)]
            rows.sort(key=lambda m: int(m.get("id", 0)), reverse=True)
            return rows[:limit]

    def mark_received(self, message_id, received_by=""):
        with self._lock:
            message = self._find_message(message_id)
            if message is None:
                return None
            if message.get("status") != "received":
                message["status"] = "received"
                message["received_at"] = util.now_str()
                message["received_by"] = received_by
                self._save()
            return dict(message)

    def list_pending(self, since_hours=None, limit=50):
        limit = max(1, min(500, int(limit)))
        with self._lock:
            rows = []
            threshold = None
            if since_hours:
                threshold = datetime.datetime.now() - datetime.timedelta(
                    hours=int(since_hours))
            for message in self._data["messages"]:
                if message.get("status") != "pending":
                    continue
                if threshold is not None:
                    created = _parse_time(message.get("created_at"))
                    if created is None or created < threshold:
                        continue
                rows.append(dict(message))
            rows.sort(key=lambda m: int(m.get("id", 0)))
            return rows[:limit]

    def count_pending(self, sender_id=None):
        with self._lock:
            return len([
                m for m in self._data["messages"]
                if m.get("status") == "pending"
                and (sender_id is None
                     or int(m.get("sender_id", 0)) == int(sender_id))
            ])

    def purge_old(self, keep_days=30):
        keep_days = max(1, int(keep_days))
        threshold = datetime.datetime.now() - datetime.timedelta(days=keep_days)
        with self._lock:
            kept = []
            for message in self._data["messages"]:
                created = _parse_time(message.get("created_at"))
                if created is not None and created < threshold:
                    continue
                kept.append(message)
            if len(kept) != len(self._data["messages"]):
                self._data["messages"] = kept
                self._save()

    def close(self):
        with self._lock:
            self._save()


# ======================================================================
# 对外入口
# ======================================================================
class Store(object):
    """按宿主能力自动选后端；也可用 backend= 强制（测试用）。"""

    def __new__(cls, db_path=None, backend=None):
        choice = (backend or os.environ.get("CLASSSPEAKER_STORE") or "auto").lower()
        if choice == "json":
            return _JsonStore(db_path)
        if choice == "sqlite":
            if not HAS_SQLITE:
                raise RuntimeError("宿主没有 sqlite3，无法使用 sqlite 后端")
            return _SqliteStore(db_path)
        if HAS_SQLITE:
            return _SqliteStore(db_path)
        util.LOG.info("宿主没有 sqlite3，改用 JSON 存储：{}".format(
            os.path.splitext(db_path or paths.DB_PATH)[0] + ".json"))
        return _JsonStore(db_path)
