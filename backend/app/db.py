from __future__ import annotations

import os
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.server_api import ServerApi


BASE_DIR = Path(__file__).resolve().parent
# Load backend/.env once during application startup. Environment variables still take precedence.
load_dotenv(BASE_DIR.parent / ".env")
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "deep_caption")

_client: MongoClient | None = None


def get_collection() -> Collection:
    """Return the caption collection, using configuration from environment variables."""
    global _client

    if not MONGODB_URI:
        raise RuntimeError(
            "MONGODB_URI is not configured. Add it to your environment before starting the API."
        )

    if _client is None:
        _client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            server_api=ServerApi("1"),
        )

    return _client[MONGODB_DATABASE]["captions"]


def get_database():
    return get_collection().database


def init_db() -> None:
    """Verify MongoDB access and create the index used by the history endpoint."""
    collection = get_collection()
    collection.database.client.admin.command("ping")
    collection.create_index([("created_at", DESCENDING)])
    database = collection.database
    database["users"].create_index("email", unique=True)
    database["activities"].create_index([("created_at", DESCENDING)])
    database["feedback"].create_index([("created_at", DESCENDING)])
    database["sessions"].create_index("token", unique=True)


def _serialize_caption(document: dict[str, Any]) -> dict[str, Any]:
    document["id"] = str(document.pop("_id"))
    document.setdefault("descriptions", {
        "short": document.get("caption", ""),
        "detailed": document.get("caption", ""),
        "visually_impaired": document.get("caption", ""),
        "social_media": document.get("caption", ""),
        "seo": document.get("caption", ""),
    })
    document.setdefault("objects", [])
    document.setdefault("ocr_text", "")
    document.setdefault("dominant_colors", [])
    document.setdefault("aspect_ratio", "1:1")
    document.setdefault("orientation", "Landscape" if document.get("width", 0) >= document.get("height", 0) else "Portrait")
    document.setdefault("scene_category", "General Scene")
    document.setdefault("timestamp", "")
    document.setdefault("file_size", "")
    document.setdefault("megapixels", "")
    document.setdefault("image_format", "")
    return document


