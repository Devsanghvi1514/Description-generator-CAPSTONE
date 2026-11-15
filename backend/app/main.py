from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from .db import (authenticate_user, create_session, delete_caption, delete_feedback, get_caption_by_id, get_session, get_user_by_id, init_db,
                 list_activities, list_captions, list_feedback, list_users, register_user, save_caption, save_feedback,
                 update_feedback_status)
from .schemas import (ActivityItem, AskQuestionRequest, AskQuestionResponse, AuthResponse, AuthUser, CaptionHistoryResponse,
                      CaptionResponse, ChatRequest, ChatResponse, Descriptions, DetectedObject, DominantColor, FeedbackItem, FeedbackRequest, FeedbackStatusUpdate, HealthResponse, LoginRequest, RegisterRequest)
from .services.caption_service import answer_image_question, chat_with_assistant, generate_full_analysis, warmup_vision_model



BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Image Description Generator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    import threading
    threading.Thread(target=warmup_vision_model, daemon=True).start()


@app.get("/api/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


def require_admin(x_session_token: str | None = Header(default=None)) -> None:
    if not x_session_token or not (session := get_session(x_session_token)) or session.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Administrator access is required.")


def require_user(x_session_token: str | None = Header(default=None)) -> dict:
    if not x_session_token or not (session := get_session(x_session_token)) or session.get("role") != "user":
        raise HTTPException(status_code=401, detail="Please sign in to submit feedback.")
    user = get_user_by_id(session["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="Your session is no longer valid.")
    return user


@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(request: RegisterRequest) -> AuthResponse:
    if len(request.password) < 6 or not request.full_name.strip() or "@" not in request.email:
        raise HTTPException(status_code=400, detail="Enter a valid name, email, and password of at least 6 characters.")
    user = register_user(request.full_name, request.email, request.password)
    if not user:
        raise HTTPException(status_code=409, detail="An account already exists with that email address.")
    return AuthResponse(token=create_session(user, "user"), user=AuthUser(**{"id": str(user["_id"]), **user}))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    user = authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return AuthResponse(token=create_session(user, "user"), user=AuthUser(**{"id": str(user["_id"]), **user}))


@app.post("/api/auth/admin/login", response_model=AuthResponse)
def admin_login(request: LoginRequest) -> AuthResponse:
    if request.email != "admin" or request.password != "admin123":
        raise HTTPException(status_code=401, detail="Invalid administrator ID or password.")
    admin = {"id": "admin", "full_name": "Administrator", "email": "admin", "created_at": ""}
    return AuthResponse(token=create_session(None, "admin"), user=AuthUser(**admin))


@app.get("/api/admin/users", response_model=list[AuthUser], dependencies=[Depends(require_admin)])
def get_users() -> list[dict]:
    return list_users()


@app.get("/api/admin/activity", response_model=list[ActivityItem], dependencies=[Depends(require_admin)])
def get_activity() -> list[dict]:
    return list_activities()


@app.get("/api/admin/images", response_model=CaptionHistoryResponse, dependencies=[Depends(require_admin)])
def get_admin_images() -> CaptionHistoryResponse:
    return CaptionHistoryResponse(items=list_captions())


@app.get("/api/admin/feedback", response_model=list[FeedbackItem], dependencies=[Depends(require_admin)])
def get_feedback() -> list[dict]:
    return list_feedback()


@app.patch("/api/admin/feedback/{feedback_id}", response_model=FeedbackItem, dependencies=[Depends(require_admin)])
def set_feedback_status(feedback_id: str, payload: FeedbackStatusUpdate) -> dict:
    if not update_feedback_status(feedback_id, payload.status):
        raise HTTPException(status_code=404, detail="Feedback item not found.")
    item = next((feedback for feedback in list_feedback() if feedback["id"] == feedback_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Feedback item not found.")
    return item


@app.delete("/api/admin/feedback/{feedback_id}", dependencies=[Depends(require_admin)])
def remove_feedback(feedback_id: str) -> dict[str, bool]:
    if not delete_feedback(feedback_id):
        raise HTTPException(status_code=404, detail="Feedback item not found.")
    return {"deleted": True}


@app.delete("/api/admin/images/{caption_id}", dependencies=[Depends(require_admin)])
def remove_admin_image(caption_id: str) -> dict[str, bool]:
    deleted = delete_caption(caption_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Image record not found.")
    return {"deleted": True}


@app.post("/api/caption", response_model=CaptionResponse)
def create_caption(image: UploadFile = File(...), x_session_token: str | None = Header(default=None)) -> CaptionResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")

    suffix = Path(image.filename or "upload").suffix or ".png"
    stored_name = f"{uuid4().hex}{suffix}"
    stored_path = UPLOAD_DIR / stored_name

    with stored_path.open("wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    try:
        with Image.open(stored_path) as opened_image:
            width, height = opened_image.size
    except Exception as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded file could not be processed as an image.") from exc

    analysis = generate_full_analysis(stored_path)

    user = None
    if x_session_token and isinstance(x_session_token, str) and (session := get_session(x_session_token)) and session.get("user_id"):
        user = {"_id": session["user_id"], "full_name": "User", "email": ""}
        from .db import get_database
        user = get_database()["users"].find_one({"_id": __import__("bson").ObjectId(session["user_id"])}) or user

    caption_id = save_caption(
        filename=image.filename or stored_name,
        content_type=image.content_type,
        width=analysis.width,
        height=analysis.height,
        aspect_ratio=analysis.aspect_ratio,
        orientation=analysis.orientation,
        scene_category=analysis.scene_category,
        caption=analysis.caption,
        descriptions=analysis.descriptions,
        objects=analysis.objects,
        ocr_text=analysis.ocr_text,
        dominant_colors=analysis.dominant_colors,
        model_used=analysis.model_used,
        stored_path=f"/static/uploads/{stored_name}",
        timestamp=analysis.timestamp,
        file_size=analysis.file_size,
        megapixels=analysis.megapixels,
        image_format=analysis.image_format,
        user=user,
    )

    return CaptionResponse(
        id=caption_id,
        filename=image.filename or stored_name,
        content_type=image.content_type,
        width=analysis.width,
        height=analysis.height,
        aspect_ratio=analysis.aspect_ratio,
        orientation=analysis.orientation,
        scene_category=analysis.scene_category,
        caption=analysis.caption,
        descriptions=Descriptions(**analysis.descriptions),
        objects=[DetectedObject(**obj) for obj in analysis.objects],
        ocr_text=analysis.ocr_text,
        dominant_colors=[DominantColor(**color) for color in analysis.dominant_colors],
        model_used=analysis.model_used,
        stored_path=f"/static/uploads/{stored_name}",
        timestamp=analysis.timestamp,
        file_size=analysis.file_size,
        megapixels=analysis.megapixels,
        image_format=analysis.image_format,
    )


@app.post("/api/caption/{caption_id}/ask", response_model=AskQuestionResponse)
def ask_question(caption_id: str, request: AskQuestionRequest) -> AskQuestionResponse:
    record = get_caption_by_id(caption_id)
    if not record:
        raise HTTPException(status_code=404, detail="Image record not found.")

    stored_path = record.get("stored_path", "")
    local_image_path = (BASE_DIR / stored_path.lstrip("/\\")).resolve()
    if not local_image_path.exists():
        local_image_path = (UPLOAD_DIR / Path(stored_path).name).resolve()
    if not local_image_path.exists():
        local_image_path = (BASE_DIR.parent / stored_path.lstrip("/\\")).resolve()

    if not local_image_path.exists():
        raise HTTPException(status_code=404, detail="Stored image file could not be found.")

    answer = answer_image_question(local_image_path, request.question, record=record)
    return AskQuestionResponse(question=request.question, answer=answer)


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    local_image_path = None
    record = None

    if request.caption_id:
        record = get_caption_by_id(request.caption_id)
        if record:
            stored_path = record.get("stored_path", "")
            local_image_path = (BASE_DIR / stored_path.lstrip("/\\")).resolve()
            if not local_image_path.exists():
                local_image_path = (UPLOAD_DIR / Path(stored_path).name).resolve()
            if not local_image_path.exists():
                local_image_path = (BASE_DIR.parent / stored_path.lstrip("/\\")).resolve()

    reply, suggestions = chat_with_assistant(
        message=request.message,
        image_path=local_image_path if (local_image_path and local_image_path.exists()) else None,
        record=record,
    )
    return ChatResponse(message=request.message, reply=reply, suggested_prompts=suggestions)


@app.post("/api/feedback", response_model=FeedbackItem, status_code=201)
def create_feedback(request: FeedbackRequest, user: dict = Depends(require_user)) -> dict:
    feedback_id = save_feedback(user=user, subject=request.subject, message=request.message)
    return next(feedback for feedback in list_feedback() if feedback["id"] == feedback_id)


@app.get("/api/captions", response_model=CaptionHistoryResponse)
def get_caption_history() -> CaptionHistoryResponse:
    items = list_captions()
    return CaptionHistoryResponse(items=items)


@app.delete("/api/captions/{caption_id}")
def remove_caption_history(caption_id: str) -> dict[str, bool]:
    deleted = delete_caption(caption_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Caption history item not found.")
    return {"deleted": True}
