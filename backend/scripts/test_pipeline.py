from pathlib import Path
from PIL import Image, ImageDraw
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.caption_service import generate_full_analysis, answer_image_question

def run_tests():
    print("========================================")
    print("Testing Vision Intelligence Capabilities")
    print("========================================")

    # 1. Create a rich synthetic test image with shapes, colors, and embedded text
    test_img_path = BASE_DIR / "test_vision_composite.png"
    img = Image.new("RGB", (600, 400), color="beige")
    draw = ImageDraw.Draw(img)

    # Draw blue rectangle
    draw.rectangle([50, 60, 240, 220], fill="navy", outline="black", width=2)
    draw.text((70, 120), "AI SYSTEM 2026", fill="white")

    # Draw green circle
    draw.ellipse([340, 100, 480, 240], fill="green", outline="black", width=2)

    # Draw a bottom banner with text
    draw.rectangle([20, 320, 580, 380], fill="crimson")
    draw.text((40, 340), "CAPSTONE OBJECT DETECTION & OCR VERIFIED", fill="yellow")

    img.save(test_img_path)
    print(f"Created test image at: {test_img_path}")

    # 2. Run Full Analysis
    print("\n--- Running generate_full_analysis ---")
    result = generate_full_analysis(test_img_path)

    print(f"\n[Model Used]: {result.model_used}")
    print(f"[Scene Category]: {result.scene_category}")
    print(f"[Aspect Ratio]: {result.aspect_ratio} ({result.width}x{result.height})")

    print("\n[DESCRIPTIONS]:")
    print(f"  Short: {result.descriptions['short']}")
    print(f"\n  Detailed: {result.descriptions['detailed']}")
    print(f"\n  Visually Impaired: {result.descriptions['visually_impaired']}")
    print(f"\n  Social Media: {result.descriptions['social_media']}")
    print(f"\n  SEO: {result.descriptions['seo']}")

    print("\n[OBJECTS DETECTED]:")
    if result.objects:
        for obj in result.objects:
            print(f"  {obj['emoji']} {obj['name']}: count={obj['count']}")
    else:
        print("  (No objects detected)")

    print("\n[OCR TEXT DETECTED]:")
    print(f"  \"{result.ocr_text}\"")

    print("\n[DOMINANT COLORS]:")
    for col in result.dominant_colors[:3]:
        print(f"  {col['name']} ({col['hex']}): {col['percentage']}%")

    # 3. Test Interactive Intelligence (Ask About Image)
    print("\n--- Testing Interactive Intelligence (Ask About Image) ---")
    questions = [
        "What text is written on the crimson banner at the bottom?",
        "What color is the circle?",
        "What is written inside the blue rectangle?",
    ]

    for q in questions:
        answer = answer_image_question(test_img_path, q)
        print(f"  Q: {q}")
        print(f"  A: {answer}\n")

    # Clean up test image
    if test_img_path.exists():
        test_img_path.unlink()

    print("========================================")
    print("Vision Intelligence Pipeline Test Completed Successfully!")
    print("========================================")

if __name__ == "__main__":
    run_tests()