def save_caption(
    *,
    filename: str,
    content_type: str,
    width: int,
    height: int,
    caption: str,
    model_used: str,
    stored_path: str,
    descriptions: dict[str, str] | None = None,
    objects: list[dict[str, Any]] | None = None,
    ocr_text: str = "",
    dominant_colors: list[dict[str, Any]] | None = None,
    aspect_ratio: str = "1:1",
    orientation: str = "Landscape",
    scene_category: str = "General Scene",
    timestamp: str = "",
    file_size: str = "",
    megapixels: str = "",
    image_format: str = "",
    user: dict[str, Any] | None = None,
) -> str:
    descriptions_data = descriptions or {
        "short": caption,
        "detailed": caption,
        "visually_impaired": caption,
        "social_media": caption,
        "seo": caption,
    }
    result = get_collection().insert_one(
        {
            "filename": filename,
            "content_type": content_type,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "orientation": orientation,
            "scene_category": scene_category,
            "caption": caption,
            "descriptions": descriptions_data,
            "objects": objects or [],
            "ocr_text": ocr_text,
            "dominant_colors": dominant_colors or [],
            "model_used": model_used,
            "stored_path": stored_path,
            "timestamp": timestamp,
            "file_size": file_size,
            "megapixels": megapixels,
            "image_format": image_format,
            "user_id": str(user["_id"]) if user else None,
            "user_name": user["full_name"] if user else "Guest",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if user:
        log_activity("Generated an image analysis", user, filename)
    return str(result.inserted_id)


def get_caption_by_id(caption_id: str) -> dict[str, Any] | None:
    try:
        object_id = ObjectId(caption_id)
    except Exception:
        return None
    document = get_collection().find_one({"_id": object_id})
    if document is None:
        return None
    return _serialize_caption(document)


def list_captions(limit: int = 12) -> list[dict[str, Any]]:
    documents = get_collection().find().sort("created_at", DESCENDING).limit(limit)
    return [_serialize_caption(document) for document in documents]


def delete_caption(caption_id: str) -> bool:
    try:
        object_id = ObjectId(caption_id)
    except Exception:
        return False

    document = get_collection().find_one_and_delete({"_id": object_id})
    if document is None:
        return False

    stored_path = document["stored_path"]
    image_path = (BASE_DIR / stored_path.lstrip("/")).resolve()
    if image_path.exists():
        image_path.unlink()

    return True


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_text, digest_text = stored_hash.split("$", 1)
        expected = _password_hash(password, base64.b64decode(salt_text))
        return hmac.compare_digest(expected, stored_hash)
    except Exception:
        return False


def _serialize_user(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "full_name": document["full_name"],
        "email": document["email"],
        "created_at": document["created_at"],
    }


def log_activity(action: str, user: dict[str, Any] | None = None, details: str = "") -> None:
    get_database()["activities"].insert_one(
        {
            "action": action,
            "user_id": str(user["_id"]) if user else None,
            "user_name": user["full_name"] if user else "Administrator",
            "user_email": user["email"] if user else "admin",
            "details": details,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def register_user(full_name: str, email: str, password: str) -> dict[str, Any] | None:
    email = email.strip().lower()
    user = {
        "full_name": full_name.strip(),
        "email": email,
        "password_hash": _password_hash(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        result = get_database()["users"].insert_one(user)
    except Exception:
        return None
    user["_id"] = result.inserted_id
    log_activity("Registered an account", user)
    return user


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    user = get_database()["users"].find_one({"email": email.strip().lower()})
    if not user or not _verify_password(password, user["password_hash"]):
        return None
    log_activity("Signed in", user)
    return user


def create_session(user: dict[str, Any] | None, role: str) -> str:
    token = secrets.token_urlsafe(32)
    get_database()["sessions"].insert_one(
        {"token": token, "user_id": str(user["_id"]) if user else None, "role": role, "created_at": datetime.now(timezone.utc).isoformat()}
    )
    return token


def get_session(token: str) -> dict[str, Any] | None:
    return get_database()["sessions"].find_one({"token": token})


def list_users(limit: int = 100) -> list[dict[str, Any]]:
    return [_serialize_user(user) for user in get_database()["users"].find().sort("created_at", DESCENDING).limit(limit)]


def list_activities(limit: int = 30) -> list[dict[str, Any]]:
    return [
        {"id": str(item["_id"]), **{key: value for key, value in item.items() if key != "_id"}}
        for item in get_database()["activities"].find().sort("created_at", DESCENDING).limit(limit)
    ]


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    try:
        return get_database()["users"].find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None


def save_feedback(*, user: dict[str, Any], subject: str, message: str) -> str:
    result = get_database()["feedback"].insert_one(
        {
            "user_id": str(user["_id"]),
            "user_name": user["full_name"],
            "user_email": user["email"],
            "subject": subject.strip(),
            "message": message.strip(),
            "status": "new",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    log_activity("Submitted feedback", user, subject.strip())
    return str(result.inserted_id)


def list_feedback(limit: int = 100) -> list[dict[str, Any]]:
    return [
        {"id": str(item["_id"]), **{key: value for key, value in item.items() if key != "_id"}}
        for item in get_database()["feedback"].find().sort("created_at", DESCENDING).limit(limit)
    ]


def update_feedback_status(feedback_id: str, status: str) -> bool:
    try:
        result = get_database()["feedback"].update_one({"_id": ObjectId(feedback_id)}, {"$set": {"status": status}})
        return result.matched_count == 1
    except Exception:
        return False


def delete_feedback(feedback_id: str) -> bool:
    try:
        return get_database()["feedback"].delete_one({"_id": ObjectId(feedback_id)}).deleted_count == 1
    except Exception:
        return False
