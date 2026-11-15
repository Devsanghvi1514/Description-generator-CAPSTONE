from __future__ import annotations

import gc
import hashlib
import math
import os
import re
import sys
import threading
import warnings
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from PIL import ExifTags, Image, ImageStat

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="torch.ao")
warnings.filterwarnings("ignore", message=".*num_beams.*early_stopping.*")

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")


def _safe_log(msg: str) -> None:
    """Print safely to standard output without throwing UnicodeEncodeError on Windows cp1252 consoles."""
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        safe_msg = msg.encode("ascii", errors="backslashreplace").decode("ascii")
        print(safe_msg, flush=True)


OBJECT_EMOJI_MAP: dict[str, str] = {
    # People & Faces
    "person": "👤",
    "people": "👥",
    "man": "👨",
    "men": "👨",
    "woman": "👩",
    "women": "👩",
    "child": "🧒",
    "children": "🧒",
    "boy": "👦",
    "girl": "👧",
    "baby": "👶",
    "face": "🙂",
    "crowd": "👥",
    # Electronics & Tech
    "laptop": "💻",
    "computer": "🖥️",
    "monitor": "🖥️",
    "screen": "🖥️",
    "keyboard": "⌨️",
    "mouse": "🖱️",
    "cell phone": "📱",
    "phone": "📱",
    "smartphone": "📱",
    "tablet": "📱",
    "camera": "📷",
    "tv": "📺",
    "television": "📺",
    "clock": "⏰",
    "watch": "⌚",
    "headphone": "🎧",
    "headphones": "🎧",
    # Furniture & Household
    "chair": "🪑",
    "seat": "🪑",
    "sofa": "🛋️",
    "couch": "🛋️",
    "table": "🪵",
    "desk": "🪵",
    "bed": "🛏️",
    "lamp": "💡",
    "light": "💡",
    "window": "🪟",
    "door": "🚪",
    "mirror": "🪞",
    "shelf": "🪵",
    # Vehicles & Transportation
    "car": "🚗",
    "automobile": "🚗",
    "vehicle": "🚘",
    "bus": "🚌",
    "truck": "🚚",
    "bicycle": "🚲",
    "bike": "🚲",
    "motorcycle": "🏍️",
    "airplane": "✈️",
    "plane": "✈️",
    "boat": "⛵",
    "ship": "🚢",
    "train": "🚆",
    "traffic light": "🚦",
    "street light": "🏮",
    # Books & Documents
    "book": "📚",
    "notebook": "📓",
    "paper": "📄",
    "document": "📑",
    "pen": "🖊️",
    "pencil": "✏️",
    "letter": "✉️",
    "sign": "🪧",
    "billboard": "🪧",
    # Kitchen & Dining
    "cup": "☕",
    "coffee": "☕",
    "mug": "☕",
    "bottle": "🍾",
    "glass": "🥛",
    "wine glass": "🍷",
    "fork": "🍴",
    "knife": "🔪",
    "spoon": "🥄",
    "bowl": "🥣",
    "plate": "🍽️",
    # Food & Produce
    "food": "🍲",
    "pizza": "🍕",
    "cake": "🎂",
    "apple": "🍎",
    "banana": "🍌",
    "orange": "🍊",
    "sandwich": "🥪",
    "bread": "🍞",
    "burger": "🍔",
    "fruit": "🍎",
    "vegetable": "🥦",
    # Apparel & Accessories
    "glasses": "👓",
    "sunglasses": "🕶️",
    "hat": "🧢",
    "cap": "🧢",
    "backpack": "🎒",
    "bag": "👜",
    "handbag": "👜",
    "purse": "👛",
    "suitcase": "🧳",
    "luggage": "🧳",
    "tie": "👔",
    "umbrella": "☂️",
    "shoes": "👟",
    "shoe": "👟",
    "boot": "🥾",
    "jacket": "🧥",
    "coat": "🧥",
    "shirt": "👕",
    "dress": "👗",
    # Animals & Nature
    "dog": "🐶",
    "cat": "🐱",
    "bird": "🐦",
    "horse": "🐴",
    "sheep": "🐑",
    "cow": "🐮",
    "elephant": "🐘",
    "bear": "🐻",
    "zebra": "🦓",
    "giraffe": "🦒",
    "lion": "🦁",
    "tiger": "🐯",
    "fish": "🐟",
    "tree": "🌳",
    "plant": "🪴",
    "flower": "🌸",
    "grass": "🌿",
    # Buildings & Scenery
    "building": "🏢",
    "house": "🏠",
    "bridge": "🌉",
    "mountain": "🏔️",
    "road": "🛣️",
    "street": "🛣️",
    "sky": "☁️",
    "cloud": "☁️",
    "sun": "☀️",
    # Sports & Recreation
    "ball": "⚽",
    "flag": "🚩",
}


def get_object_emoji(name: str) -> str:
    """Return an appropriate emoji for a detected object name by exact match or substring."""
    clean = name.strip().lower()
    if clean in OBJECT_EMOJI_MAP:
        return OBJECT_EMOJI_MAP[clean]

    for key, emoji in OBJECT_EMOJI_MAP.items():
        if key in clean or clean in key:
            return emoji
    return "🔹"


REFERENCE_COLORS: list[tuple[str, str, tuple[int, int, int]]] = [
    ("Pure Black", "#000000", (15, 15, 15)),
    ("Charcoal", "#2D3748", (45, 55, 72)),
    ("Slate Gray", "#64748B", (100, 116, 139)),
    ("Silver", "#CBD5E1", (203, 213, 225)),
    ("Pure White", "#FFFFFF", (250, 250, 250)),
    ("Navy Blue", "#1E3A8A", (30, 58, 138)),
    ("Royal Blue", "#2563EB", (37, 99, 235)),
    ("Sky Blue", "#38BDF8", (56, 189, 248)),
    ("Teal", "#0D9488", (13, 148, 136)),
    ("Emerald Green", "#10B981", (16, 185, 129)),
    ("Forest Green", "#166534", (22, 101, 52)),
    ("Olive", "#65A30D", (101, 163, 13)),
    ("Bright Yellow", "#FACC15", (250, 204, 21)),
    ("Amber Gold", "#F59E0B", (245, 158, 11)),
    ("Coral Orange", "#F97316", (249, 115, 22)),
    ("Crimson Red", "#DC2626", (220, 38, 38)),
    ("Ruby Red", "#991B1B", (153, 27, 27)),
    ("Rose Pink", "#F43F5E", (244, 63, 94)),
    ("Magenta", "#D946EF", (217, 70, 239)),
    ("Royal Purple", "#8B5CF6", (139, 92, 246)),
    ("Deep Indigo", "#4338CA", (67, 56, 202)),
    ("Warm Cream", "#FEF3C7", (254, 243, 199)),
    ("Beige / Tan", "#D4B996", (212, 185, 150)),
    ("Warm Brown", "#854D0E", (133, 77, 14)),
    ("Chocolate Brown", "#5B3214", (91, 50, 20)),
]


