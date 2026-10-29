"""살림 계정 카드뉴스의 여러 가지 디자인.

배경(Canva에서 만든 이미지) + 틀(폴라로이드·체크리스트·분할) + 글꼴 + 색을 묶은 '스타일'을 날마다 다르게 골라 쓴다.
서버에 글꼴이 없으면 비슷한 글꼴로 대신해서 멈추지 않는다.
"""
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from images import generate_image
from photos import get_photo

W, H = 1080, 1350
HERE = Path(__file__).parent
BG_DIR = HERE / "backgrounds"
HANDLE = os.environ.get("IG_HANDLE", "@nordic_log")
SCALES = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5)  # 글이 길어서 안 들어가면 이 순서로 줄여 가며 다시 짠다

# ---------------------------------------------------------------- 글꼴
FONT_DIRS = ["/usr/share/fonts", "C:/Windows/Fonts", str(HERE / "fonts")]
FONT_CANDIDATES = {
    "sans_black": ["NotoSansCJK-Black.ttc", "NotoSansCJK-Bold.ttc", "NanumGothicBold.ttf", "malgunbd.ttf"],
    "sans_bold": ["NotoSansCJK-Bold.ttc", "NanumGothicBold.ttf", "malgunbd.ttf"],
    "sans_reg": ["NotoSansCJK-Regular.ttc", "NanumGothic.ttf", "malgun.ttf"],
    "serif": ["NotoSerifCJK-Bold.ttc", "NanumMyeongjoBold.ttf", "HANBatangB.ttf", "batang.ttc"],
    "pen": ["NanumPen.ttf", "NanumBarunpenB.ttf", "NanumBrush.ttf", "NanumGothicBold.ttf", "malgunbd.ttf"],
    "brush": ["NanumBrush.ttf", "NanumPen.ttf", "NanumGothicBold.ttf", "malgunbd.ttf"],
    "round": ["NanumSquareRoundEB.ttf", "NanumSquareRoundB.ttf", "NanumBarunGothicBold.ttf",
              "HanSantteutDotum-Bold.ttf", "NanumGothicBold.ttf", "malgunbd.ttf"],
}
# 손글씨 글꼴은 같은 크기여도 작아 보여서 키워 준다
SIZE_SCALE = {"pen": 1.32, "brush": 1.15, "round": 1.0, "serif": 0.98, "sans_black": 1.0, "sans_bold": 1.0, "sans_reg": 1.0}
_index = {}
_font_cache = {}


def _build_index():
    if _index:
        return
    for d in FONT_DIRS:
        if not Path(d).exists():
            continue
        for root, _dirs, files in os.walk(d):
            for f in files:
                _index.setdefault(f.lower(), str(Path(root) / f))


def find_font(key: str):
    _build_index()
    for name in FONT_CANDIDATES[key]:
        p = _index.get(name.lower())
        if p:
            return p
    raise FileNotFoundError(f"글꼴을 찾지 못했어요: {key}")


