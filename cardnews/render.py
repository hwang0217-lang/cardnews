"""카드뉴스 글(JSON)을 1080x1350 이미지 7장으로 그린다.

디자인: 사진을 화면 가득 깔고, 글자를 사진 위에 얹고, 핵심 구절에 형광펜을 칠한다.
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from images import generate_image
from photos import get_photo

W, H = 1080, 1350
LIME = "#C8F04A"       # 포인트(형광펜) 색
DARK = "#1B1A17"       # 형광펜 위 글자색
WHITE = "#FFFFFF"
SOFT = "#E9E4DA"
HANDLE = os.environ.get("IG_HANDLE", "@nordic_log")
MARGIN = 64

BOLD_FONTS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
]
# Black 굵기는 별도 글꼴 패키지에 있어서, 없으면 Bold로 대신 써요.
BLACK_FONTS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Black.ttc",
] + BOLD_FONTS
REGULAR_FONTS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/malgun.ttf",
]


def font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    raise FileNotFoundError("한글 글꼴을 찾지 못했어요")


# ---------- 글자 배치 ----------

def norm(text: str) -> str:
    return " ".join(text.split())  # 줄바꿈·연속 공백은 한 칸 공백으로


def wrap_spans(draw, text, fnt, max_width):
    """text를 줄로 나눠 (시작, 끝) 위치 목록으로 돌려준다."""
    spans, line_start, line_end = [], None, None
    pos = 0
    for word in text.split(" "):
        w_start, w_end = pos, pos + len(word)
        pos = w_end + 1
        if not word:
            continue
        if line_start is None:
            line_start, line_end = w_start, w_end
        elif draw.textlength(text[line_start:w_end], font=fnt) <= max_width:
            line_end = w_end
        else:
            spans.append((line_start, line_end))
            line_start, line_end = w_start, w_end
        # 한 단어가 한 줄보다 길면 글자 단위로 쪼갠다
        while draw.textlength(text[line_start:line_end], font=fnt) > max_width:
            cut = line_start + 1
            while cut < line_end and draw.textlength(text[line_start:cut + 1], font=fnt) <= max_width:
                cut += 1
            spans.append((line_start, cut))
            line_start = cut
    if line_start is not None:
        spans.append((line_start, line_end))
    return spans


def text_height(draw, text, fnt, max_width, gap):
    n = len(wrap_spans(draw, norm(text), fnt, max_width))
    return n * fnt.size + max(0, n - 1) * gap


def draw_text(draw, text, fnt, x, y, max_width, fill, gap, last_fill=None):
    """줄 단위로 그리고 다음 y를 돌려준다. last_fill이 있으면 마지막 줄만 그 색."""
    text = norm(text)
    spans = wrap_spans(draw, text, fnt, max_width)
    for i, (s, e) in enumerate(spans):
        color = last_fill if (last_fill and i == len(spans) - 1) else fill
        draw.text((x, y), text[s:e], font=fnt, fill=color)
        y += fnt.size + gap
    return y - gap


def draw_highlighted(draw, text, highlight, fnt, x, y, max_width, gap, fill=WHITE):
    """본문을 그리면서 highlight 구절에는 형광펜을 칠한다."""
    text = norm(text)
    hl = norm(highlight or "")
    h_start = text.find(hl) if hl else -1
    h_end = h_start + len(hl) if h_start >= 0 else -1
    for s, e in wrap_spans(draw, text, fnt, max_width):
        a, b = max(s, h_start), min(e, h_end)
        if h_start >= 0 and a < b:
            x0 = x + draw.textlength(text[s:a], font=fnt)
            x1 = x + draw.textlength(text[s:b], font=fnt)
            draw.rectangle((x0 - 4, y + 2, x1 + 4, y + fnt.size + 8), fill=LIME)
            draw.text((x, y), text[s:a], font=fnt, fill=fill)
            draw.text((x0, y), text[a:b], font=fnt, fill=DARK)
            draw.text((x1, y), text[b:e], font=fnt, fill=fill)
        else:
            draw.text((x, y), text[s:e], font=fnt, fill=fill)
        y += fnt.size + gap
    return y - gap


# ---------- 이미지 처리 ----------

def cover_crop(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def fallback_background(w: int, h: int) -> Image.Image:
    """사진이 없을 때: 어두운 따뜻한 회색 그라데이션."""
    top, bottom = (58, 52, 46), (24, 21, 18)
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return grad.resize((w, h))


_photo_cache: dict = {}


def full_photo(prompt: str, query: str, style: str = ""):
    """AI 생성 이미지 → 스톡 사진 → 어두운 배경 순으로 시도한다. 같은 요청은 한 번만 만든다."""
    key = (prompt, query, style)
    if key not in _photo_cache:
        ph = generate_image(prompt, style) if prompt else None
        if ph is None and query:
            ph = get_photo(query, "vertical")
        _photo_cache[key] = cover_crop(ph, W, H) if ph is not None else None
    cached = _photo_cache[key]
    if cached is None:
        return fallback_background(W, H), False
    return cached.copy(), True


def shade(img: Image.Image, stops) -> Image.Image:
    """stops=[(위치0~1, 어둡기0~255), ...]를 이어서 세로 그림자를 입힌다."""
    mask = Image.new("L", (1, img.height))
    for y in range(img.height):
        t = y / (img.height - 1)
        a = stops[-1][1]
        for (p0, a0), (p1, a1) in zip(stops, stops[1:]):
            if p0 <= t <= p1:
                a = a0 + (a1 - a0) * (t - p0) / (p1 - p0 or 1)
                break
        else:
            if t < stops[0][0]:
                a = stops[0][1]
        mask.putpixel((0, y), int(a))
    return Image.composite(Image.new("RGB", img.size, (14, 12, 10)), img, mask.resize(img.size))


def pill(d, x, y, text, fnt, fill, color, pad_x=28, pad_y=12):
    tw = d.textlength(text, font=fnt)
    d.rounded_rectangle((x, y, x + tw + pad_x * 2, y + fnt.size + pad_y * 2), 40, fill=fill)
    d.text((x + pad_x, y + pad_y - 2), text, font=fnt, fill=color)


def sticker(img: Image.Image, text: str, center, angle: float, fill, color):
    """사진 위에 붙이는 기울어진 라벨."""
    f = font(BOLD_FONTS, 38)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    tw = int(tmp.textlength(text, font=f))
    pad_x, pad_y = 26, 16
    w, h = tw + pad_x * 2, f.size + pad_y * 2
    tag = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    td = ImageDraw.Draw(tag)
    td.rounded_rectangle((4, 4, w + 4, h + 4), 12, fill=fill)
    td.text((4 + pad_x, 4 + pad_y - 3), text, font=f, fill=color)
    tag = tag.rotate(angle, expand=True, resample=Image.BICUBIC)
    img.paste(tag, (int(center[0] - tag.width / 2), int(center[1] - tag.height / 2)), tag)


def footer(d, page, total, y):
    d.line((MARGIN, y, W - MARGIN, y), fill="#6B655C", width=2)
    f = font(REGULAR_FONTS, 28)
    d.text((MARGIN, y + 22), HANDLE, font=f, fill=SOFT)
    label = f"{page} / {total}"
    d.text((W - MARGIN - d.textlength(label, font=f), y + 22), label, font=f, fill=SOFT)


EMOJI_FONTS = [  # (글꼴 경로, 글꼴 크기) - 컬러 이모지 글꼴은 정해진 크기로만 그릴 수 있어요
    ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109),
    ("/usr/share/fonts/noto/NotoColorEmoji.ttf", 109),
    ("C:/Windows/Fonts/seguiemj.ttf", 109),
]


def emoji_image(ch: str, size: int):
    """이모지 한 개를 컬러 그림으로 만든다. 글꼴이 없거나 실패하면 None (그러면 이모지만 빼고 진행)."""
    ch = (ch or "").strip()
    if not ch:
        return None
    for path, px in EMOJI_FONTS:
        if not Path(path).exists():
            continue
        try:
            fnt = ImageFont.truetype(path, px)
            tile = Image.new("RGBA", (px * 2, px * 2), (0, 0, 0, 0))
            ImageDraw.Draw(tile).text((px // 2, px // 4), ch, font=fnt, embedded_color=True)
            box = tile.getbbox()
            if not box:
                continue
            tile = tile.crop(box)
            scale = size / max(tile.size)
            return tile.resize((max(1, int(tile.width * scale)), max(1, int(tile.height * scale))), Image.LANCZOS)
        except Exception as e:
            print(f"이모지 그리기 실패({path}): {e}")
    return None


# ---------- 슬라이드 ----------

def cover(c, total):
    img, has_photo = full_photo(c.get("cover_image_prompt", ""), c.get("cover_photo_query", ""), c.get("visual_style", ""))
    img = shade(img, [(0, 70), (0.22, 20), (0.45, 70), (1, 235)])

    stickers = (c.get("cover_stickers") or [])[:2]
    positions = [((300, 470), -7), ((790, 560), 6)]
    for text, (center, angle), fill, color in zip(stickers, positions, (LIME, WHITE), (DARK, DARK)):
        sticker(img, text, center, angle, fill, color)

    d = ImageDraw.Draw(img)
    d.text((MARGIN, 62), HANDLE.lstrip("@"), font=font(BLACK_FONTS, 50), fill=WHITE)

    tf = font(BLACK_FONTS, 84)
    mw = W - MARGIN * 2
    sub_f = font(BOLD_FONTS, 42)
    th = text_height(d, c["cover_title"], tf, mw, 18)
    sh = text_height(d, c["cover_sub"], sub_f, mw, 10)
    y = H - 150 - sh - 30 - th
    d.text((MARGIN, y - 52), HANDLE.lstrip("@") + " 자취 주방", font=font(REGULAR_FONTS, 30), fill=SOFT)
    y = draw_text(d, c["cover_title"], tf, MARGIN, y, mw, WHITE, 18, last_fill=LIME)
    draw_text(d, c["cover_sub"], sub_f, MARGIN, y + 30, mw, SOFT, 10)
    d.text((MARGIN, H - 96), "옆으로 넘겨서 확인  →", font=font(BOLD_FONTS, 32), fill=LIME)
    label = f"1 / {total}"
    f = font(REGULAR_FONTS, 28)
    d.text((W - MARGIN - d.textlength(label, font=f), H - 94), label, font=f, fill=SOFT)
    return img


def body(item, num, page, total, style=""):
    img, has_photo = full_photo(item.get("image_prompt", ""), item.get("photo_query", ""), style)
    img = shade(img, [(0, 150), (0.2, 40), (0.5, 20), (0.66, 150), (1, 245)])
    d = ImageDraw.Draw(img)

    pill(d, MARGIN, 64, f"POINT {num}", font(BLACK_FONTS, 30), LIME, DARK)
    mw = W - MARGIN * 2
    emoji = emoji_image(item.get("emoji", ""), 66)
    tx = MARGIN + (84 if emoji else 0)          # 이모지가 있으면 제목을 오른쪽으로 비켜서 쓴다
    draw_text(d, item["title"], font(BLACK_FONTS, 66), tx, 140, mw - (tx - MARGIN), WHITE, 14)
    if emoji:
        img.paste(emoji, (MARGIN, 140 + 4), emoji)

    bf = font(REGULAR_FONTS, 44)
    bh = text_height(d, item["body"], bf, mw, 22)
    y = H - 150 - bh
    draw_highlighted(d, item["body"], item.get("highlight"), bf, MARGIN, y, mw, 22)
    footer(d, page, total, H - 112)
    return img


def closing(c, page, total):
    # 표지와 같은 사진을 재사용해서 이미지 생성 비용을 아낀다 (캐시에서 가져옴)
    img, has_photo = full_photo(c.get("cover_image_prompt", ""), c.get("cover_photo_query", ""), c.get("visual_style", ""))
    if has_photo:
        img = img.filter(ImageFilter.GaussianBlur(7))
    img = shade(img, [(0, 190), (1, 235)])
    d = ImageDraw.Draw(img)
    cf = font(BLACK_FONTS, 84)
    mw = W - 140
    th = text_height(d, c["closing"], cf, mw, 22)
    y = (H - th) // 2 - 90
    y = draw_text(d, c["closing"], cf, 70, y, mw, WHITE, 22, last_fill=LIME)
    pill(d, 70, y + 64, "저장 & 팔로우", font(BLACK_FONTS, 48), LIME, DARK, 48, 22)
    footer(d, page, total, H - 112)
    return img


def render_all(content: dict, out_dir: Path, style: dict = None, seed_text: str = "") -> list[Path]:
    # 스타일이 사진 꽉 채우기(photo)가 아니면 Canva 배경을 쓰는 다른 틀로 그린다
    if style and style.get("layout") != "photo":
        from layouts import render_styled

        return render_styled(content, out_dir, style, seed_text)
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(content["slides"]) + 2
    images = [cover(content, total)]
    for i, s in enumerate(content["slides"], 1):
        images.append(body(s, i, i + 1, total, content.get("visual_style", "")))
    images.append(closing(content, total, total))
    paths = []
    for i, im in enumerate(images, 1):
        p = out_dir / f"{i:02d}.jpg"
        im.convert("RGB").save(p, "JPEG", quality=92)
        paths.append(p)
    return paths


if __name__ == "__main__":
    import json
    import sys

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(render_all(data, Path(sys.argv[2])))