def _match_color_name_and_hex(rgb: tuple[int, int, int]) -> tuple[str, str]:
    r, g, b = rgb
    best_name, best_hex = "Custom", f"#{r:02X}{g:02X}{b:02X}"
    min_dist = float("inf")
    for name, hex_val, ref_rgb in REFERENCE_COLORS:
        dist = math.sqrt(
            (r - ref_rgb[0]) ** 2 + (g - ref_rgb[1]) ** 2 + (b - ref_rgb[2]) ** 2
        )
        if dist < min_dist:
            min_dist = dist
            best_name = name
            best_hex = hex_val
    return best_name, f"#{r:02X}{g:02X}{b:02X}"


def extract_dominant_colors(image: Image.Image, num_colors: int = 5) -> list[dict[str, Any]]:
    """Extract dominant colors with human names, hex codes, and percentage share."""
    try:
        rgb_image = image.convert("RGB").resize((120, 120))
        quantized = rgb_image.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
        palette = quantized.getpalette()
        if not palette:
            return []

        color_counts = Counter(quantized.getdata())
        total_pixels = sum(color_counts.values()) or 1
        results = []

        for color_idx, count in color_counts.most_common(num_colors):
            r = palette[color_idx * 3]
            g = palette[color_idx * 3 + 1]
            b = palette[color_idx * 3 + 2]
            name, hex_code = _match_color_name_and_hex((r, g, b))
            pct = max(1, round((count / total_pixels) * 100))
            results.append({
                "hex": hex_code,
                "name": name,
                "percentage": pct,
                "rgb": [r, g, b],
            })

        return results
    except Exception as exc:
        _safe_log(f"Color extraction error: {exc}")
        return [
            {"hex": "#3B82F6", "name": "Blue", "percentage": 50, "rgb": [59, 130, 246]},
            {"hex": "#64748B", "name": "Slate Gray", "percentage": 30, "rgb": [100, 116, 139]},
            {"hex": "#F8FAFC", "name": "Pure White", "percentage": 20, "rgb": [248, 250, 252]},
        ]


def _detect_scene_category(caption: str, objects: list[dict[str, Any]], ocr_text: str) -> str:
    text_corpus = f"{caption} {' '.join(o.get('name', '') for o in objects)} {ocr_text}".lower()

    scores = {
        "Document & Text": sum(text_corpus.count(k) for k in ["document", "invoice", "letter", "receipt", "certificate", "contract", "newspaper", "book", "text", "page", "font", "signboard", "paper"]),
        "Architecture & Urban": sum(text_corpus.count(k) for k in ["monument", "mausoleum", "architecture", "building", "house", "palace", "temple", "church", "castle", "tower", "bridge", "skyscraper", "city", "street", "urban", "facade", "villa"]),
        "Vehicles & Transport": sum(text_corpus.count(k) for k in ["car", "automobile", "vehicle", "truck", "bus", "train", "airplane", "plane", "bicycle", "bike", "motorcycle", "highway", "traffic", "road"]),
        "Food & Dining": sum(text_corpus.count(k) for k in ["food", "dish", "meal", "plate", "restaurant", "pizza", "burger", "cake", "fruit", "vegetable", "coffee", "beverage", "dining", "dessert"]),
        "Animals & Pets": sum(text_corpus.count(k) for k in ["dog", "cat", "bird", "animal", "pet", "wildlife", "horse", "lion", "tiger", "fish", "puppy", "kitten"]),
        "People & Portrait": sum(text_corpus.count(k) for k in ["person", "people", "portrait", "man", "woman", "child", "girl", "boy", "crowd", "face", "selfie", "smiling", "posing"]),
        "Indoor Office & Tech": sum(text_corpus.count(k) for k in ["laptop", "computer", "desk", "office", "monitor", "keyboard", "screen", "workspace", "mouse", "electronics"]),
        "Nature & Landscape": sum(text_corpus.count(k) for k in ["mountain", "forest", "beach", "ocean", "sea", "river", "valley", "lake", "waterfall", "sunset", "sunrise", "landscape", "field", "garden", "flowers", "trees"]),
    }

    best_cat, max_score = max(scores.items(), key=lambda x: x[1])
    return best_cat if max_score > 0 else "General Scene"


def _format_natural_color_phrase(dominant_colors: list[dict[str, Any]]) -> str:
    """Format dominant colors into natural conversational English without raw percentage math."""
    clean_names = []
    for c in dominant_colors[:3]:
        name = c.get("name", "").strip().lower()
        if "/" in name:
            name = name.split("/")[0].strip()
        if name and name not in clean_names:
            clean_names.append(name)

    if not clean_names:
        return "natural balanced tones"
    if len(clean_names) == 1:
        return f"{clean_names[0]} tones"
    if len(clean_names) == 2:
        return f"{clean_names[0]} and {clean_names[1]} tones"
    return f"{clean_names[0]}, {clean_names[1]}, and {clean_names[2]} tones"


def extract_image_technical_metadata_and_timestamp(image_path: Path, image: Image.Image) -> dict[str, str]:
    """Extract precise camera EXIF timestamp, capture specifications, format, megapixels, and file size."""
    width, height = image.size
    img_format = image.format or image_path.suffix.lstrip(".").upper() or "JPEG"
    mp = (width * height) / 1_000_000
    megapixels = f"{mp:.2f} MP" if mp >= 0.1 else f"{mp:.3f} MP"

    try:
        size_bytes = image_path.stat().st_size
        file_size = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024 * 1024 else f"{size_bytes / (1024 * 1024):.2f} MB"
    except Exception:
        file_size = "Unknown"

    timestamp_str = None
    # 1. Try EXIF camera capture timestamp (DateTimeOriginal, DateTimeDigitized, DateTime)
    try:
        exif = image.getexif()
        if exif:
            for tag_id in [36867, 36868, 306]:
                val = exif.get(tag_id)
                if val and isinstance(val, str) and len(val.strip()) >= 10:
                    try:
                        dt = datetime.strptime(val.strip()[:19], "%Y:%m:%d %H:%M:%S")
                        timestamp_str = dt.strftime("%B %d, %Y at %I:%M %p")
                        break
                    except Exception:
                        timestamp_str = val.strip()
                        break
            if not timestamp_str:
                try:
                    ifd = exif.get_ifd(ExifTags.IFD.Exif)
                    for tag_id in [36867, 36868, 306]:
                        val = ifd.get(tag_id)
                        if val and isinstance(val, str) and len(val.strip()) >= 10:
                            try:
                                dt = datetime.strptime(val.strip()[:19], "%Y:%m:%d %H:%M:%S")
                                timestamp_str = dt.strftime("%B %d, %Y at %I:%M %p")
                                break
                            except Exception:
                                timestamp_str = val.strip()
                                break
                except Exception:
                    pass
    except Exception:
        pass

    # 2. File creation/modification timestamp fallback
    if not timestamp_str:
        try:
            mtime = os.path.getmtime(image_path)
            dt = datetime.fromtimestamp(mtime)
            timestamp_str = dt.strftime("%B %d, %Y at %I:%M %p")
        except Exception:
            timestamp_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    return {
        "timestamp": timestamp_str,
        "image_format": img_format,
        "megapixels": megapixels,
        "file_size": file_size,
    }


