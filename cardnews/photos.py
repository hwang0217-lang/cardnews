"""무료 스톡 사진 사이트에서 검색어에 맞는 사진을 가져온다. 키가 없거나 실패하면 None.

Pixabay(PIXABAY_API_KEY)를 우선 쓰고, 없으면 Pexels(PEXELS_API_KEY)를 쓴다.
"""
import io
import os
import random

import requests
from PIL import Image

_used: set = set()


def _download(url: str) -> Image.Image:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def _pixabay(query: str, orientation: str, key: str):
    r = requests.get(
        "https://pixabay.com/api/",
        params={
            "key": key,
            "q": query[:100],
            "image_type": "photo",
            "orientation": orientation,  # horizontal | vertical
            "safesearch": "true",
            "per_page": 20,
            "order": "popular",
        },
        timeout=30,
    )
    r.raise_for_status()
    hits = [h for h in r.json().get("hits", []) if ("px", h["id"]) not in _used]
    if not hits:
        return None
    pick = random.choice(hits[:12])
    _used.add(("px", pick["id"]))
    return _download(pick["largeImageURL"])


def _pexels(query: str, orientation: str, key: str):
    r = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": key},
        params={
            "query": query,
            "orientation": "landscape" if orientation == "horizontal" else "portrait",
            "per_page": 15,
        },
        timeout=30,
    )
    r.raise_for_status()
    photos = [p for p in r.json().get("photos", []) if ("pe", p["id"]) not in _used]
    if not photos:
        return None
    pick = random.choice(photos[:10])
    _used.add(("pe", pick["id"]))
    return _download(pick["src"]["large2x"])


def get_photo(query: str, orientation: str = "vertical"):
    if not query:
        return None
    try:
        if os.environ.get("PIXABAY_API_KEY"):
            return _pixabay(query, orientation, os.environ["PIXABAY_API_KEY"])
        if os.environ.get("PEXELS_API_KEY"):
            return _pexels(query, orientation, os.environ["PEXELS_API_KEY"])
    except Exception as e:  # 사진 실패가 전체 발행을 막지 않게 한다
        print(f"사진 가져오기 실패({query}): {e}")
    return None
