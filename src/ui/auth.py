"""Local accounts for the panel: salted PBKDF2 hashes and signed session cookies.

Everything lives in .cache/ (gitignored). This guards a local dashboard; it is
not meant to face the internet.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import time
from pathlib import Path

CACHE = Path(__file__).parent / ".cache"
USERS = CACHE / "users.json"
SECRET = CACHE / "secret"
ITERATIONS = 240_000
SESSION_SECONDS = 12 * 3600
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MIN_PASSWORD = 8


def _users() -> dict[str, dict]:
    try:
        data = json.loads(USERS.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS).hex()


def _secret() -> bytes:
    try:
        return bytes.fromhex(SECRET.read_text().strip())
    except (OSError, ValueError):
        CACHE.mkdir(exist_ok=True)
        key = secrets.token_bytes(32)
        SECRET.write_text(key.hex())
        SECRET.chmod(0o600)
        return key


def register(name: str, password: str) -> str | None:
    """Return an error message, or None when the account was created."""
    if not NAME_RE.match(name):
        return "Kullanıcı adı 3–32 karakter olmalı; harf, rakam, nokta, tire ve alt çizgi kullanılabilir."
    if len(password) < MIN_PASSWORD:
        return f"Şifre en az {MIN_PASSWORD} karakter olmalı."
    users = _users()
    if name.lower() in (u.lower() for u in users):
        return "Bu kullanıcı adı alınmış."
    salt = secrets.token_bytes(16)
    users[name] = {"salt": salt.hex(), "hash": _hash(password, salt)}
    CACHE.mkdir(exist_ok=True)
    USERS.write_text(json.dumps(users, indent=1), encoding="utf-8")
    USERS.chmod(0o600)
    return None


def check(name: str, password: str) -> bool:
    user = _users().get(name)
    if not user:
        _hash(password, b"timing-equaliser")  # same cost whether or not the name exists
        return False
    return hmac.compare_digest(user["hash"], _hash(password, bytes.fromhex(user["salt"])))


def issue(name: str) -> str:
    payload = f"{name}|{int(time.time()) + SESSION_SECONDS}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def verify(token: str | None) -> str | None:
    """The user a session cookie belongs to, or None if it is forged or expired."""
    try:
        name, expires, sig = (token or "").split("|")
        good = hmac.new(_secret(), f"{name}|{expires}".encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, good) and int(expires) > time.time() and name in _users():
            return name
    except ValueError:
        pass
    return None
