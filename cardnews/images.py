"""Gemini 이미지 모델로 '사람 없는 실물 상품 사진'을 만든다. 키가 없거나 실패하면 None."""
import base64
import io
import os
import time

from PIL import Image

MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-nano-banana-2.1")
SIZE = os.environ.get("GEMINI_IMAGE_SIZE", "1K")  # 대문자 K만 허용돼요 (사진이 액자 안에 들어가서 1K로 충분해요)
ASPECT = "4:5"  # 카드뉴스 1080x1350과 같은 비율

RULES = (
    "Photorealistic product photograph, shot on a full-frame camera with an 85mm lens, "
    "soft natural window light, a clean uncluttered small studio-apartment kitchen, "
    "realistic materials, scale and proportions, sharp focus on the product, shallow depth of field. "
    "Strictly no people, no hands, no faces, no text, no letters, no logos, no brand names, "
    "no watermark, no illustration, no 3D render, no gold or metallic surreal materials."
)


def build_prompt(subject: str, style: str = "") -> str:
    parts = [subject.strip().rstrip("."), style.strip().rstrip("."), RULES]
    return ". ".join(p for p in parts if p)


def generate_image(subject: str, style: str = ""):
    key = os.environ.get("GEMINI_API_KEY")
    if not key or not subject:
        return None
    try:
        from google import genai
    except ImportError:
        print("google-genai가 설치되지 않았어요")
        return None

    client = genai.Client(api_key=key)
    prompt = build_prompt(subject, style)
    for attempt in range(3):
        try:
            interaction = client.interactions.create(
                model=MODEL,
                input=prompt,
                response_format={"type": "image", "aspect_ratio": ASPECT, "image_size": SIZE},
            )
            data = interaction.output_image.data
            raw = base64.b64decode(data) if isinstance(data, str) else data
            return Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception as e:
            print(f"이미지 생성 실패 {attempt + 1}/3 ({subject[:40]}): {e}")
            time.sleep(4 * (attempt + 1))
    return None
