"""카드뉴스 글(JSON)을 1080x1350 이미지 7장으로 그린다."""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
BG = "#F7F1E8"
ACCENT = "#E8743B"
TEXT = "#2B2B2B"
SUB = "#7A6F63"
CARD = "#FFFFFF"
HANDLE = os.environ.get("IG_HANDLE", "@nordic_log")

BOLD_FONTS = [
    "C:/Windows/Fonts/malgunbd.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
]
REGULAR_FONTS = [
    "C:/Windows/Fonts/malgun.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]


def font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    raise FileNotFoundError("한글 글꼴을 찾지 못했어요")


def wrap(draw, text, fnt, max_width):
    """글자 단위로 줄바꿈 (한국어는 띄어쓰기가 짧아서 글자 기준이 안전해요)."""
    lines, cur = [], ""
    for word in text.split():  # 줄바꿈·연속 공백은 모두 한 칸 공백으로 취급
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


def draw_block(draw, text, fnt, x, y, max_width, fill, line_gap):
    for line in wrap(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + line_gap
    return y


def footer(draw, page, total, inside=False):
    f = font(REGULAR_FONTS, 30)
    x0, y = (120, H - 150) if inside else (80, H - 90)
    draw.text((x0, y), HANDLE, font=f, fill=SUB)
    label = f"{page} / {total}"
    draw.text((W - x0 - draw.textlength(label, font=f), y), label, font=f, fill=SUB)


def cover(c, total):
    img = Image.new("RGB", (W, H), ACCENT)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, 70, W - 70, H - 70), 48, fill=BG)
    tag = font(BOLD_FONTS, 38)
    d.rounded_rectangle((120, 140, 460, 214), 37, fill=ACCENT)
    d.text((150, 154), "원룸 자취 주방템", font=tag, fill="#FFFFFF")
    title = font(BOLD_FONTS, 104)
    y = draw_block(d, c["cover_title"], title, 120, 380, W - 240, TEXT, 26)
    sub = font(REGULAR_FONTS, 48)
    draw_block(d, c["cover_sub"], sub, 120, y + 40, W - 240, SUB, 14)
    d.text((120, H - 260), "옆으로 넘겨서 확인 →", font=font(BOLD_FONTS, 40), fill=ACCENT)
    footer(d, 1, total, inside=True)
    return img


def body(item, num, page, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, 110, W - 70, H - 140), 48, fill=CARD)
    d.ellipse((120, 170, 250, 300), fill=ACCENT)
    nf = font(BOLD_FONTS, 76)
    t = str(num)
    d.text((185 - d.textlength(t, font=nf) / 2, 190), t, font=nf, fill="#FFFFFF")
    y = draw_block(d, item["title"], font(BOLD_FONTS, 78), 120, 370, W - 240, TEXT, 20)
    d.rectangle((120, y + 30, 260, y + 40), fill=ACCENT)
    draw_block(d, item["body"], font(REGULAR_FONTS, 50), 120, y + 90, W - 240, SUB, 22)
    footer(d, page, total)
    return img


def closing(c, page, total):
    img = Image.new("RGB", (W, H), ACCENT)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, 70, W - 70, H - 70), 48, fill=BG)
    y = draw_block(d, c["closing"], font(BOLD_FONTS, 82), 120, 400, W - 240, TEXT, 24)
    d.rounded_rectangle((120, y + 60, 560, y + 160), 50, fill=ACCENT)
    d.text((165, y + 85), "저장 & 팔로우", font=font(BOLD_FONTS, 52), fill="#FFFFFF")
    footer(d, page, total, inside=True)
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
        im.save(p, "JPEG", quality=92)
        paths.append(p)
    return paths


if __name__ == "__main__":
    import json
    import sys

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(render_all(data, Path(sys.argv[2])))