def font(key: str, size: float):
    path = find_font(key)
    pen_like = Path(path).name.lower().startswith(("nanumpen", "nanumbrush", "nanumbarunpen"))
    size = int(round(size * (SIZE_SCALE.get(key, 1.0) if pen_like else 1.0)))
    k = (path, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(path, size)
    return _font_cache[k]


def describe_fonts() -> str:
    out = []
    for k in FONT_CANDIDATES:
        try:
            out.append(f"{k}={Path(find_font(k)).name}")
        except FileNotFoundError:
            out.append(f"{k}=없음")
    return ", ".join(out)


# ---------------------------------------------------------------- 스타일
def _c(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


CANVA_STYLES = [
    dict(id="kraft-doodle-polaroid", bg="bg05-kraft-doodle", layout="polaroid", title="pen", body="sans_reg",
         ink=_c("3B2A1E"), accent=_c("B5523B"), paper=_c("F4E8D2"), inner=(130, 160, 950, 1190), dark=False),
    dict(id="kraft-crumpled-checklist", bg="bg06-kraft-crumpled", layout="checklist", title="serif", body="sans_reg",
         ink=_c("3A2B20"), accent=_c("A8442F"), paper=_c("F1E3C8"), inner=(120, 150, 960, 1200), dark=False),
    dict(id="gingham-bows-polaroid", bg="bg03-gingham-bows", layout="polaroid", title="serif", body="sans_reg",
         ink=_c("4A2E24"), accent=_c("C23B3B"), paper=_c("F7EBD3"), inner=(190, 210, 890, 1150), dark=False),
    dict(id="gingham-corners-split", bg="bg04-gingham-corners", layout="split", title="sans_black", body="sans_reg",
         ink=_c("3E2A22"), accent=_c("C23B3B"), paper=_c("FBF1DC"), inner=(130, 150, 950, 1200), dark=False),
    dict(id="cream-blobs-split", bg="bg01-cream-blobs", layout="split", title="round", body="sans_reg",
         ink=_c("4A3326"), accent=_c("D9733F"), paper=_c("FFF6E6"), inner=(110, 170, 970, 1190), dark=False),
    dict(id="utensil-border-checklist", bg="bg02-utensil-border", layout="checklist", title="sans_black", body="sans_reg",
         ink=_c("4B3426"), accent=_c("C46A3A"), paper=_c("FBF0DC"), inner=(150, 170, 930, 1180), dark=False),
    dict(id="mint-leaves-polaroid", bg="bg07-mint-leaves", layout="polaroid", title="round", body="sans_reg",
         ink=_c("1E4D3F"), accent=_c("E0A93B"), paper=_c("F4FBF6"), inner=(110, 170, 920, 1170), dark=False),
    dict(id="mint-wave-checklist", bg="bg08-mint-wave", layout="checklist", title="serif", body="sans_reg",
         ink=_c("1E4D3F"), accent=_c("D4932E"), paper=_c("F1F8F0"), inner=(215, 250, 865, 1110), dark=False, narrow=True),
    dict(id="diary-tape-polaroid", bg="bg09-diary-tape", layout="polaroid", title="pen", body="sans_reg",
         ink=_c("4A3524"), accent=_c("C8782E"), paper=_c("FFF8E3"), inner=(120, 140, 960, 1210), dark=False),
    dict(id="note-grid-checklist", bg="bg10-note-grid", layout="checklist", title="pen", body="sans_reg",
         ink=_c("3F3022"), accent=_c("D0592F"), paper=_c("FFF7DD"), inner=(120, 140, 960, 1210), dark=False),
    dict(id="chalk-border-split", bg="bg11-chalk-border", layout="split", title="round", body="sans_reg",
         ink=_c("F5F1E6"), accent=_c("F7D56B"), paper=_c("2D2D2B"), inner=(130, 150, 950, 1200), dark=True),
    dict(id="chalk-hearts-polaroid", bg="bg12-chalk-hearts", layout="polaroid", title="pen", body="sans_reg",
         ink=_c("F7F2E7"), accent=_c("FFB3C1"), paper=_c("2B2B2A"), inner=(130, 150, 950, 1200), dark=True),
]

# ---- 사진 위주 스타일: 사진은 크게 쓰고 틀 색 · 글꼴 · 글 위치 · 강조 방식만 바꿔 가며 쓴다 ----
_WHITE, _DARKINK = (255, 255, 255), (27, 26, 23)
PHOTO_STYLES = [
    dict(id="p-lime-bottom", layout="photo2", title="sans_black", accent=_c("C8F04A"), ink=_WHITE,
         frame="none", text_pos="bottom", label="pill", marker="fill", align="left"),
    dict(id="p-orange-top", layout="photo2", title="sans_black", accent=_c("FF8A3D"), ink=_WHITE,
         frame="inset", frame_color=_WHITE, text_pos="top", label="tag", marker="soft", align="left"),
    dict(id="p-gold-matte-serif", layout="photo2", title="serif", accent=_c("E8C27A"), ink=_WHITE,
         frame="white", canvas=_c("F5EFE4"), text_pos="bottom", label="line", marker="underline", align="left", page=True),
    dict(id="p-sky-left", layout="photo2", title="sans_black", accent=_c("7CC4FF"), ink=_WHITE,
         frame="none", text_pos="left", label="tag", marker="color", align="left"),
    dict(id="p-coral-center", layout="photo2", title="round", accent=_c("FF6F61"), ink=_WHITE,
         frame="none", text_pos="center", label="pill", marker="fill", align="center"),
    dict(id="p-mint-band", layout="photo2", title="sans_bold", accent=_c("5EE0B5"), ink=_WHITE,
         frame="band", canvas=_c("0F2E2A"), text_pos="band", label="pill", marker="color", align="left"),
    dict(id="p-butter-rounded", layout="photo2", title="sans_black", accent=_c("FFD54A"), ink=_WHITE,
         frame="rounded", canvas=_c("1E1E1E"), text_pos="bottom", label="pill", marker="fill", align="left"),
    dict(id="p-mono-editorial", layout="photo2", title="serif", accent=_WHITE, ink=_WHITE,
         frame="inset", frame_color=_WHITE, text_pos="bottom", label="line", marker="underline", align="left", page=True),
    dict(id="p-navy-panel", layout="photo2", title="sans_bold", accent=_c("6AA9FF"), ink=_WHITE,
         frame="none", text_pos="panel", panel="dark", label="tag", marker="soft", align="left"),
    dict(id="p-peach-top-serif", layout="photo2", title="serif", accent=_c("FFB38A"), ink=_WHITE,
         frame="inset", frame_color=_c("FFB38A"), text_pos="top", label="line", marker="color", align="left"),
    dict(id="p-terracotta-center-serif", layout="photo2", title="serif", accent=_c("E8896B"), ink=_WHITE,
         frame="none", text_pos="center", label="line", marker="underline", align="center"),
    dict(id="p-green-left-serif", layout="photo2", title="serif", accent=_c("A8E063"), ink=_WHITE,
         frame="none", text_pos="left", label="pill", marker="fill", align="left"),
    dict(id="p-light-panel", layout="photo2", title="sans_black", accent=_c("FF6B35"), ink=_DARKINK,
         frame="none", text_pos="panel", panel="light", label="pill", marker="soft", align="left"),
]
# 기본으로는 사진 위주 스타일만 돌려 쓴다. (Canva 배경 스타일은 ENABLE_CANVA_STYLES=1일 때만 섞는다)
STYLES = PHOTO_STYLES + (CANVA_STYLES if os.environ.get("ENABLE_CANVA_STYLES") == "1" else [])
STYLE_BY_ID = {s["id"]: s for s in PHOTO_STYLES + CANVA_STYLES}


def pick_style(state: dict, seed_text: str) -> dict:
    """최근에 쓴 스타일(4개)은 피해서 하나 고른다. 같은 seed면 같은 결과가 나와 시험하기 쉽다."""
    recent = state.get("styles", [])[-4:]
    pool = [s for s in STYLES if s["id"] not in recent]
    return random.Random(seed_text).choice(pool)


# ---------------------------------------------------------------- 공통 도구
def blend(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def crop_to(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def load_background(style) -> Image.Image:
    p = BG_DIR / f"{style['bg']}.jpg"
    if p.exists():
        return Image.open(p).convert("RGBA")
    # 배경 파일이 없으면 종이색 단색으로 대신한다
    return Image.new("RGBA", (W, H), style["paper"] + (255,))


def shadowed(tile: Image.Image, offset=(8, 12), blur=16, opacity=100):
    pad = blur * 3
    base = Image.new("RGBA", (tile.width + pad * 2, tile.height + pad * 2), (0, 0, 0, 0))
    mask = Image.new("L", base.size, 0)
    mask.paste(tile.split()[3], (pad + offset[0], pad + offset[1]))
    mask = mask.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: v * opacity // 255)
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    shadow.putalpha(mask)
    base = Image.alpha_composite(base, shadow)
    base.alpha_composite(tile, (pad, pad))
    return base


def placeholder(w, h, style, label="") -> Image.Image:
    tile = Image.new("RGB", (w, h), blend(style["paper"], style["accent"], 0.25))
    return tile


def polaroid(photo, pw, ph, angle, paper=(255, 252, 246), border=22, bottom=88):
    w, h = pw + border * 2, ph + border + bottom
    tile = Image.new("RGBA", (w, h), paper + (255,))
    tile.paste(photo.convert("RGBA"), (border, border))
    tile = tile.rotate(angle, expand=True, resample=Image.BICUBIC)
    return shadowed(tile)


def rounded_photo(photo, w, h, radius=36, border=10, border_color=(255, 252, 246), angle=0.0, tape=None):
    tile = Image.new("RGBA", (w + border * 2, h + border * 2), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, tile.width - 1, tile.height - 1), radius + border // 2,
                                           fill=border_color + (255,))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
    tile.paste(photo.convert("RGB"), (border, border), mask)
    if tape:
        pad = 40
        canvas = Image.new("RGBA", (tile.width, tile.height + pad), (0, 0, 0, 0))
        canvas.alpha_composite(tile, (0, pad))
        tp = Image.new("RGBA", (200, 56), tape + (175,))
        tp = tp.rotate(-4, expand=True, resample=Image.BICUBIC)
        canvas.alpha_composite(tp, ((canvas.width - tp.width) // 2, 6))
        tile = canvas
    if angle:
        tile = tile.rotate(angle, expand=True, resample=Image.BICUBIC)
    return shadowed(tile)


def circle_photo(photo, d, ring, ring_w=12, angle=0.0):
    tile = Image.new("RGBA", (d + ring_w * 2, d + ring_w * 2), (0, 0, 0, 0))
    ImageDraw.Draw(tile).ellipse((0, 0, tile.width - 1, tile.height - 1), fill=ring + (255,))
    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d - 1, d - 1), fill=255)
    tile.paste(photo.convert("RGB"), (ring_w, ring_w), mask)
    if angle:
        tile = tile.rotate(angle, expand=True, resample=Image.BICUBIC)
    return shadowed(tile, offset=(6, 10), blur=14, opacity=90)


def paste_center(img, tile, cx, y):
    img.alpha_composite(tile, (int(cx - tile.width / 2), int(y)))


# ---------------------------------------------------------------- 글자
def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
            continue
        if cur:
            lines.append(cur)
            cur = ""
        for ch in w:  # 한 단어가 너무 길면 글자 단위로 쪼갠다
            if draw.textlength(cur + ch, font=fnt) <= max_w:
                cur += ch
            else:
                lines.append(cur)
                cur = ch
    if cur:
        lines.append(cur)
    return lines


def fit_lines(draw, text, key, sizes, max_w, max_lines):
    for s in sizes:
        f = font(key, s)
        lines = wrap(draw, " ".join(text.split()), f, max_w)
        if len(lines) <= max_lines:
            return f, lines
    return f, lines[:max_lines]


def line_gap(f, ratio=0.24):
    return int(f.size * ratio)


def text_block_height(lines, f, ratio=0.24):
    return len(lines) * f.size + (len(lines) - 1) * line_gap(f, ratio)


def draw_lines(d, lines, f, x, y, fill, align="left", max_w=0, ratio=0.24, last_fill=None):
    for i, line in enumerate(lines):
        lx = x
        if align == "center":
            lx = x + (max_w - d.textlength(line, font=f)) / 2
        d.text((lx, y), line, font=f, fill=last_fill if (last_fill and i == len(lines) - 1) else fill)
        y += f.size + line_gap(f, ratio)
    return y


def draw_body(img, d, text, highlight, f, x, y, max_w, style, ratio=0.5, ink=None, mode="soft",
              center=False, hl_ink=(27, 26, 23)):
    """본문을 그리고 highlight 구절을 강조한다. mode: soft(반투명 형광펜) · fill(꽉 찬 형광펜) · underline · color.
    다음 y를 돌려준다."""
    ink = ink or style["ink"]
    text = " ".join(text.split())
    hl = " ".join((highlight or "").split())
    h0 = text.find(hl) if hl else -1
    h1 = h0 + len(hl) if h0 >= 0 else -1
    # 줄 나누기를 글자 위치로 기억한다
    spans, pos, start, end = [], 0, None, None
    for word in text.split(" "):
        ws, we = pos, pos + len(word)
        pos = we + 1
        if start is None:
            start, end = ws, we
        elif d.textlength(text[start:we], font=f) <= max_w:
            end = we
        else:
            spans.append((start, end))
            start, end = ws, we
    if start is not None:
        spans.append((start, end))
    gap = int(f.size * ratio)
    for s, e in spans:
        line = text[s:e]
        lx = x + ((max_w - d.textlength(line, font=f)) / 2 if center else 0)
        a, b = max(s, h0), min(e, h1)
        if h0 >= 0 and a < b:
            x0 = lx + d.textlength(text[s:a], font=f)
            x1 = lx + d.textlength(text[s:b], font=f)
            if mode in ("soft", "fill"):
                alpha = 255 if mode == "fill" else 110
                ov = Image.new("RGBA", (W, f.size + 16), (0, 0, 0, 0))
                ImageDraw.Draw(ov).rounded_rectangle((x0 - 6, 4, x1 + 6, f.size + 12), 10, fill=style["accent"] + (alpha,))
                img.alpha_composite(ov, (0, int(y) - 2))
            elif mode == "underline":
                d.rectangle((x0, y + f.size + 4, x1, y + f.size + 10), fill=style["accent"])
            mid_color = hl_ink if mode == "fill" else (style["accent"] if mode == "color" else ink)
            d.text((lx, y), text[s:a], font=f, fill=ink)
            d.text((x0, y), text[a:b], font=f, fill=mid_color)
            d.text((x1, y), text[b:e], font=f, fill=ink)
        else:
            d.text((lx, y), line, font=f, fill=ink)
        y += f.size + gap
    return y


def body_height(d, text, f, max_w, ratio=0.5):
    return text_block_height(wrap(d, " ".join(text.split()), f, max_w), f, ratio)


# 이모지 (컬러 글꼴이 없으면 그냥 빼고 진행)
EMOJI_FONTS = [
    ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109),
    ("/usr/share/fonts/noto/NotoColorEmoji.ttf", 109),
    ("C:/Windows/Fonts/seguiemj.ttf", 109),
]


def emoji_tile(ch: str, size: int):
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
            s = size / max(tile.size)
            return tile.resize((max(1, int(tile.width * s)), max(1, int(tile.height * s))), Image.LANCZOS)
        except Exception as e:
            print(f"이모지 그리기 실패({path}): {e}")
    return None


def sticker(img, text, center, angle, fill, color, size=40):
    f = font("sans_bold", size)
    d0 = ImageDraw.Draw(img)
    tw = int(d0.textlength(text, font=f))
    padx, pady = 28, 14
    w, h = tw + padx * 2, int(f.size * 1.0) + pady * 2
    tag = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    ImageDraw.Draw(tag).rounded_rectangle((4, 4, w + 4, h + 4), 10, fill=fill + (245,))
    ImageDraw.Draw(tag).text((4 + padx, 4 + pady - 3), text, font=f, fill=color)
    tag = shadowed(tag.rotate(angle, expand=True, resample=Image.BICUBIC), offset=(4, 6), blur=8, opacity=80)
    img.alpha_composite(tag, (int(center[0] - tag.width / 2), int(center[1] - tag.height / 2)))


# ---------------------------------------------------------------- 사진
_photo_cache = {}
PHOTO_STATS = {"missing": 0, "cover_missing": False}


def get_photo_image(prompt, query, style_text):
    """AI 사진만 쓴다. 엉뚱한 무료 스톡 사진은 글과 안 맞아서 쓰지 않는다. (ALLOW_STOCK_PHOTOS=1일 때만 허용)"""
    key = (prompt, query, style_text)
    if key not in _photo_cache:
        ph = generate_image(prompt, style_text) if prompt else None
        if ph is None and query and os.environ.get("ALLOW_STOCK_PHOTOS") == "1":
            ph = get_photo(query, "vertical")
        if ph is None:
            PHOTO_STATS["missing"] += 1
        _photo_cache[key] = ph
    return _photo_cache[key]


def photo_or_block(item, content, w, h, style):
    ph = get_photo_image(item.get("image_prompt", ""), item.get("photo_query", ""), content.get("visual_style", ""))
    if ph is None:
        return placeholder(w, h, style)
    return crop_to(ph, w, h)


def cover_photo(content, w, h, style):
    ph = get_photo_image(content.get("cover_image_prompt", ""), content.get("cover_photo_query", ""),
                         content.get("visual_style", ""))
    return placeholder(w, h, style) if ph is None else crop_to(ph, w, h)


# ---------------------------------------------------------------- 틀 1: 폴라로이드
def _footer(img, d, style, page, total):
    f = font("sans_reg", 28)
    x0, y0, x1, y1 = style["inner"]
    label = f"{page} / {total}"
    d.text((x1 - d.textlength(label, font=f), y1 + 4), label, font=f, fill=blend(style["ink"], style["paper"], 0.35))
    d.text((x0, y1 + 4), HANDLE, font=f, fill=blend(style["ink"], style["paper"], 0.35))


def polaroid_cover(content, style, rnd, total):
    img = load_background(style)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = style["inner"]
    win = x1 - x0
    angle = rnd.choice([-4, -3, 3, 4])
    for s in SCALES:
        pw = int(min(win * 0.72, 500) * s)
        tile = polaroid(cover_photo(content, pw, pw, style), pw, pw, angle, paper=(255, 252, 246))
        f_title, lines = fit_lines(d, content["cover_title"], style["title"], tuple(int(z * s) for z in (86, 78, 70, 62)), win, 3)
        f_sub, sub_lines = fit_lines(d, content.get("cover_sub", ""), "sans_reg", (int(38 * s), int(34 * s)), win, 2)
        total_h = tile.height - 60 + 20 + text_block_height(lines, f_title) + 26 + text_block_height(sub_lines, f_sub, 0.4)
        if total_h <= y1 - y0:
            break
    y = y0 + max(0, (y1 - y0 - total_h) // 2)
    cx = (x0 + x1) / 2
    paste_center(img, tile, cx, y - 20)
    for text, pos, ang, fill, col in zip((content.get("cover_stickers") or [])[:2],
                                         [(cx - pw * 0.42, y + 40), (cx + pw * 0.42, y + pw * 0.55)],
                                         [-8, 7], [style["accent"], style["paper"]],
                                         [(255, 255, 255) if not style["dark"] else (30, 30, 30), style["ink"]]):
        sticker(img, text, pos, ang, fill, col, 36)
    y += tile.height - 60 + 20
    y = draw_lines(d, lines, f_title, x0, y, style["ink"], "center", win, last_fill=style["accent"])
    draw_lines(d, sub_lines, f_sub, x0, y + 22, blend(style["ink"], style["paper"], 0.25), "center", win, 0.4)
    return img


def polaroid_body(item, content, style, rnd, num, page, total):
    img = load_background(style)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = style["inner"]
    win = x1 - x0
    angle = rnd.choice([-3.5, -2.5, 2.5, 3.5])
    emoji = emoji_tile(item.get("emoji", ""), 60)
    tx = x0 + (74 if emoji else 0)
    for s in SCALES:
        pw = int(min(win * 0.62, 440) * s)
        tile = polaroid(photo_or_block(item, content, pw, pw, style), pw, pw, angle)
        f_title, t_lines = fit_lines(d, item["title"], style["title"], tuple(int(z * s) for z in (62, 56, 50)), win - (74 if emoji else 0), 2)
        f_body = font(style["body"], 38 * s)
        b_h = body_height(d, item["body"], f_body, win)
        total_h = tile.height - 70 + 30 + text_block_height(t_lines, f_title) + 28 + b_h
        if total_h <= y1 - y0:
            break
    y = y0 + max(0, (y1 - y0 - total_h) // 2)
    side = 1 if num % 2 else -1
    cx = (x0 + x1) / 2 + side * (win - tile.width) * 0.25
    paste_center(img, tile, cx, y - 30)
    # 번호 스티커
    sticker(img, f"POINT {num}", (cx - side * tile.width * 0.38, y + 20), -6 * side, style["accent"],
            (255, 255, 255) if not style["dark"] else (30, 30, 30), 34)
    y += tile.height - 70 + 30
    if emoji:
        img.alpha_composite(emoji, (x0, int(y + (f_title.size - emoji.height) / 2 + 6)))
    y = draw_lines(d, t_lines, f_title, tx, y, style["ink"])
    draw_body(img, d, item["body"], item.get("highlight"), f_body, x0, y + 28, win, style)
    return img


# ---------------------------------------------------------------- 틀 2: 체크리스트(노트)
def checklist_cover(content, style, rnd, total):
    img = load_background(style)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = style["inner"]
    win = x1 - x0
    narrow = style.get("narrow")
    ang = rnd.choice([-4, 4])
    base_sizes = (100, 92, 84, 76, 68) if not narrow else (76, 70, 64, 58)
    for s in SCALES:
        f_title, lines = fit_lines(d, content["cover_title"], style["title"], tuple(int(z * s) for z in base_sizes), win, 4)
        f_sub, sub_lines = fit_lines(d, content.get("cover_sub", ""), "sans_bold", (int(42 * s), int(38 * s), int(34 * s)), win, 2)
        dia = int(min(win * 0.62, 460) * s)
        circ = circle_photo(cover_photo(content, dia, dia, style), dia, (255, 252, 246), 12, ang)
        th = text_block_height(lines, f_title) + 26 + text_block_height(sub_lines, f_sub, 0.4)
        total_h = th + 40 + circ.height + 70
        if total_h <= y1 - y0:
            break
    y = y0 + 70 + max(0, (y1 - y0 - total_h) // 2)
    tag = "오늘의 살림 노트"
    ftag = font("sans_bold", 30)
    tw = d.textlength(tag, font=ftag)
    d.rounded_rectangle((x0, y - 70, x0 + tw + 44, y - 70 + ftag.size + 22), 30, fill=style["accent"])
    d.text((x0 + 22, y - 70 + 8), tag, font=ftag, fill=(255, 255, 255) if not style["dark"] else (30, 30, 30))
    y = draw_lines(d, lines, f_title, x0, y, style["ink"], last_fill=style["accent"])
    y = draw_lines(d, sub_lines, f_sub, x0, y + 24, blend(style["ink"], style["paper"], 0.2), ratio=0.4)
    img.alpha_composite(circ, (int(x1 - circ.width + 20), int(y + 30)))
    for text, pos, ang, fill in zip((content.get("cover_stickers") or [])[:2],
                                    [(x0 + 190, y + 70 + circ.height * 0.45), (x0 + 250, y + 70 + circ.height * 0.85)],
                                    [-7, 6], [style["paper"], style["accent"]]):
        sticker(img, text, pos, ang, fill, style["ink"] if fill == style["paper"] else
                ((255, 255, 255) if not style["dark"] else (30, 30, 30)), 34)
    return img


def checklist_body(item, content, style, rnd, num, page, total):
    img = load_background(style)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = style["inner"]
    win = x1 - x0
    narrow = style.get("narrow")
    ang = rnd.choice([-5, 5])
    emoji = emoji_tile(item.get("emoji", ""), 64)
    for s in SCALES:
        dia = int((250 if not narrow else 200) * s)
        circ = circle_photo(photo_or_block(item, content, dia, dia, style), dia, (255, 252, 246), 10, ang)
        text_w = win - dia - 40
        base = (64, 58, 52, 46) if not narrow else (50, 46, 42)
        f_title, t_lines = fit_lines(d, item["title"], style["title"], tuple(int(z * s) for z in base), text_w, 3)
        f_body = font(style["body"], (38 if not narrow else 33) * s)
        b_h = int(body_height(d, item["body"], f_body, win, 0.5) + len(wrap(d, item["body"], f_body, win)) * 6)
        head_h = max(text_block_height(t_lines, f_title) + 70 + (70 if emoji else 0), circ.height - 30)
        total_h = head_h + 36 + b_h
        if total_h <= y1 - y0:
            break
    y = y0 + max(0, (y1 - y0 - total_h) // 2)
    chip = f"POINT {num}"
    fc = font("sans_bold", 28)
    cw = d.textlength(chip, font=fc)
    d.rounded_rectangle((x0, y, x0 + cw + 36, y + fc.size + 18), 24, fill=style["accent"])
    d.text((x0 + 18, y + 6), chip, font=fc, fill=(255, 255, 255) if not style["dark"] else (30, 30, 30))
    ty = y + fc.size + 34
    if emoji:
        img.alpha_composite(emoji, (x0, int(ty)))
        ty += emoji.height + 10
    draw_lines(d, t_lines, f_title, x0, ty, style["ink"])
    img.alpha_composite(circ, (int(x1 - circ.width + 14), int(y - 10)))
    by = y + head_h + 36
    # 줄 노트 느낌: 본문 줄마다 가는 밑줄
    lines = wrap(d, " ".join(item["body"].split()), f_body, win)
    for i in range(len(lines)):
        ly = by + i * int(f_body.size * 1.5) + f_body.size + 14
        d.line((x0, ly, x1, ly), fill=blend(style["ink"], style["paper"], 0.78), width=2)
    draw_body(img, d, item["body"], item.get("highlight"), f_body, x0, by, win, style, ratio=0.5)
    return img


# ---------------------------------------------------------------- 틀 3: 분할(위 사진, 아래 글)
def split_cover(content, style, rnd, total):
    img = load_background(style)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = style["inner"]
    win = x1 - x0
    ang = rnd.choice([-1.5, 1.5])
    for s in SCALES:
        ph_h = int(min(660, (y1 - y0) * 0.58) * s)
        tile = rounded_photo(cover_photo(content, win - 30, ph_h, style), win - 30, ph_h, 40, 10,
                             (255, 252, 246), ang, tape=blend(style["accent"], (255, 255, 255), 0.55))
        f_title, lines = fit_lines(d, content["cover_title"], style["title"], tuple(int(z * s) for z in (84, 76, 68, 60)), win, 3)
        f_sub, sub_lines = fit_lines(d, content.get("cover_sub", ""), "sans_reg", (int(38 * s), int(34 * s)), win, 2)
        total_h = tile.height - 60 + 30 + text_block_height(lines, f_title) + 22 + text_block_height(sub_lines, f_sub, 0.4)
        if total_h <= y1 - y0:
            break
    y = y0 + max(0, (y1 - y0 - total_h) // 2)
    paste_center(img, tile, (x0 + x1) / 2, y - 30)
    for text, pos, ang, fill in zip((content.get("cover_stickers") or [])[:2],
                                    [(x0 + 180, y + ph_h - 30), (x1 - 180, y + ph_h * 0.45)], [-6, 6],
                                    [style["accent"], style["paper"]]):
        sticker(img, text, pos, ang, fill, style["ink"] if fill == style["paper"] else
                ((255, 255, 255) if not style["dark"] else (30, 30, 30)), 34)
    y += tile.height - 60 + 30
    y = draw_lines(d, lines, f_title, x0, y, style["ink"], "center", win, last_fill=style["accent"])
    draw_lines(d, sub_lines, f_sub, x0, y + 20, blend(style["ink"], style["paper"], 0.25), "center", win, 0.4)
    return img


def split_body(item, content, style, rnd, num, page, total):
    img = load_background(style)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = style["inner"]
    win = x1 - x0
    ang = rnd.choice([-1.2, 1.2])
    emoji = emoji_tile(item.get("emoji", ""), 56)
    tx = x0 + (68 if emoji else 0)
    for s in SCALES:
        ph_h = int((y1 - y0) * 0.44 * s)
        tile = rounded_photo(photo_or_block(item, content, win - 30, ph_h, style), win - 30, ph_h, 38, 10,
                             (255, 252, 246), ang)
        f_title, t_lines = fit_lines(d, item["title"], style["title"], tuple(int(z * s) for z in (60, 54, 48)), win - (68 if emoji else 0), 2)
        f_body = font(style["body"], 38 * s)
        b_h = body_height(d, item["body"], f_body, win)
        total_h = tile.height - 40 + 26 + text_block_height(t_lines, f_title) + 22 + b_h
        if total_h <= y1 - y0:
            break
    y = y0 + max(0, (y1 - y0 - total_h) // 2)
    paste_center(img, tile, (x0 + x1) / 2, y - 20)
    # 번호 동그라미
    r = 46
    cx, cy = x0 + 36, y + 14
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=style["accent"], outline=(255, 252, 246), width=6)
    nf = font("sans_black", 44)
    nt = str(num)
    d.text((cx - d.textlength(nt, font=nf) / 2, cy - nf.size * 0.58), nt, font=nf,
           fill=(255, 255, 255) if not style["dark"] else (30, 30, 30))
    y += tile.height - 40 + 26
    if emoji:
        img.alpha_composite(emoji, (x0, int(y + (f_title.size - emoji.height) / 2 + 4)))
    y = draw_lines(d, t_lines, f_title, tx, y, style["ink"])
    draw_body(img, d, item["body"], item.get("highlight"), f_body, x0, y + 22, win, style)
    return img


# ---------------------------------------------------------------- 마지막 장
def closing_card(content, style, rnd, page, total):
    img = load_background(style)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = style["inner"]
    win = x1 - x0
    ph_w = int(min(win * 0.5, 360))
    tile = rounded_photo(cover_photo(content, ph_w, ph_w, style), ph_w, ph_w, 40, 10, (255, 252, 246), rnd.choice([-3, 3]),
                         tape=blend(style["accent"], (255, 255, 255), 0.55))
    msg = content.get("closing", "저장해 두고 장 볼 때 꺼내 보세요")
    f_msg, lines = fit_lines(d, msg, style["title"], (70, 64, 58, 52), win, 3)
    btn = "저장 & 팔로우"
    fb = font("sans_black", 44)
    bw = int(d.textlength(btn, font=fb)) + 100
    total_h = tile.height - 30 + 30 + text_block_height(lines, f_msg) + 40 + 100
    y = y0 + max(0, (y1 - y0 - total_h) // 2)
    paste_center(img, tile, (x0 + x1) / 2, y - 20)
    y += tile.height - 30 + 30
    y = draw_lines(d, lines, f_msg, x0, y, style["ink"], "center", win, last_fill=style["accent"])
    bx = (x0 + x1) / 2 - bw / 2
    d.rounded_rectangle((bx, y + 40, bx + bw, y + 140), 50, fill=style["accent"])
    d.text((bx + 50, y + 40 + (100 - fb.size) / 2 - 4), btn, font=fb,
           fill=(255, 255, 255) if not style["dark"] else (30, 30, 30))
    return img


LAYOUTS = {
    "polaroid": (polaroid_cover, polaroid_body),
    "checklist": (checklist_cover, checklist_body),
    "split": (split_cover, split_body),
}


def render_styled(content: dict, out_dir: Path, style: dict, seed_text: str = "") -> list:
    """photo(꽉 찬 사진) 외의 스타일로 카드를 그려 파일 경로 목록을 돌려준다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(f"{style['id']}-{seed_text}")
    if style["layout"] == "photo2":
        from photo_layouts import render_photo2

        return render_photo2(content, out_dir, style, rnd)
    cover_fn, body_fn = LAYOUTS[style["layout"]]
    slides = content["slides"]
    total = len(slides) + 2
    images = [cover_fn(content, style, rnd, total)]
    for i, s in enumerate(slides, 1):
        images.append(body_fn(s, content, style, rnd, i, i + 1, total))
    images.append(closing_card(content, style, rnd, total, total))
    paths = []
    for i, im in enumerate(images, 1):
        p = out_dir / f"{i:02d}.jpg"
        im.convert("RGB").save(p, "JPEG", quality=92)
        paths.append(p)
    return paths