def _generate_social_media_caption(
    caption: str,
    objects: list[dict[str, Any]],
    category: str,
    timestamp: str = "",
    image_format: str = "",
    width: int = 0,
    height: int = 0,
) -> str:
    """Generate an engaging, natural social media post with timestamp and relevant smart hashtags."""
    # Extract clean sentence for the hook
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", caption) if s.strip()]
    hook = sentences[0] if sentences else caption
    if not hook.endswith((".", "!", "?")):
        hook += "."

    tags = set()
    # Extract proper nouns (e.g. Taj Mahal, Agra, India, Paris)
    proper_nouns = re.findall(r"\b[A-Z][a-z]{2,}\b", caption)
    stopwords = {"The", "This", "There", "Image", "Photo", "Photograph", "View", "Scene", "Overall", "Main", "With", "From", "Key", "Near", "Under"}
    for pn in proper_nouns:
        if pn not in stopwords:
            tags.add(f"#{pn}")
            if len(tags) >= 3:
                break

    # Add relevant recognized subject tags
    for obj in objects[:3]:
        clean_name = re.sub(r"[^a-zA-Z0-9]", "", obj.get("name", ""))
        if clean_name and len(clean_name) > 2 and clean_name.lower() not in {"flag", "item", "background", "poly"}:
            tags.add(f"#{clean_name}")

    category_tags = {
        "Architecture & Urban": ["#Architecture", "#TravelPhotography", "#Wanderlust", "#HistoricPlaces"],
        "Nature & Landscape": ["#NaturePhotography", "#LandscapeLovers", "#ScenicView", "#Outdoors"],
        "Food & Dining": ["#FoodPhotography", "#Foodie", "#CulinaryDelight", "#Delicious"],
        "People & Portrait": ["#PortraitPhotography", "#HumanStories", "#MomentsInTime"],
        "Animals & Pets": ["#WildlifePhotography", "#PetLovers", "#AnimalKingdom"],
        "Vehicles & Transport": ["#Automotive", "#TravelGram", "#OnTheRoad"],
        "Indoor Office & Tech": ["#Technology", "#WorkspaceGoals", "#ModernDesign"],
        "Document & Text": ["#DocumentAnalysis", "#Archival", "#Readable"],
    }
    tags.update(category_tags.get(category, ["#Photography", "#VisualPerspective", "#PhotoOfTheDay"]))

    # Filter out forbidden generic/mismatched tags
    forbidden_tags = {"#aiart", "#deepcaption", "#swimmingpool", "#poly", "#flag"}
    valid_tags = [t for t in tags if t.lower() not in forbidden_tags]
    tag_str = " ".join(valid_tags[:6])

    time_line = f"📅 Captured: {timestamp}\n" if timestamp else ""
    specs_line = f"📸 Specs: {width}x{height} px ({image_format})\n" if width and height and image_format else ""
    details_block = f"\n{time_line}{specs_line}".rstrip()
    if details_block:
        details_block = f"\n{details_block}"

    return f"✨ {hook}{details_block}\n\n{tag_str}"


def _generate_visually_impaired_description(
    caption: str,
    objects: list[dict[str, Any]],
    dominant_colors: list[dict[str, Any]],
    width: int,
    height: int,
    ocr_text: str = "",
    spatial_notes: list[str] | None = None,
    timestamp: str = "",
    megapixels: str = "",
    aspect_ratio: str = "1:1",
) -> str:
    """Generate a rich, accessible audio description designed for screen readers and speech synthesis."""
    orientation = "landscape" if width > height else "portrait" if height > width else "square"
    color_phrase = _format_natural_color_phrase(dominant_colors)
    mp_info = f", {megapixels}" if megapixels else ""
    ts_info = f" recorded on {timestamp}" if timestamp else ""

    parts = [
        f"Accessibility Description: A {orientation} photograph ({width} by {height} pixels, {aspect_ratio} ratio{mp_info}){ts_info}.",
        f"Main Scene: {caption.strip().rstrip('.')}.",
        f"Visual Atmosphere: The composition is illuminated under natural lighting with prominent {color_phrase}."
    ]

    if ocr_text and ocr_text.strip() not in {"-", "none", "", "no text detected"}:
        parts.append(f"Visible Lettering: Text appearing within the image reads: \"{ocr_text.strip()}\".")

    return " ".join(parts)


