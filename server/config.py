import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "relationship.sqlite3")))
DATABASE_URL = os.getenv("DATABASE_URL")
VALID_PEOPLE = {"aditya", "tishu"}
PEOPLE = {"aditya": "Aditya", "tishu": "Tishu"}
DEFAULT_LOCATIONS = {
    "aditya": {"city": "Delhi", "time_zone": "Asia/Kolkata"},
    "tishu": {"city": "Sydney", "time_zone": "Australia/Sydney"},
}
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
CALL_SIGNAL_ACTIONS = {
    "invite", "accept", "decline", "busy", "cancel", "offer", "answer", "ice", "connected", "hangup"
}
MAX_CALL_SIGNAL_BYTES = 128 * 1024
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILURES = 8
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
MAX_CHAT_ATTACHMENTS = 4
ALLOWED_ATTACHMENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
