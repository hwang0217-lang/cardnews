"""카드뉴스 글(JSON)을 1080x1350 이미지 7장으로 그린다. 사진이 있으면 사진 위주 레이아웃."""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from photos import get_photo

W, H = 1080, 1350
BG = "#F7F1E8"
ACCENT = "#E8743B"
ACCENT_LIGHT = "#FFD2B3"
TEXT = "#2B2B2B"
SUB = "#6F655A"
HANDLE = os.environ.get("IG_HANDLE", "@nordic_log")

BLACK_FONTS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Black.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
]
BOLD_FONTS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
]
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


def wrap(draw, text, fnt, max_width):
    lines, cur = [], ""
    for word in text.split():  # 줄바꿈·연속 공백은 한 칸 공백으로 취급
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_width:
            cur = trial
            continue
        if cur:
            lines.append(cur)
            cur = ""
        for ch in word:
            if draw.textlength(cur + ch, font=fnt) <= max_width:
                cur += ch
            else:
                lines.append(cur)
                cur = ch
    if cur:
        lines.append(cur)
    return lines


def block_height(draw, text, fnt, max_width, gap):
    return len(wrap(draw, text, fnt, max_width)) * (fnt.size + gap) - gap


def draw_block(draw, text, fnt, x, y, max_width, fill, gap):
    for line in wrap(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + gap
    return y


def cover_crop(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def fallback_background(w: int, h: int) -> Image.Image:
    """사진이 없을 때: 주황 계열 그라데이션."""
    top, bottom = (232, 116, 59), (196, 78, 30)
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return grad.resize((w, h))


def photo_or_fallback(query: str, w: int, h: int) -> tuple[Image.Image, bool]:
    # 가로로 넓은 칸(본문 위쪽)은 가로 사진, 꽉 찬 세로 칸(표지·마지막)은 세로 사진을 가져와요.
    ph = get_photo(query, "horizontal" if w / h > 0.9 else "vertical")
    if ph is None:
        return fallback_background(w, h), False
    return cover_crop(ph, w, h), True


def vertical_shade(img: Image.Image, start: float, end_alpha: int, start_alpha: int = 0) -> Image.Image:
    """start(0~1) 지점부터 아래로 갈수록 어두워지는 그림자."""
    mask = Image.new("L", (1, img.height))
    for y in range(img.height):
        t = max(0.0, (y / img.height - start) / (1 - start))
        mask.putpixel((0, y), int(start_alpha + (end_alpha - start_alpha) * t))
    mask = mask.resize(img.size)
    return Image.composite(Image.new("RGB", img.size, (22, 16, 10)), img, mask)


def pill(d, x, y, text, fnt, fill, color, pad_x=34, pad_y=16):
    tw = d.textlength(text, font=fnt)
    d.rounded_rectangle((x, y, x + tw + pad_x * 2, y + fnt.size + pad_y * 2), 60, fill=fill)
    d.text((x + pad_x, y + pad_y - 2), text, font=fnt, fill=color)
    return x + tw + pad_x * 2


def page_chip(d, page, total):
    f = font(BOLD_FONTS, 30)
    t = f"{page} / {total}"
    tw = d.textlength(t, font=f)
    x = W - 70 - tw - 48
    d.rounded_rectangle((x, 70, W - 70, 70 + 30 + 28), 40, fill="#3A2F26")
    d.text((x + 24, 84), t, font=f, fill="#FFFFFF")


def cover(c, total):
    img, has_photo = photo_or_fallback(c.get("cover_photo_query", ""), W, H)
    img = vertical_shade(img, 0.30, 235, 40 if has_photo else 0)
    d = ImageDraw.Draw(img)
    pill(d, 70, 70, "원룸 자취 주방템", font(BOLD_FONTS, 36), ACCENT, "#FFFFFF")
    page_chip(d, 1, total)

    title_f = font(BLACK_FONTS, 112)
    sub_f = font(BOLD_FONTS, 50)
    mw = W - 140
    th = block_height(d, c["cover_title"], title_f, mw, 22)
    sh = block_height(d, c["cover_sub"], sub_f, mw, 12)
    y = H - 190 - sh - 44 - th
    y = draw_block(d, c["cover_title"], title_f, 70, y, mw, "#FFFFFF", 22)
    draw_block(d, c["cover_sub"], sub_f, 70, y + 32, mw, ACCENT_LIGHT, 12)
    d.text((70, H - 120), "옆으로 넘겨서 확인  →", font=font(BOLD_FONTS, 38), fill="#FFFFFF")
    d.text((W - 70 - d.textlength(HANDLE, font=font(REGULAR_FONTS, 32)), H - 118), HANDLE,
           font=font(REGULAR_FONTS, 32), fill="#E8E0D6")
    return img


def body(item, num, page, total):
    PH_H = 760
    photo, _ = photo_or_fallback(item.get("photo_query", ""), W, PH_H)
    img = Image.new("RGB", (W, H), BG)
    img.paste(photo, (0, 0))
    d = ImageDraw.Draw(img)
    # 아래 카드가 사진 위로 둥글게 올라오는 모양
    d.rounded_rectangle((0, PH_H - 70, W, H + 80), 70, fill=BG)
    # 번호 배지
    d.ellipse((70, PH_H - 130, 70 + 140, PH_H + 10), fill=ACCENT, outline=BG, width=10)
    nf = font(BLACK_FONTS, 84)
    t = str(num)
    d.text((70 + 70 - d.textlength(t, font=nf) / 2, PH_H - 130 + 70 - nf.size * 0.58), t, font=nf, fill="#FFFFFF")

    mw = W - 140
    tf = font(BLACK_FONTS, 70)
    y = draw_block(d, item["title"], tf, 70, PH_H + 60, mw, TEXT, 16)
    d.rounded_rectangle((70, y + 22, 70 + 120, y + 32), 5, fill=ACCENT)
    draw_block(d, item["body"], font(REGULAR_FONTS, 46), 70, y + 70, mw, SUB, 20)

    sf = font(REGULAR_FONTS, 28)
    d.text((70, H - 62), HANDLE, font=sf, fill="#9A8F83")
    label = f"{page} / {total}"
    d.text((W - 70 - d.textlength(label, font=sf), H - 62), label, font=sf, fill="#9A8F83")
    return img


def closing(c, page, total):
    img, has_photo = photo_or_fallback(c.get("closing_photo_query") or c.get("cover_photo_query", ""), W, H)
    if has_photo:
        img = img.filter(ImageFilter.GaussianBlur(6))
    img = vertical_shade(img, 0.0, 215, 150 if has_photo else 0)
    d = ImageDraw.Draw(img)
    page_chip(d, page, total)
    cf = font(BLACK_FONTS, 92)
    mw = W - 160
    th = block_height(d, c["closing"], cf, mw, 24)
    y = (H - th) // 2 - 80
    y = draw_block(d, c["closing"], cf, 80, y, mw, "#FFFFFF", 24)
    pill(d, 80, y + 60, "저장 & 팔로우", font(BLACK_FONTS, 50), ACCENT, "#FFFFFF", 52, 24)
    hf = font(REGULAR_FONTS, 34)
    d.text((80, H - 120), HANDLE, font=hf, fill="#E8E0D6")
    return img


def render_all(content: dict, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(content["slides"]) + 2
    images = [cover(content, total)]
    for i, s in enumerate(content["slides"], 1):
        images.append(body(s, i, i + 1, total))
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
