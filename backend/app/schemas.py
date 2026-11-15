from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DetectedObject(BaseModel):
    name: str
    emoji: str = "🔹"
    count: int = 1


class DominantColor(BaseModel):
    hex: str
    name: str
    percentage: int
    rgb: list[int] = Field(default_factory=list)


class Descriptions(BaseModel):
    short: str = ""
    detailed: str = ""
    visually_impaired: str = ""
    social_media: str = ""
    seo: str = ""


class CaptionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    filename: str
    content_type: str
    width: int
    height: int
    aspect_ratio: str = "1:1"
    orientation: str = "Landscape"
    scene_category: str = "General Scene"
    caption: str
    descriptions: Descriptions = Field(default_factory=Descriptions)
    objects: list[DetectedObject] = Field(default_factory=list)
    ocr_text: str = ""
    dominant_colors: list[DominantColor] = Field(default_factory=list)
    model_used: str
    stored_path: str
    timestamp: str = ""
    file_size: str = ""
    megapixels: str = ""
    image_format: str = ""
    created_at: str = ""


class CaptionHistoryItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    filename: str
    content_type: str
    width: int
    height: int
    aspect_ratio: str = "1:1"
    orientation: str = "Landscape"
    scene_category: str = "General Scene"
    caption: str
    descriptions: Descriptions = Field(default_factory=Descriptions)
    objects: list[DetectedObject] = Field(default_factory=list)
    ocr_text: str = ""
    dominant_colors: list[DominantColor] = Field(default_factory=list)
    model_used: str
    stored_path: str
    created_at: str
    timestamp: str = ""
    file_size: str = ""
    megapixels: str = ""
    image_format: str = ""


class CaptionHistoryResponse(BaseModel):
    items: list[CaptionHistoryItem]


class AskQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AskQuestionResponse(BaseModel):
    question: str
    answer: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    caption_id: str | None = None


class ChatResponse(BaseModel):
    message: str
    reply: str
    suggested_prompts: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthUser(BaseModel):
    id: str
    full_name: str
    email: str
    created_at: str


class AuthResponse(BaseModel):
    token: str
    user: AuthUser


class ActivityItem(BaseModel):
    id: str
    action: str
    user_id: str | None = None
    user_name: str
    user_email: str
    details: str = ""
    created_at: str


class FeedbackRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=120)
    message: str = Field(min_length=10, max_length=2000)


class FeedbackItem(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_email: str
    subject: str
    message: str
    status: Literal["new", "reviewed", "resolved"]
    created_at: str


class FeedbackStatusUpdate(BaseModel):
    status: Literal["new", "reviewed", "resolved"]
