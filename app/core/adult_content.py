"""Cryptographic authentication, security questions and visibility state for adult content."""
import hashlib
import json
import os
import secrets
from typing import Dict, List, Optional, Tuple
from app import db

SALT_LEN = 16
HASH_ITERATIONS = 200_000

DEFAULT_SECURITY_QUESTIONS = [
    "What was the title of your first favorite anime?",
    "What was the name of your first childhood pet or character?",
    "In what city or hometown were you born?",
    "What was the first video game you ever completed?",
    "What was your childhood nickname or handle?",
]

# In-memory runtime unlock state. Defaults to False.
_session_unlocked: bool = False


def _hash_secret(value: str, salt: bytes) -> str:
    normalized = value.strip().casefold()
    digest = hashlib.pbkdf2_hmac("sha256", normalized.encode("utf-8"), salt, HASH_ITERATIONS)
    return digest.hex()


def is_password_configured() -> bool:
    return bool(db.get_state("adult_lock.hash")) and bool(db.get_state("adult_lock.salt"))


def set_password(plain: str, security_qa: Optional[List[Dict[str, str]]] = None) -> None:
    """Configure a new password and optional 3 security questions."""
    plain = plain.strip()
    if len(plain) < 4:
        raise ValueError("Password must be at least 4 characters long.")

    salt = secrets.token_bytes(SALT_LEN)
    pwd_hash = _hash_secret(plain, salt)

    db.set_state("adult_lock.salt", salt.hex())
    db.set_state("adult_lock.hash", pwd_hash)

    if security_qa:
        if len(security_qa) < 3:
            raise ValueError("Please provide all 3 security questions and answers.")
        questions_payload = []
        for item in security_qa[:3]:
            q = str(item.get("question", "")).strip()
            a = str(item.get("answer", "")).strip()
            if not q or not a:
                raise ValueError("All 3 security questions must have a non-empty answer.")
            q_salt = secrets.token_bytes(SALT_LEN)
            q_hash = _hash_secret(a, q_salt)
            questions_payload.append({
                "question": q,
                "salt": q_salt.hex(),
                "hash": q_hash,
            })
        db.set_state("adult_lock.questions", json.dumps(questions_payload))


def verify_password(plain: str) -> bool:
    stored_hash = db.get_state("adult_lock.hash")
    stored_salt_hex = db.get_state("adult_lock.salt")
    if not stored_hash or not stored_salt_hex:
        return False
    try:
        salt = bytes.fromhex(stored_salt_hex)
        candidate = _hash_secret(plain, salt)
        return secrets.compare_digest(candidate, stored_hash)
    except Exception:
        return False


def change_password(current_plain: str, new_plain: str) -> bool:
    if not verify_password(current_plain):
        raise ValueError("Current password does not match.")
    set_password(new_plain)
    return True


def get_security_questions() -> List[str]:
    """Return the 3 saved question prompts for recovery (never reveals answers or salts)."""
    raw = db.get_state("adult_lock.questions", "[]")
    try:
        data = json.loads(raw)
        return [item["question"] for item in data if isinstance(item, dict) and "question" in item]
    except Exception:
        return []


def verify_security_answers(answers: List[str]) -> bool:
    """Verify 3 submitted answers against the stored salted hashes."""
    raw = db.get_state("adult_lock.questions", "[]")
    try:
        data = json.loads(raw)
    except Exception:
        return False
    if not data or len(data) != 3 or len(answers) != 3:
        return False

    for item, ans in zip(data, answers):
        salt = bytes.fromhex(item["salt"])
        expected = item["hash"]
        candidate = _hash_secret(ans, salt)
        if not secrets.compare_digest(candidate, expected):
            return False
    return True


def reset_password_with_answers(answers: List[str], new_plain: str) -> bool:
    if not verify_security_answers(answers):
        raise ValueError("One or more security answers are incorrect.")
    set_password(new_plain)
    return True


def get_auto_lock_on_restart() -> bool:
    return db.get_state("adult_lock.auto_lock_restart", "1") == "1"


def set_auto_lock_on_restart(enabled: bool) -> None:
    db.set_state("adult_lock.auto_lock_restart", "1" if enabled else "0")


def is_adult_unlocked() -> bool:
    global _session_unlocked
    if not is_password_configured():
        # If no password has ever been configured, respect the explicit user toggle state or allow_mature preference
        return db.get_state("adult_lock.unlocked", "0") == "1" or db.get_state("preference:allow_mature", "0") == "1"
    return _session_unlocked


def unlock(plain: str) -> bool:
    global _session_unlocked
    if not verify_password(plain):
        return False
    _session_unlocked = True
    db.set_state("adult_lock.unlocked", "1")
    return True


def lock() -> None:
    global _session_unlocked
    _session_unlocked = False
    db.set_state("adult_lock.unlocked", "0")


def initialize_session() -> None:
    """Called on application startup to enforce auto-lock on restart if enabled."""
    global _session_unlocked
    if is_password_configured() and get_auto_lock_on_restart():
        _session_unlocked = False
        db.set_state("adult_lock.unlocked", "0")
    else:
        _session_unlocked = db.get_state("adult_lock.unlocked", "0") == "1"