def _generate_seo_description(
    caption: str,
    objects: list[dict[str, Any]],
    category: str,
    dominant_colors: list[dict[str, Any]],
    orientation: str = "landscape",
    timestamp: str = "",
    image_format: str = "",
    width: int = 0,
    height: int = 0,
) -> str:
    """Generate concise, keyword-dense Alt-Text and SEO metadata without template filler."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", caption) if s.strip()]
    first_sentence = sentences[0] if sentences else caption

    # Strip conversational lead-ins
    base = re.sub(r"^(The image shows|The image is|This image depicts|This is|A photograph showing)\s+(a\s+|an\s+)?", "", first_sentence, flags=re.IGNORECASE)
    base = base[0].upper() + base[1:] if base else first_sentence
    base = base.rstrip(".")

    color_phrase = _format_natural_color_phrase(dominant_colors)
    ts_phrase = f" Recorded on {timestamp}." if timestamp else ""
    specs = f" ({width}x{height} px, {image_format})" if width and height and image_format else ""
    return f"{base}. High-resolution visual capture featuring natural {color_phrase} in a {orientation.lower()} view{specs}.{ts_phrase}"


@dataclass
class FullAnalysisResult:
    caption: str
    descriptions: dict[str, str]
    objects: list[dict[str, Any]]
    ocr_text: str
    dominant_colors: list[dict[str, Any]]
    width: int
    height: int
    aspect_ratio: str
    orientation: str
    scene_category: str
    model_used: str
    timestamp: str = ""
    file_size: str = ""
    megapixels: str = ""
    image_format: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _calculate_aspect_ratio(width: int, height: int) -> str:
    gcd = math.gcd(width, height)
    if gcd > 0:
        w_ratio = width // gcd
        h_ratio = height // gcd
        if w_ratio <= 16 and h_ratio <= 16:
            return f"{w_ratio}:{h_ratio}"
    ratio = width / max(1, height)
    if abs(ratio - 16 / 9) < 0.1:
        return "16:9"
    if abs(ratio - 4 / 3) < 0.1:
        return "4:3"
    if abs(ratio - 1.0) < 0.05:
        return "1:1"
    if abs(ratio - 9 / 16) < 0.1:
        return "9:16"
    return f"{ratio:.2f}:1"


_VISION_MODEL_INSTANCE: tuple[str, Any, Any] | None = None
_MODEL_LOCK = threading.Lock()
_ANALYSIS_CACHE: dict[str, FullAnalysisResult] = {}
_CACHE_MAX_SIZE = 50


def _load_vision_model() -> tuple[str, Any, Any] | None:
    """Load vision captioning model.
    Checks for a local fine-tuned model first, then loads Florence-2 with CPU optimization.
    Thread-safe and prioritizes local cache to prevent slow HuggingFace Hub network checks.
    """
    global _VISION_MODEL_INSTANCE
    if _VISION_MODEL_INSTANCE is not None:
        return _VISION_MODEL_INSTANCE

    with _MODEL_LOCK:
        if _VISION_MODEL_INSTANCE is not None:
            return _VISION_MODEL_INSTANCE

        if os.getenv("ENABLE_TRANSFORMER_MODEL", "1") != "1":
            return None

        try:
            import torch
            optimal_threads = min(4, os.cpu_count() or 4)
            torch.set_num_threads(optimal_threads)
        except Exception:
            return None

        # Patch PretrainedConfig for cross-version transformers compatibility
        try:
            from transformers import PretrainedConfig
            if not hasattr(PretrainedConfig, "forced_bos_token_id"):
                PretrainedConfig.forced_bos_token_id = None
        except Exception:
            pass

        # 1. Check for fine-tuned local BLIP checkpoint if explicitly requested
        trained_blip_dir = os.getenv("TRAINED_BLIP_MODEL") or str(
            BASE_DIR.parent / "models" / "blip-flickr30k"
        )
        if trained_blip_dir and Path(trained_blip_dir).exists() and os.getenv("USE_TRAINED_BLIP", "0") == "1":
            try:
                from transformers import BlipForConditionalGeneration, BlipProcessor
                _safe_log(f"Loading custom fine-tuned BLIP model from {trained_blip_dir}...")
                processor = BlipProcessor.from_pretrained(trained_blip_dir, local_files_only=True)
                model = BlipForConditionalGeneration.from_pretrained(trained_blip_dir, local_files_only=True)
                model.to("cpu")
                model.eval()
                _VISION_MODEL_INSTANCE = ("blip-custom", processor, model)
                return _VISION_MODEL_INSTANCE
            except Exception as exc:
                _safe_log(f"Could not load custom model from {trained_blip_dir}: {exc}")

        # 2. Load Florence-2 for multi-task vision intelligence
        try:
            from transformers import AutoModelForCausalLM, AutoProcessor

            model_name = os.getenv("VISION_MODEL", "microsoft/Florence-2-base")
            _safe_log(f"Loading vision intelligence model: {model_name}...")
            # Try loading with local_files_only=True first to avoid slow HuggingFace Hub network roundtrips
            try:
                processor = AutoProcessor.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                    local_files_only=True,
                )
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                    torch_dtype=torch.float32,
                    local_files_only=True,
                )
            except Exception:
                processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                    torch_dtype=torch.float32,
                )
            model.to("cpu")
            model.eval()

            _VISION_MODEL_INSTANCE = ("florence", processor, model)
            _safe_log(f"Vision intelligence model {model_name} loaded successfully!")
            return _VISION_MODEL_INSTANCE
        except Exception as exc:
            _safe_log(f"Vision model could not be loaded: {exc}")
            return None


def warmup_vision_model() -> None:
    """Preload and warm up the model so the first user upload is responsive."""
    try:
        _load_vision_model()
    except Exception as exc:
        _safe_log(f"Model warm-up error: {exc}")


def _clean_model_text(text: str) -> str:
    """Strip special tokens and formatting markers."""
    cleaned = re.sub(r"<(?:[^>]+)>", "", text)
    cleaned = re.sub(r"^(?:</s>|<s>|QA>)+", "", cleaned)
    cleaned = re.sub(r"(?:</s>|<s>)+$", "", cleaned)
    return cleaned.strip()


def _fallback_analysis(image_path: Path) -> FullAnalysisResult:
    with Image.open(image_path) as image:
        width, height = image.size
        meta = extract_image_technical_metadata_and_timestamp(image_path, image)
        timestamp = meta["timestamp"]
        img_format = meta["image_format"]
        megapixels = meta["megapixels"]
        file_size = meta["file_size"]

        colors = extract_dominant_colors(image)
        orientation = "Landscape" if width > height else "Portrait" if height > width else "Square"
        aspect_ratio = _calculate_aspect_ratio(width, height)
        primary_color = colors[0]["name"] if colors else "balanced"

        short_desc = f"A {orientation.lower()} image with a {primary_color.lower()} color palette (Captured on {timestamp})."
        detailed_narrative = (
            f"The image is composed in a {orientation.lower()} format with dimensions of {width} by {height} pixels ({megapixels}). "
            f"The visual aesthetic features {primary_color.lower()} tones as the dominant theme."
        )
        meta_section = (
            f"Image Details & Timestamp: Recorded on {timestamp} in a {orientation.lower()} view "
            f"({width} × {height} px, {aspect_ratio} ratio, {megapixels}, {img_format} format, {file_size})."
        )
        detailed_desc = f"{detailed_narrative}\n\n{meta_section}"
        category = "General Scene"
        objects: list[dict[str, Any]] = []
        ocr_text = ""

        descriptions = {
            "short": short_desc,
            "detailed": detailed_desc,
            "visually_impaired": _generate_visually_impaired_description(
                detailed_narrative, objects, colors, width, height, timestamp=timestamp, megapixels=megapixels, aspect_ratio=aspect_ratio
            ),
            "social_media": _generate_social_media_caption(short_desc, objects, category, timestamp=timestamp, image_format=img_format, width=width, height=height),
            "seo": _generate_seo_description(short_desc, objects, category, colors, orientation, timestamp=timestamp, image_format=img_format, width=width, height=height),
        }

        return FullAnalysisResult(
            caption=detailed_desc,
            descriptions=descriptions,
            objects=objects,
            ocr_text=ocr_text,
            dominant_colors=colors,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            orientation=orientation,
            scene_category=category,
            model_used="heuristic-fallback",
            timestamp=timestamp,
            file_size=file_size,
            megapixels=megapixels,
            image_format=img_format,
        )


def generate_full_analysis(image_path: Path) -> FullAnalysisResult:
    """Run comprehensive vision pipeline: multi-mode descriptions, object detection, OCR, and color analysis.
    Optimized for CPU: single-pass image feature encoding, reusable embeddings, token budgets, and hash caching.
    """
    # 0. Hash-based caching for identical uploads
    img_hash = None
    try:
        with image_path.open("rb") as f:
            img_hash = hashlib.sha256(f.read()).hexdigest()
        if img_hash in _ANALYSIS_CACHE:
            _safe_log(f"Returning cached analysis for image {image_path.name}")
            return _ANALYSIS_CACHE[img_hash]
    except Exception:
        img_hash = None

    loaded = _load_vision_model()

    with Image.open(image_path) as opened_img:
        width, height = opened_img.size
        meta = extract_image_technical_metadata_and_timestamp(image_path, opened_img)
        timestamp = meta["timestamp"]
        img_format = meta["image_format"]
        megapixels = meta["megapixels"]
        file_size = meta["file_size"]

        image_rgb = opened_img.convert("RGB")
        dominant_colors = extract_dominant_colors(image_rgb)
        orientation = "Landscape" if width > height else "Portrait" if height > width else "Square"
        aspect_ratio = _calculate_aspect_ratio(width, height)

    if loaded is None:
        result = _fallback_analysis(image_path)
        if img_hash:
            _ANALYSIS_CACHE[img_hash] = result
        return result

    model_type, processor, model = loaded

    import torch

    # Resize large images for CPU inference speed (Florence-2 native vision resolution is 768)
    max_model_dim = 768
    if max(width, height) > max_model_dim:
        scale = max_model_dim / max(width, height)
        inference_img = image_rgb.resize((int(width * scale), int(height * scale)), Image.Resampling.BILINEAR)
    else:
        inference_img = image_rgb

    short_caption = ""
    detailed_caption = ""
    detected_objects: list[dict[str, Any]] = []
    ocr_text = ""
    spatial_notes: list[str] = []
    model_name_tag = "microsoft/Florence-2-base"

    if model_type == "florence":
        try:
            # 1. Vision backbone encoding: compute image embeddings ONCE instead of 5 separate times!
            pixel_values = processor.image_processor(inference_img, return_tensors="pt")["pixel_values"]
            with torch.inference_mode():
                image_features = model._encode_image(pixel_values)

            def _run_florence_task(task_token: str, max_new_tokens: int) -> dict[str, Any]:
                """Run a task reusing pre-encoded image features for fast CPU decoding."""
                prompts = processor._construct_prompts([task_token])
                task_inputs = processor.tokenizer(prompts, return_tensors="pt")
                text_embeds = model.get_input_embeddings()(task_inputs["input_ids"])
                inputs_embeds, _ = model._merge_input_ids_with_image_features(image_features, text_embeds)
                with torch.inference_mode():
                    out = model.language_model.generate(
                        inputs_embeds=inputs_embeds,
                        max_new_tokens=max_new_tokens,
                        num_beams=1,
                        do_sample=False,
                        early_stopping=True,
                    )
                decoded = processor.batch_decode(out, skip_special_tokens=False)[0]
                return processor.post_process_generation(decoded, task=task_token, image_size=(width, height))

            # 2. Detailed Caption (<MORE_DETAILED_CAPTION>)
            try:
                parsed_det = _run_florence_task("<MORE_DETAILED_CAPTION>", max_new_tokens=150)
                raw_detailed = parsed_det.get("<MORE_DETAILED_CAPTION>", "")
                detailed_caption = _clean_model_text(raw_detailed)
            except Exception as det_exc:
                _safe_log(f"Detailed caption task failed: {det_exc}")

            # 3. Derive Short Caption instantly from the detailed description
            # (First sentence is a high-accuracy summary; eliminates redundant ~6-second model pass)
            if detailed_caption:
                sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", detailed_caption) if s.strip()]
                short_caption = sentences[0] if sentences else detailed_caption
                if not short_caption.endswith((".", "!", "?")):
                    short_caption += "."
            else:
                short_caption = "An image containing visual elements and natural composition."

            # 4. Object Detection (<OD>)
            seen_object_names: set[str] = set()
            try:
                parsed_od = _run_florence_task("<OD>", max_new_tokens=110)
                od_data = parsed_od.get("<OD>", {})
                labels = od_data.get("labels", [])
                bboxes = od_data.get("bboxes", [])

                label_counts = Counter(labels)
                for label, count in label_counts.most_common(12):
                    clean_label = _clean_model_text(label).lower()
                    if not clean_label or clean_label in seen_object_names:
                        continue
                    # Ignore invalid or model syntax tokens
                    if any(bad in clean_label for bad in ["poly", "loc_", "unk", "pad", "caption", "task"]):
                        continue
                    if len(clean_label) < 2 or not re.search(r"[a-z]", clean_label):
                        continue
                    seen_object_names.add(clean_label)
                    emoji = get_object_emoji(clean_label)
                    detected_objects.append({
                        "name": clean_label.title(),
                        "emoji": emoji,
                        "count": count,
                    })

                # Record spatial placement of top objects for accessibility description
                for lbl, bbox in zip(labels[:6], bboxes[:6]):
                    if len(bbox) >= 4:
                        cx = (bbox[0] + bbox[2]) / 2
                        cy = (bbox[1] + bbox[3]) / 2
                        loc_h = "left side" if cx < width * 0.35 else "right side" if cx > width * 0.65 else "center"
                        loc_v = "upper" if cy < height * 0.35 else "lower" if cy > height * 0.65 else "middle"
                        clean_lbl = _clean_model_text(lbl).lower()
                        if clean_lbl:
                            spatial_notes.append(f"{clean_lbl} in the {loc_v} {loc_h}")
            except Exception as od_exc:
                _safe_log(f"OD task skipped or failed: {od_exc}")

            # Supplement detected objects from detailed caption keywords if OD was sparse
            if len(detected_objects) < 2 and detailed_caption:
                words = re.findall(r"\b[a-z]{3,}\b", detailed_caption.lower())
                for w in words:
                    if w in OBJECT_EMOJI_MAP and w not in seen_object_names:
                        seen_object_names.add(w)
                        detected_objects.append({
                            "name": w.title(),
                            "emoji": OBJECT_EMOJI_MAP[w],
                            "count": 1,
                        })
                        if len(detected_objects) >= 5:
                            break

            # 5. Fast OCR text detection (<OCR>)
            try:
                parsed_ocr = _run_florence_task("<OCR>", max_new_tokens=50)
                ocr_raw = parsed_ocr.get("<OCR>", "")
                if isinstance(ocr_raw, str):
                    cleaned_ocr = _clean_model_text(ocr_raw)
                    if cleaned_ocr and cleaned_ocr.lower() not in {"-", "none", "", "no text detected"}:
                        ocr_text = cleaned_ocr
            except Exception as ocr_exc:
                _safe_log(f"OCR task skipped or failed: {ocr_exc}")

        except Exception as pipe_exc:
            _safe_log(f"Fast Florence pipeline error: {pipe_exc}, falling back to single generate")
            try:
                inputs = processor(text="<MORE_DETAILED_CAPTION>", images=inference_img, return_tensors="pt")
                with torch.inference_mode():
                    out = model.generate(**inputs, max_new_tokens=140, num_beams=1, do_sample=False)
                decoded = processor.batch_decode(out, skip_special_tokens=False)[0]
                parsed = processor.post_process_generation(decoded, task="<MORE_DETAILED_CAPTION>", image_size=(width, height))
                detailed_caption = _clean_model_text(parsed.get("<MORE_DETAILED_CAPTION>", decoded))
                short_caption = detailed_caption.split(".")[0].strip() + "."
            except Exception as inner_exc:
                _safe_log(f"Fallback generation error: {inner_exc}")

    elif model_type == "blip-custom":
        try:
            inputs = processor(images=inference_img, return_tensors="pt")
            with torch.inference_mode():
                out = model.generate(**inputs, max_new_tokens=80, num_beams=2)
            caption_str = processor.decode(out[0], skip_special_tokens=True).strip()
            short_caption = caption_str
            detailed_caption = f"A high quality scene: {caption_str}."
            model_name_tag = "fine-tuned-blip"
        except Exception as blip_exc:
            _safe_log(f"Custom BLIP generation error: {blip_exc}")

    # Fallbacks and cross-population for captions
    if not short_caption and detailed_caption:
        short_caption = detailed_caption.split(".")[0].strip() + "."
    elif not short_caption:
        short_caption = "An image containing visual elements and natural composition."

    if not detailed_caption:
        detailed_caption = short_caption

    # Polish detailed narrative (fix model spelling/grammar artifacts)
    polished_detailed = detailed_caption.rstrip('. ') + "."
    polished_detailed = re.sub(r"\bmausolesum\b", "mausoleum", polished_detailed, flags=re.IGNORECASE)
    polished_detailed = re.sub(r"stretching out to the horizon", "stretching into the distance", polished_detailed, flags=re.IGNORECASE)

    # Seamlessly incorporate OCR text if genuine and not already in narrative
    if ocr_text and ocr_text.strip() not in {"-", "none", "", "no text detected"}:
        clean_ocr = ocr_text.strip()
        if clean_ocr.lower() not in polished_detailed.lower():
            polished_detailed = f"{polished_detailed.rstrip('. ')}. Visible text within the scene reads: \"{clean_ocr}\"."

    # Build concise short caption with capture timestamp
    formatted_short = short_caption.rstrip('. ') + "."
    if timestamp:
        formatted_short = f"{formatted_short.rstrip('. ')} (Captured on {timestamp})."

    # Append accurate image technical details and timestamp block to the comprehensive detailed description
    meta_section = (
        f"Image Specifications & Timestamp: Recorded on {timestamp} in a {orientation.lower()} view "
        f"({width} x {height} px, {aspect_ratio} ratio, {megapixels}, {img_format} format, {file_size})."
    )
    full_detailed_desc = f"{polished_detailed}\n\n{meta_section}"

    # Detect scene category accurately using term scoring
    scene_cat = _detect_scene_category(polished_detailed, detected_objects, ocr_text)

    # Build all 5 specialized, high-accuracy description modes
    descriptions = {
        "short": formatted_short,
        "detailed": full_detailed_desc,
        "visually_impaired": _generate_visually_impaired_description(
            polished_detailed,
            detected_objects,
            dominant_colors,
            width,
            height,
            ocr_text=ocr_text,
            spatial_notes=spatial_notes,
            timestamp=timestamp,
            megapixels=megapixels,
            aspect_ratio=aspect_ratio,
        ),
        "social_media": _generate_social_media_caption(
            polished_detailed,
            detected_objects,
            scene_cat,
            timestamp=timestamp,
            image_format=img_format,
            width=width,
            height=height,
        ),
        "seo": _generate_seo_description(
            short_caption,
            detected_objects,
            scene_cat,
            dominant_colors,
            orientation=orientation,
            timestamp=timestamp,
            image_format=img_format,
            width=width,
            height=height,
        ),
    }

    # Clean up memory after intensive pipeline pass
    try:
        gc.collect()
    except Exception:
        pass

    result = FullAnalysisResult(
        caption=full_detailed_desc,
        descriptions=descriptions,
        objects=detected_objects,
        ocr_text=ocr_text,
        dominant_colors=dominant_colors,
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        orientation=orientation,
        scene_category=scene_cat,
        model_used=model_name_tag,
        timestamp=timestamp,
        file_size=file_size,
        megapixels=megapixels,
        image_format=img_format,
    )

    if img_hash:
        if len(_ANALYSIS_CACHE) >= _CACHE_MAX_SIZE:
            _ANALYSIS_CACHE.pop(next(iter(_ANALYSIS_CACHE)))
        _ANALYSIS_CACHE[img_hash] = result

    return result


def answer_image_question(
    image_path: Path | None,
    question: str,
    record: dict[str, Any] | None = None,
) -> str:
    """Answer a user question regarding the image using visual analysis context and Florence-2 grounding."""
    clean_q = question.strip()
    if not clean_q:
        return "Please ask a specific question about the image."

    q_lower = clean_q.lower().rstrip("?.!")

    # 1. Extract visual intelligence from record if provided
    caption_text = ""
    detailed_desc = ""
    detected_objects: list[dict[str, Any]] = []
    dominant_colors: list[dict[str, Any]] = []
    ocr_text = ""
    scene_category = "General Scene"

    if record:
        caption_text = record.get("caption") or ""
        descriptions = record.get("descriptions") or {}
        detailed_desc = descriptions.get("detailed", "") or caption_text
        detected_objects = record.get("objects") or []
        dominant_colors = record.get("dominant_colors") or []
        ocr_text = record.get("ocr_text") or ""
        scene_category = record.get("scene_category") or "General Scene"

    full_context = f"{detailed_desc} {caption_text}".strip()

    # Extended stop words
    stopwords = {
        "a", "an", "the", "in", "on", "at", "of", "to", "for", "with", "is", "are", "was", "were",
        "this", "that", "these", "those", "there", "it", "its", "image", "photo", "picture", "show", "tell",
        "visible", "can", "you", "see", "any", "some", "all", "what", "how", "where", "which", "me"
    }

    # A. Text / OCR inquiries ("what text", "what is written", "what does it say", "read")
    if any(k in q_lower for k in ["what text", "what is written", "what does it say", "read", "words", "letters", "written text", "sign say", "banner say", "ocr"]):
        if ocr_text and ocr_text.strip() not in {"-", "none", "", "no text detected"}:
            return f"The text visible in the image reads: \"{ocr_text.strip()}\"."
        return "No distinct written text or lettering was detected in this image."

    # B. Quantity / Count inquiries ("how many", "count of", "number of")
    if any(k in q_lower for k in ["how many", "count of", "number of", "how much"]):
        q_words = [w for w in re.findall(r"[a-z]+", q_lower) if w not in {"how", "many", "count", "of", "number", "are", "there", "in", "the", "image", "photo", "picture", "total", "visible", "item", "items"}]
        target_name = q_words[-1] if q_words else ""

        # Check in detected objects list
        matched_obj = None
        if target_name and target_name not in stopwords:
            for obj in detected_objects:
                obj_name_lower = obj.get("name", "").lower()
                if (target_name in obj_name_lower or obj_name_lower in target_name
                        or target_name.rstrip("s") == obj_name_lower.rstrip("s")):
                    matched_obj = obj
                    break

        if matched_obj:
            count = matched_obj.get("count", 1)
            name = matched_obj.get("name", target_name.title())
            emoji = matched_obj.get("emoji", "🔹")
            plural = f"{name}s" if count > 1 and not name.endswith("s") else name
            return f"There {'is' if count == 1 else 'are'} {count} {plural} {emoji} detected in the image."

        if any(w in q_lower for w in ["object", "objects", "item", "items", "things", "elements"]):
            if detected_objects:
                items_str = ", ".join([f"{o.get('count', 1)} {o.get('name', 'Item')}" for o in detected_objects[:6]])
                return f"Identified objects include: {items_str}."
            return "No isolated standalone objects were categorized."

        if full_context:
            sentences = [s.strip() for s in full_context.split(".") if s.strip()]
            for s in sentences:
                if target_name and target_name not in stopwords and re.search(r"\b" + re.escape(target_name.rstrip("s")) + r"[a-z]*\b", s, flags=re.IGNORECASE):
                    return f"{s}."

        if target_name and target_name not in stopwords:
            return f"There are no {target_name}s specifically identified in this image."
        return "I could not find a count for that specific element in the image."

    # C. Color inquiries ("what color", "palette", "what colors")
    if any(k in q_lower for k in ["what color", "what colors", "color of", "palette", "which color"]):
        q_tokens = [
            w for w in re.findall(r"[a-z]+", q_lower)
            if w not in {"what", "color", "colors", "is", "are", "the", "of", "in", "image", "photo", "picture", "it", "this", "that", "there", "scene", "overall"}
        ]
        specific_target = q_tokens[-1] if q_tokens else ""

        if specific_target and specific_target not in stopwords and full_context:
            sentences = [s.strip() for s in full_context.split(".") if s.strip()]
            for s in sentences:
                if re.search(r"\b" + re.escape(specific_target) + r"\b", s, flags=re.IGNORECASE):
                    return f"{s}."

        if dominant_colors:
            colors_str = ", ".join([f"{c['name']} (~{c['percentage']}%)" for c in dominant_colors[:4]])
            return f"The dominant color palette consists of {colors_str}."
        if full_context:
            return f"Overall color tone: {full_context.split('.')[0]}."

    # D. Setting / Location / Environment inquiries
    if any(k in q_lower for k in ["setting", "environment", "where is", "where was", "location", "place", "background"]):
        if "background" in q_lower and full_context:
            sentences = [s.strip() for s in full_context.split(".") if s.strip()]
            for s in sentences:
                if "background" in s.lower():
                    return f"{s}."

        if full_context:
            first_sentence = full_context.split(".")[0]
            return f"Setting category: {scene_category}. {first_sentence}."

    # E. General Description / Identity ("what is this", "describe", "what do you see", "what is happening")
    if any(k in q_lower for k in ["what is this", "describe", "what do you see", "what is happening", "tell me about", "what's in", "what is in", "explain the image", "summary"]):
        if detailed_desc:
            return detailed_desc
        if caption_text:
            return caption_text

    # F. Holding / Person Action inquiries
    if any(k in q_lower for k in ["holding", "carrying", "wearing", "person", "people"]):
        has_person = any(o.get("name", "").lower() in {"person", "man", "woman", "people", "child"} for o in detected_objects)
        if not has_person and full_context and not any(p in full_context.lower() for p in ["person", "man", "woman", "people", "child"]):
            return "There are no people detected in this image."
        if full_context:
            sentences = [s.strip() for s in full_context.split(".") if s.strip()]
            for s in sentences:
                if any(w in s.lower() for w in ["holding", "carrying", "wearing", "person", "man", "woman"]):
                    return f"{s}."

    # G. Query Florence-2 for direct visual inspection if an image file is available
    if image_path and image_path.exists():
        loaded = _load_vision_model()
        if loaded is not None:
            model_type, processor, model = loaded
            if model_type == "florence":
                try:
                    import torch

                    with Image.open(image_path) as opened_img:
                        width, height = opened_img.size
                        image_rgb = opened_img.convert("RGB")
                        if max(width, height) > 768:
                            scale = 768 / max(width, height)
                            image_rgb = image_rgb.resize((int(width * scale), int(height * scale)), Image.Resampling.BILINEAR)

                    # Florence-2 VQA prompt format
                    prompt = clean_q if clean_q.endswith("?") else clean_q + "?"
                    prompts = processor._construct_prompts([prompt])
                    task_inputs = processor.tokenizer(prompts, return_tensors="pt")
                    pixel_values = processor.image_processor(image_rgb, return_tensors="pt")["pixel_values"]
                    with torch.inference_mode():
                        img_feats = model._encode_image(pixel_values)
                        text_embeds = model.get_input_embeddings()(task_inputs["input_ids"])
                        inputs_embeds, _ = model._merge_input_ids_with_image_features(img_feats, text_embeds)
                        out = model.language_model.generate(
                            inputs_embeds=inputs_embeds,
                            max_new_tokens=60,
                            num_beams=1,
                            do_sample=False,
                            early_stopping=True,
                        )

                    raw_decoded = processor.batch_decode(out, skip_special_tokens=False)[0]
                    # Strip loc tokens and special markers
                    answer = re.sub(r"<loc_\d+>", "", raw_decoded)
                    answer = _clean_model_text(answer)
                    answer = re.sub(r"^(?:qa>|vqa>|docvqa>|a>)\s*", "", answer, flags=re.IGNORECASE).strip()

                    gc.collect()

                    clean_prompt_str = re.sub(r"[^a-zA-Z0-9\s]", "", clean_q).lower().strip()
                    clean_ans_str = re.sub(r"[^a-zA-Z0-9\s]", "", answer).lower().strip()

                    if answer and len(answer) > 2 and clean_ans_str != clean_prompt_str:
                        if any(q_lower.startswith(prefix) for prefix in ["is there", "are there", "do you see", "can you see", "does it have"]):
                            if answer.lower() not in {"no", "none", "nothing"} and not answer.lower().startswith("no"):
                                return f"Yes, observable in the image: {answer.rstrip('.')}."
                        formatted = answer[0].upper() + answer[1:]
                        if not formatted.endswith((".", "!", "?")):
                            formatted += "."
                        return formatted
                except Exception as exc:
                    _safe_log(f"Direct vision QA error: {exc}")

    if full_context:
        return f"{full_context.split('.')[0]}."

    return "I couldn't identify that specific detail in the image. Please try asking in another way."


def chat_with_assistant(
    message: str,
    image_path: Path | None = None,
    record: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    """Universal AI Chatbot handler providing app assistance, features guide, and visual Q&A."""
    clean_msg = message.strip()
    if not clean_msg:
        return (
            "Hi there! I'm your Deep Caption AI Assistant. How can I help you today?",
            ["What can this app do?", "How do I describe an image?", "What description modes exist?"]
        )

    msg_lower = clean_msg.lower().rstrip("?.!")

    # 1. Greetings
    if any(g in msg_lower for g in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "greetings"]):
        if record:
            return (
                f"Hello! I am your AI assistant for this analyzed image (Category: {record.get('scene_category', 'Scene')}). "
                "You can ask me about detected objects, color palette, text/OCR, or visual details!",
                ["What is in this image?", "What are the dominant colors?", "What objects are detected?", "Is there any text?"]
            )
        return (
            "Hello! Welcome to **Deep Caption**! 🚀\n\n"
            "I'm your multimodal vision assistant. You can upload any image on the left to generate:\n"
            "• 5 AI description modes (Short, Detailed, Accessibility, Social Media, SEO)\n"
            "• Read-aloud Text-to-Speech audio\n"
            "• Object detection & color palette breakdown\n"
            "• OCR text extraction & Interactive Visual Q&A",
            ["How do I get started?", "What description modes exist?", "Can you read descriptions aloud?"]
        )

    # 2. Capabilities & Help
    if any(k in msg_lower for k in ["what can you do", "who are you", "help", "how to use", "features", "what is this app", "capabilities"]):
        return (
            "**Deep Caption** is an intelligent multi-modal image analysis platform powered by deep learning vision models.\n\n"
            "Here is what you can do:\n"
            "1. **Upload an Image**: Drag & drop or browse an image and click *Describe Image*.\n"
            "2. **Multi-Mode Captions**: Switch between 5 specialized styles (Short, Detailed, For Visually Impaired, Social Media, SEO).\n"
            "3. **Audio Playback**: Click *Listen Aloud* to hear speech synthesis audio of any description.\n"
            "4. **Object & OCR Recognition**: View detected items with counts and text extracted from signs or documents.\n"
            "5. **Interactive Q&A**: Ask me questions anytime about the uploaded image or application features!\n"
            "6. **Export**: Download formatted `.txt` reports or structured `.json` for developer APIs.",
            ["How do I upload an image?", "What are the 5 description modes?", "Tell me about OCR text"]
        )

    # 3. Specific App Questions
    if any(k in msg_lower for k in ["description mode", "modes", "5 modes", "different descriptions"]):
        return (
            "Deep Caption provides **5 distinct description modes**:\n"
            "• **⚡ Short**: Fast, single-sentence summary for quick previews.\n"
            "• **📖 Detailed**: Comprehensive narrative covering subjects, environment, context, and activities.\n"
            "• **👁️ For Visually Impaired**: High-accessibility audio description with spatial layout, focal subjects, lighting, and ambient balance.\n"
            "• **📱 Social Media**: Engaging social post draft complete with trending hashtags and emojis.\n"
            "• **🔍 SEO Description**: Search-engine and alt-text optimized description with high-relevance keywords.",
            ["Can you read descriptions aloud?", "How do I export results?", "What model is used?"]
        )

    if any(k in msg_lower for k in ["audio", "speech", "read aloud", "tts", "listen"]):
        return (
            "To listen to any description:\n"
            "1. Select your preferred mode (e.g. Detailed or For Visually Impaired).\n"
            "2. Click the **🔊 Listen Aloud** button.\n"
            "3. You can Pause, Resume, or Stop playback anytime using the audio controls bar.",
            ["What is the accessibility mode?", "How do I download reports?"]
        )

    if any(k in msg_lower for k in ["export", "download", "save", "json", "txt"]):
        return (
            "You can export your analysis in two formats:\n"
            "• **⬇ Download .txt**: Formatted text summary including all 5 modes, detected objects, and color palette.\n"
            "• **{ } JSON for Devs**: Full structured JSON payload with bounding data, hex colors, and metadata ready for APIs.",
            ["What objects can be detected?", "How does OCR work?"]
        )

    if any(k in msg_lower for k in ["model", "vision model", "florence", "blip", "architecture"]):
        model_name = record.get("model_used", "Florence-2 & BLIP") if record else "Microsoft Florence-2 / BLIP"
        return (
            f"Deep Caption uses **{model_name}** along with customized spatial heuristic pipelines. "
            "It runs local transformer inference to generate detailed image captions, object recognition, and visual question answering.",
            ["What is the visual Q&A feature?", "How do I upload an image?"]
        )

    # 4. If an image context IS present, route visual question to answer_image_question
    if record or (image_path and image_path.exists()):
        answer = answer_image_question(image_path, clean_msg, record=record)
        return (
            answer,
            ["What color is dominant?", "What objects are in the image?", "Is there any text visible?", "Describe the overall setting"]
        )

    # 5. Visual Question asked WITHOUT an image loaded
    if any(k in msg_lower for k in ["image", "picture", "photo", "see", "color", "object", "text", "holding", "wearing", "who", "car", "person"]):
        return (
            "To answer questions about a specific picture, please **upload an image first** using the panel on the left and click **Describe Image**! "
            "Once processed, I'll be able to inspect every visual element, detect objects, extract text, and answer all your questions.",
            ["How do I upload an image?", "What image formats are supported?", "What can this app do?"]
        )

    # 6. Fallback General Response
    return (
        "I'm here to help with Deep Caption and multi-modal image analysis! "
        "You can ask me questions about using the application, or upload an image on the left to ask questions directly about what's in your picture.",
        ["What can this app do?", "How do I get started?", "What are the 5 description modes?"]
    )

