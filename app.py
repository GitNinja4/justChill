import asyncio
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "relationship.sqlite3")))
VALID_PEOPLE = {"aditya", "tishu"}
PEOPLE = {"aditya": "Aditya", "tishu": "Tishu"}
SESSION_COOKIE = "aditya_tishu_session"
SESSION_SECONDS = 60 * 60 * 24 * 30
PASSWORD_ROUNDS = 310_000
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if origin.strip()
]


def connect_db():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def database():
    connection = connect_db()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_db():
    with database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sign_in_phrases (
                person TEXT PRIMARY KEY,
                salt TEXT NOT NULL,
                phrase_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                person TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            );
            """
        )
        for person, phrase in (("aditya", "I'm Aditya"), ("tishu", "I'm Tishu")):
            exists = connection.execute(
                "SELECT 1 FROM sign_in_phrases WHERE person = ?", (person,)
            ).fetchone()
            if not exists:
                salt, phrase_hash = hash_phrase(phrase)
                connection.execute(
                    "INSERT INTO sign_in_phrases (person, salt, phrase_hash) VALUES (?, ?, ?)",
                    (person, salt, phrase_hash),
                )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_db()
    yield


app = FastAPI(title="Aditya & Tishu", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


class ChatMessage(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class LoginRequest(BaseModel):
    sentence: str = Field(min_length=1, max_length=200)


class ChangeSentenceRequest(BaseModel):
    current_sentence: str = Field(min_length=1, max_length=200)
    new_sentence: str = Field(min_length=8, max_length=200)


def hash_phrase(phrase: str, salt: bytes | None = None):
    salt = salt or secrets.token_bytes(16)
    phrase_hash = hashlib.pbkdf2_hmac(
        "sha256", phrase.strip().casefold().encode("utf-8"), salt, PASSWORD_ROUNDS
    )
    return salt.hex(), phrase_hash.hex()


def phrase_matches(phrase: str, salt: str, phrase_hash: str):
    _, candidate_hash = hash_phrase(phrase, bytes.fromhex(salt))
    return hmac.compare_digest(candidate_hash, phrase_hash)


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


def serialize_message(row):
    created_at = datetime.fromisoformat(row["created_at"])
    return {
        "id": row["id"],
        "from": row["sender"],
        "text": row["text"],
        "ts": int(created_at.timestamp() * 1000),
    }


@app.get("/")
async def home():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/config")
async def get_config():
    numbers = {
        "aditya": os.getenv("ADITYA_WHATSAPP_NUMBER", "919334823399"),
        "tishu": os.getenv("TISHU_WHATSAPP_NUMBER", ""),
    }
    return {
        "whatsapp_numbers": {
            person: "".join(character for character in number if character.isdigit())
            for person, number in numbers.items()
        }
    }


@app.get("/api/auth/session")
async def get_auth_session(request: Request):
    person = authenticated_person(request)
    return {"person": person, "name": PEOPLE[person]}


@app.post("/api/auth/login")
async def login(payload: LoginRequest, request: Request, response: Response):
    phrase = payload.sentence.strip()
    if not phrase:
        raise HTTPException(status_code=401, detail="That sentence didn't sound quite right.")
    with database() as connection:
        rows = connection.execute(
            "SELECT person, salt, phrase_hash FROM sign_in_phrases"
        ).fetchall()
    matches = [
        row["person"]
        for row in rows
        if phrase_matches(phrase, row["salt"], row["phrase_hash"])
    ]
    if len(matches) != 1:
        raise HTTPException(status_code=401, detail="That sentence didn't sound quite right.")

    person = matches[0]
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with database() as connection:
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))
        connection.execute(
            "INSERT INTO sessions (token_hash, person, expires_at) VALUES (?, ?, ?)",
            (token_hash, person, int(time.time()) + SESSION_SECONDS),
        )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )
    return {"person": person, "name": PEOPLE[person]}


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with database() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict")
    return {"ok": True}


@app.put("/api/auth/login-sentence")
async def change_login_sentence(payload: ChangeSentenceRequest, request: Request):
    person = authenticated_person(request)
    current_phrase = payload.current_sentence.strip()
    new_phrase = payload.new_sentence.strip()
    with database() as connection:
        rows = connection.execute(
            "SELECT person, salt, phrase_hash FROM sign_in_phrases"
        ).fetchall()
        own_row = next(row for row in rows if row["person"] == person)
        if not phrase_matches(current_phrase, own_row["salt"], own_row["phrase_hash"]):
            raise HTTPException(status_code=400, detail="The current sentence doesn't match.")
        if phrase_matches(new_phrase, own_row["salt"], own_row["phrase_hash"]):
            raise HTTPException(status_code=400, detail="Pick a different sentence this time.")
        for row in rows:
            if row["person"] != person and phrase_matches(new_phrase, row["salt"], row["phrase_hash"]):
                raise HTTPException(status_code=400, detail="That sentence is already theirs. Choose another.")
        salt, phrase_hash = hash_phrase(new_phrase)
        connection.execute(
            "UPDATE sign_in_phrases SET salt = ?, phrase_hash = ? WHERE person = ?",
            (salt, phrase_hash, person),
        )
        token = request.cookies.get(SESSION_COOKIE, "")
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        connection.execute(
            "DELETE FROM sessions WHERE person = ? AND token_hash != ?", (person, token_hash)
        )
    return {"ok": True}


@app.get("/api/messages")
async def get_messages(request: Request):
    authenticated_person(request)
    with database() as connection:
        rows = connection.execute(
            "SELECT id, sender, text, created_at FROM messages ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return [serialize_message(row) for row in reversed(rows)]


connected_clients: set[WebSocket] = set()
broadcast_lock = asyncio.Lock()


async def broadcast(message: dict):
    async with broadcast_lock:
        clients = list(connected_clients)
        results = await asyncio.gather(
            *(client.send_json(message) for client in clients), return_exceptions=True
        )
        for client, result in zip(clients, results):
            if isinstance(result, Exception):
                connected_clients.discard(client)


@app.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket):
    await websocket.accept()
    person = session_person(websocket.cookies.get(SESSION_COOKIE))
    if not person:
        await websocket.close(code=4401, reason="Sign in first.")
        return
    connected_clients.add(websocket)
    with database() as connection:
        rows = connection.execute(
            "SELECT id, sender, text, created_at FROM messages ORDER BY id DESC LIMIT 100"
        ).fetchall()
    await websocket.send_json({"type": "history", "messages": [serialize_message(row) for row in reversed(rows)]})
    try:
        while True:
            payload = await websocket.receive_json()
            if session_person(websocket.cookies.get(SESSION_COOKIE)) != person:
                await websocket.close(code=4401, reason="Your sign-in has changed.")
                break
            try:
                message = ChatMessage.model_validate(payload)
            except Exception:
                await websocket.send_json({"type": "error", "message": "That message needs a name and a little less than 300 characters."})
                continue
            text = message.text.strip()
            if not text:
                continue
            created_at = datetime.now(timezone.utc).isoformat()
            with database() as connection:
                cursor = connection.execute(
                    "INSERT INTO messages (sender, text, created_at) VALUES (?, ?, ?)",
                    (PEOPLE[person], text, created_at),
                )
                row = connection.execute(
                    "SELECT id, sender, text, created_at FROM messages WHERE id = ?", (cursor.lastrowid,)
                ).fetchone()
            await broadcast({"type": "message", "message": serialize_message(row)})
    except WebSocketDisconnect:
        pass
    finally:
        connected_clients.discard(websocket)