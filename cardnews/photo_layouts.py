"""사진 위주의 카드뉴스.

AI 상품 사진을 크게 깔고, 스타일마다 틀(테두리·매트·둥근 액자·아래 띠), 글 위치(아래·위·가운데·왼쪽·패널),
글꼴, 포인트 색, 강조 방식(형광펜·밑줄·글자색)만 바꿔서 매번 다르게 보이게 한다.
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from layouts import (SCALES, W, H, blend, body_height, crop_to, draw_body, draw_lines, emoji_tile, fit_lines,
                     font, get_photo_image, sticker, text_block_height)

MX = 76  # 글자 좌우 여백
DARK = (27, 26, 23)


def _lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _on(color):
    """색 위에 올릴 글자색(밝은 색이면 어두운 글자)."""
    return DARK if _lum(color) > 150 else (255, 255, 255)


def _d0():
    return ImageDraw.Draw(Image.new("RGB", (10, 10)))


# ---------------------------------------------------------------- 사진과 틀
def photo_of(content, item=None):
    if item is None:
        return get_photo_image(content.get("cover_image_prompt", ""), content.get("cover_photo_query", ""),
                               content.get("visual_style", ""))
    return get_photo_image(item.get("image_prompt", ""), item.get("photo_query", ""), content.get("visual_style", ""))


def fallback_photo(style, w, h):
    top, bottom = blend((60, 56, 52), style["accent"], 0.25), (24, 22, 20)
    g = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        g.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return g.resize((w, h))


def photo_rect(style, band_h=0):
    frame = style.get("frame", "none")
    if frame == "white":
        return (46, 46, W - 46, H - 46), 0
    if frame == "rounded":
        return (42, 42, W - 42, H - 42), 46
    if frame == "band":
        return (0, 0, W, H - band_h), 0
    return (0, 0, W, H), 0


def compose_base(style, photo, rect, radius):
    canvas = style.get("canvas", (16, 16, 16))
    base = Image.new("RGBA", (W, H), canvas + (255,))
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    ph = crop_to(photo, w, h) if photo is not None else fallback_photo(style, w, h)
    ph = ph.convert("RGBA")
    if radius:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
        base.paste(ph, (x0, y0), mask)
    else:
        base.paste(ph, (x0, y0))
    return base


def gradient(rect, direction, stops):
    """rect 안에서만 어두워지는 그림자. direction: v(위→아래) 또는 h(왼→오)."""
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    n = h if direction == "v" else w
    line = Image.new("L", (1, n) if direction == "v" else (n, 1))
    for i in range(n):
        t = i / max(1, n - 1)
        a = stops[-1][1]
        for (p0, a0), (p1, a1) in zip(stops, stops[1:]):
            if p0 <= t <= p1:
                a = a0 + (a1 - a0) * (t - p0) / ((p1 - p0) or 1)
                break
        line.putpixel((0, i) if direction == "v" else (i, 0), int(a))
    mask = line.resize((w, h))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    black = Image.new("RGBA", (w, h), (8, 8, 8, 255))
    black.putalpha(mask)
    ov.paste(black, (x0, y0))
    return ov


def even_dim(rect, alpha):
    x0, y0, x1, y1 = rect
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov.paste(Image.new("RGBA", (x1 - x0, y1 - y0), (8, 8, 8, alpha)), (x0, y0))
    return ov


# ---------------------------------------------------------------- 글 덩어리
class Part:
    def __init__(self, h, fn):
        self.h, self.fn = h, fn


def stack_height(parts, gap):
    return sum(p.h for p in parts) + gap * (len(parts) - 1)


def draw_stack(img, d, parts, x, y, w, align, gap):
    for p in parts:
        p.fn(img, d, x, y, w, align)
        y += p.h + gap


def label_part(style, text):
    kind, acc = style["label"], style["accent"]
    f = font("sans_bold", 28)
    tw = _d0().textlength(text, font=f)
    on = _on(acc)
    if kind == "line":
        h = f.size + 18

        def draw(img, d, x, y, w, align):
            lx = x if align == "left" else x + (w - tw) / 2
            d.text((lx, y), text, font=f, fill=acc)
            d.line((lx, y + f.size + 12, lx + 64, y + f.size + 12), fill=acc, width=4)
        return Part(h, draw)
    h = f.size + (24 if kind == "pill" else 20)
    radius = h // 2 if kind == "pill" else 6

    def draw(img, d, x, y, w, align):
        bw = tw + 44
        bx = x if align == "left" else x + (w - bw) / 2
        d.rounded_rectangle((bx, y, bx + bw, y + h), radius, fill=acc)
        d.text((bx + 22, y + (h - f.size) / 2 - 3), text, font=f, fill=on)
    return Part(h, draw)


def title_part(d0, text, key, sizes, w, max_lines, ink, accent, accent_last=False, emoji=None, align="left"):
    f, lines = fit_lines(d0, text, key, sizes, w - (72 if (emoji and align == "left") else 0), max_lines)
    th = text_block_height(lines, f)
    top_emoji = emoji is not None and align == "center"
    h = th + (emoji.height + 14 if top_emoji else 0)

    def draw(img, d, x, y, w2, al):
        if top_emoji:
            img.alpha_composite(emoji, (int(x + (w2 - emoji.width) / 2), int(y)))
            y += emoji.height + 14
        tx = x
        if emoji and al == "left":
            img.alpha_composite(emoji, (int(x), int(y + (f.size - emoji.height) / 2 + 4)))
            tx = x + 72
        draw_lines(d, lines, f, tx, y, ink, al, w2 - (72 if (emoji and al == "left") else 0),
                   last_fill=accent if accent_last else None)
    return Part(h, draw), f


def text_part(d0, text, f, w, h_text_ratio=0.5, fn=None, h=None):
    return Part(h if h is not None else int(body_height(d0, text, f, w, h_text_ratio)), fn)


# ---------------------------------------------------------------- 한 장 그리기
def region_limits(style, kind):
    """글 덩어리가 차지할 수 있는 최대 높이."""
    pos = style["text_pos"]
    if pos in ("bottom", "top"):
        return 640 if kind != "closing" else 760
    if pos == "center":
        return 760
    if pos == "left":
        return 900
    if pos == "panel":
        return 640
    return 600  # band


def text_width(style, kind):
    pos = style["text_pos"]
    if kind == "closing" or pos == "center":
        return W - 2 * (MX + 20)
    if pos == "left":
        return 640
    if pos == "panel":
        return W - 2 * (MX + 34)
    if style.get("frame") in ("white", "rounded"):
        return W - 2 * (MX + 20)
    return W - 2 * MX


def build_slide(style, photo, make_parts, kind, page_text="", stickers=None, hint=False):
    """make_parts(scale, width, ink) -> (parts, gap). 크기를 줄여 가며 들어갈 때까지 시도한다."""
    pos = style["text_pos"]
    w = text_width(style, kind)
    panel = style.get("panel")
    ink = (27, 26, 23) if panel == "light" else style["ink"]
    if kind == "closing":
        ink = (255, 255, 255)
    for s in SCALES:
        parts, gap = make_parts(s, w, ink)
        h = stack_height(parts, gap)
        if h <= region_limits(style, kind):
            break
    align = style["align"] if kind != "closing" else "center"

    band_h = 0
    if pos == "band" and kind != "closing":
        band_h = min(int(H * 0.5), max(380, h + 120))
    rect, radius = photo_rect(style, band_h if kind != "closing" else 0)
    base = compose_base(style, photo, rect, radius)
    x0, y0, x1, y1 = rect

    # ---- 그림자(글자가 잘 읽히게)
    if kind == "closing":
        base.alpha_composite(even_dim(rect, 175))
    elif pos == "bottom":
        base.alpha_composite(gradient(rect, "v", [(0, 40), (0.30, 0), (0.55, 70), (0.78, 175), (1, 235)]))
    elif pos == "top":
        base.alpha_composite(gradient(rect, "v", [(0, 225), (0.30, 150), (0.55, 0), (0.8, 0), (1, 70)]))
    elif pos == "center":
        base.alpha_composite(even_dim(rect, 125))
    elif pos == "left":
        base.alpha_composite(gradient(rect, "h", [(0, 215), (0.52, 150), (0.82, 25), (1, 0)]))
        base.alpha_composite(gradient(rect, "v", [(0, 60), (0.3, 0), (0.7, 0), (1, 70)]))
    elif pos == "panel":
        base.alpha_composite(gradient(rect, "v", [(0, 30), (0.4, 0), (0.7, 20), (1, 90)]))
    d = ImageDraw.Draw(base)

    # ---- 틀 장식
    if style.get("frame") == "inset":
        d.rectangle((30, 30, W - 30, H - 30), outline=style.get("frame_color", (255, 255, 255)), width=5)
    if pos == "band" and kind != "closing":
        d.rectangle((0, H - band_h, W, H), fill=style.get("canvas", (16, 16, 16)))
        d.rectangle((0, H - band_h, W, H - band_h + 8), fill=style["accent"])

    # ---- 글 위치
    if kind == "closing" or pos == "center":
        x = (W - w) / 2
        y = y0 + (y1 - y0 - h) / 2
        al = "center"
    elif pos == "left":
        x = MX
        y = y0 + (y1 - y0 - h) / 2 + 40
        al = "left"
    elif pos == "top":
        x = (MX + 20) if style.get("frame") in ("white", "rounded") else MX
        y = y0 + 96
        al = align
    elif pos == "panel":
        pad = 40
        px0, px1 = MX - 10, W - MX + 10
        py1 = H - 70
        py0 = py1 - h - pad * 2
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fill = (255, 255, 255, 236) if panel == "light" else (14, 18, 30, 214)
        ImageDraw.Draw(ov).rounded_rectangle((px0, py0, px1, py1), 38, fill=fill)
        ov = shadowed_overlay(ov) if panel == "light" else ov
        base.alpha_composite(ov)
        d = ImageDraw.Draw(base)
        x, y, al = px0 + pad + 6, py0 + pad, align
        w = (px1 - px0) - 2 * (pad + 6)
    elif pos == "band":
        x, y, al = MX, H - band_h + 8 + (band_h - 8 - h) / 2, align
    else:  # bottom
        x = (MX + 20) if style.get("frame") in ("white", "rounded") else MX
        y = y1 - (170 if kind == "cover" else 130) - h
        al = align
    draw_stack(base, d, parts, x, y, w, al, gap)

    if page_text and style.get("page"):
        pf = font("sans_reg", 28)
        d.text((W - 70 - d.textlength(page_text, font=pf), 74), page_text, font=pf, fill=(255, 255, 255))
    for st in (stickers or []):
        sticker(base, *st)
    if hint:
        hf = font("sans_bold", 30)
        d.text((MX, H - 92), "옆으로 넘겨서 확인  →", font=hf, fill=style["accent"] if _lum(style["accent"]) > 80 else (255, 255, 255))
    return base.convert("RGB")


def shadowed_overlay(ov):
    sh = ov.filter(ImageFilter.GaussianBlur(14))
    sh = Image.merge("RGBA", (Image.new("L", ov.size, 0),) * 3 + (sh.split()[3].point(lambda v: v // 3),))
    sh.alpha_composite(ov)
    return sh


# ---------------------------------------------------------------- 표지 · 본문 · 마지막 장
def cover_image(content, style, rnd, total):
    d0 = _d0()
    pos = style["text_pos"]
    accent = style["accent"]
    title_key = style["title"]

    def make_parts(s, w, ink):
        parts = [label_part(style, "원룸 자취 주방템")]
        tp, _ = title_part(d0, content["cover_title"], title_key, tuple(int(z * s) for z in (96, 88, 80, 72, 64)), w, 4,
                           ink, accent, True, None, style["align"])
        parts.append(tp)
        sub = content.get("cover_sub", "")
        if sub:
            f, lines = fit_lines(d0, sub, "sans_bold", (int(42 * s), int(38 * s), int(34 * s)), w, 2)
            parts.append(Part(text_block_height(lines, f, 0.4),
                              lambda img, d, x, y, w2, al, f=f, lines=lines: draw_lines(
                                  d, lines, f, x, y, blend(ink, (0, 0, 0), 0.12) if ink != DARK else ink, al, w2, 0.4)))
        return parts, 26 if title_key != "serif" else 30

    # 스티커 위치는 글이 없는 쪽에 둔다
    top_area = pos in ("bottom", "panel", "band", "left", "center")
    ys = (330, 470) if top_area else (H - 470, H - 340)
    xs = (250, W - 260)
    texts = (content.get("cover_stickers") or [])[:2]
    stickers = [(t, (xs[i], ys[i]), [-6, 6][i], [accent, (255, 252, 246)][i],
                 _on(accent) if i == 0 else DARK, 38) for i, t in enumerate(texts)]
    return build_slide(style, photo_of(content), make_parts, "cover", f"1 / {total}", stickers,
                       hint=pos not in ("panel", "band"))  # 패널·띠 스타일은 아래가 글 영역이라 안내 문구를 빼요


def body_image(item, content, style, rnd, num, page, total):
    d0 = _d0()
    accent = style["accent"]
    emoji = emoji_tile(item.get("emoji", ""), 60)
    label = f"POINT {num}" if style["label"] != "line" else f"POINT {num:02d}"

    def make_parts(s, w, ink):
        parts = [label_part(style, label)]
        tp, _ = title_part(d0, item["title"], style["title"], tuple(int(z * s) for z in (68, 62, 56, 50)), w, 2, ink, accent,
                           False, emoji, style["align"])
        parts.append(tp)
        bf = font("sans_reg", 40 * s)
        hl_ink = DARK if _lum(accent) > 110 else (255, 255, 255)
        bh = int(body_height(d0, item["body"], bf, w, 0.5)) + 6

        def draw_b(img, d, x, y, w2, al, bf=bf, ink=ink, hl_ink=hl_ink):
            draw_body(img, d, item["body"], item.get("highlight"), bf, x, y, w2, style, 0.5, ink, style["marker"],
                      al == "center", hl_ink)
        parts.append(Part(bh, draw_b))
        return parts, 24

    return build_slide(style, photo_of(content, item), make_parts, "body", f"{page} / {total}")


def closing_image(content, style, rnd, page, total):
    d0 = _d0()
    accent = style["accent"]
    msg = content.get("closing", "저장해 두고 장 볼 때 꺼내 보세요")

    def make_parts(s, w, ink):
        tp, _ = title_part(d0, msg, style["title"], tuple(int(z * s) for z in (78, 70, 62, 54)), w, 3, (255, 255, 255), accent,
                           True, None, "center")
        btn = "저장 & 팔로우"
        fb = font("sans_black", 46)
        bw = int(d0.textlength(btn, font=fb)) + 100

        def draw_btn(img, d, x, y, w2, al):
            bx = x + (w2 - bw) / 2
            d.rounded_rectangle((bx, y, bx + bw, y + 100), 50, fill=accent)
            d.text((bx + 50, y + (100 - fb.size) / 2 - 4), btn, font=fb, fill=_on(accent))
        return [tp, Part(100, draw_btn)], 40

    return build_slide(style, photo_of(content), make_parts, "closing")


def render_photo2(content: dict, out_dir: Path, style: dict, rnd: random.Random) -> list:
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = content["slides"]
    total = len(slides) + 2
    images = [cover_image(content, style, rnd, total)]
    for i, s in enumerate(slides, 1):
        images.append(body_image(s, content, style, rnd, i, i + 1, total))
    images.append(closing_image(content, style, rnd, total, total))
    paths = []
    for i, im in enumerate(images, 1):
        p = out_dir / f"{i:02d}.jpg"
        im.save(p, "JPEG", quality=92)
        paths.append(p)
    return paths
