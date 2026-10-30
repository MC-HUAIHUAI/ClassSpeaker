# -*- coding: utf-8 -*-
"""账号口令哈希与登录令牌。"""
import hashlib
import hmac
import os
import re
import secrets
import threading
import time

ITERATIONS = 120000
TOKEN_TTL = 12 * 3600  # 令牌有效期（秒）

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,32}$")
MIN_PASSWORD = 6
MAX_PASSWORD = 64

DEFAULT_ADMIN_NAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def hash_password(password, salt=None):
    """返回 (salt_hex, hash_hex)。"""
    if salt is None:
        salt = os.urandom(16)
    elif isinstance(salt, str):
        salt = bytes.fromhex(salt)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, ITERATIONS
    )
    return salt.hex(), digest.hex()


def verify_password(password, salt_hex, hash_hex):
    try:
        _, candidate = hash_password(password, salt_hex)
    except Exception:
        return False
    return hmac.compare_digest(candidate, hash_hex or "")


def check_username(username):
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        return False, "用户名需为 3-32 位字母、数字、下划线、点或短横线"
    return True, ""


def check_password(password):
    password = password or ""
    if len(password) < MIN_PASSWORD:
        return False, "密码至少 {} 位".format(MIN_PASSWORD)
    if len(password) > MAX_PASSWORD:
        return False, "密码最多 {} 位".format(MAX_PASSWORD)
    return True, ""


class TokenManager(object):
    """内存令牌表。教室端独立部署，重启后教师重新登录即可。"""

    def __init__(self, ttl=TOKEN_TTL):
        self.ttl = int(ttl)
        self._lock = threading.RLock()
        self._tokens = {}

    def issue(self, user):
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = {
                "user_id": int(user["id"]),
                "username": user["username"],
                "role": user.get("role", "teacher"),
                "expire_at": time.time() + self.ttl,
            }
        return token

    def resolve(self, token):
        if not token:
            return None
        with self._lock:
            session = self._tokens.get(token)
            if not session:
                return None
            if session["expire_at"] < time.time():
                self._tokens.pop(token, None)
                return None
            return dict(session)

    def revoke(self, token):
        with self._lock:
            self._tokens.pop(token, None)

    def revoke_user(self, user_id):
        with self._lock:
            for token in [t for t, s in self._tokens.items()
                          if s["user_id"] == int(user_id)]:
                self._tokens.pop(token, None)

    def purge(self):
        now = time.time()
        with self._lock:
            for token in [t for t, s in self._tokens.items() if s["expire_at"] < now]:
                self._tokens.pop(token, None)
