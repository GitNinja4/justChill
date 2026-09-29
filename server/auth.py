import asyncio
import hashlib
import hmac
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from fastapi import HTTPException, Request

from server.config import (
    LOGIN_MAX_FAILURES,
    LOGIN_WINDOW_SECONDS,
    PASSWORD_ROUNDS,
    PEOPLE,
    SESSION_COOKIE,
    VALID_PEOPLE,
)
from server.db import database


password_hasher = PasswordHasher()
login_failures: dict[str, list[float]] = {}
login_rate_lock = asyncio.Lock()


async def enforce_login_rate_limit(source: str):
    now = time.monotonic()
    async with login_rate_lock:
        attempts = [timestamp for timestamp in login_failures.get(source, []) if now - timestamp < LOGIN_WINDOW_SECONDS]
        login_failures[source] = attempts
        if len(attempts) >= LOGIN_MAX_FAILURES:
            retry_after = max(1, int(LOGIN_WINDOW_SECONDS - (now - attempts[0])))
            raise HTTPException(
                status_code=429,
                detail="Too many sign-in attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )


async def record_login_failure(source: str):
    now = time.monotonic()
    async with login_rate_lock:
        attempts = [timestamp for timestamp in login_failures.get(source, []) if now - timestamp < LOGIN_WINDOW_SECONDS]
        attempts.append(now)
        login_failures[source] = attempts


async def clear_login_failures(source: str):
    async with login_rate_lock:
        login_failures.pop(source, None)


def hash_phrase(phrase: str, salt: bytes | None = None):
    if salt is None:
        return "", password_hasher.hash(phrase.strip().casefold())
    salt = salt or secrets.token_bytes(16)
    phrase_hash = hashlib.pbkdf2_hmac(
        "sha256", phrase.strip().casefold().encode("utf-8"), salt, PASSWORD_ROUNDS
    )
    return salt.hex(), phrase_hash.hex()


def phrase_matches(phrase: str, salt: str, phrase_hash: str):
    if phrase_hash.startswith("$argon2"):
        try:
            password_hasher.verify(phrase_hash, phrase.strip().casefold())
            return True
        except (VerifyMismatchError, VerificationError):
            return False
    _, candidate_hash = hash_phrase(phrase, bytes.fromhex(salt))
    return hmac.compare_digest(candidate_hash, phrase_hash)


def needs_hash_upgrade(phrase_hash: str):
    return not phrase_hash.startswith("$argon2")


def login_source(request: Request):
    return request.client.host if request.client else "unknown"


def session_person(token: str | None):
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with database() as connection:
        row = connection.execute(
            "SELECT person, expires_at FROM sessions WHERE token_hash = ?", (token_hash,)
        ).fetchone()
        if row and row["expires_at"] <= int(time.time()):
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
            return None
    return row["person"] if row else None


def authenticated_person(request: Request):
    person = session_person(request.cookies.get(SESSION_COOKIE))
    if not person:
        raise HTTPException(status_code=401, detail="Sign in to open your little corner.")
    return person


def require_owner(request: Request, person: str):
    validate_person(person)
    signed_in_person = authenticated_person(request)
    if signed_in_person != person:
        raise HTTPException(status_code=403, detail="That plan belongs to the other person.")


def validate_person(person: str):
    if person not in VALID_PEOPLE:
        raise HTTPException(status_code=404, detail="That person isn't on this little map.")


def profile_name(connection, person: str):
    row = connection.execute(
        "SELECT display_name FROM profiles WHERE person = ?", (person,)
    ).fetchone()
    return row["display_name"] if row else PEOPLE[person]
