"""주제 하나를 받아 카드뉴스 글을 Claude로 만든다. (도구 호출로 형식을 강제해 JSON 오류를 막는다)"""
import os

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

SYSTEM = """너는 '원룸 자취생 주방템' 인스타그램 계정의 카드뉴스 작가야.
독자는 처음 자취를 시작한 20대다. 쉬운 말, 짧은 문장, 친근한 말투(해요체)로 쓴다.
확인되지 않은 수치, 가격, 효능을 단정적으로 쓰지 않는다. 특정 브랜드명도 쓰지 않는다.
의학적 효능이나 과장 표현은 쓰지 않는다."""

PROMPT = """주제: {topic}

반드시 submit_cardnews 도구를 호출해서 카드뉴스 내용을 제출해줘. 글로 답하지 말고 도구만 써.
- cover_title: 표지 제목 (최대 22자, 숫자나 질문으로 시선 끌기)
- cover_sub: 표지 부제 (최대 20자)
- cover_stickers: 표지 사진 위에 붙일 짧은 문구 2개 (각각 최대 12자, 예: "원룸 필수템만!")
- visual_style: 모든 사진이 공유할 분위기 한 줄 (영어, 예: "light oak countertop, warm morning light, cream and sage color palette")
- cover_image_prompt: 표지 사진에 찍힐 대상을 구체적으로 묘사한 영어 한두 문장
  (예: "a stack of three clear glass meal prep containers with snap-on lids on a light oak kitchen counter")
- cover_photo_query: 표지 배경 사진 검색어 (영어 2~4단어, 예: "cozy small kitchen")
- slides: 정확히 5개. 각각 title(최대 16자), body(최대 60자, 두 줄 이내),
  highlight(body 안에 글자 그대로 들어 있는 핵심 구절 하나, 최대 14자),
  image_prompt(그 장이 말하는 실제 물건 하나를 구체적으로 묘사한 영어 한두 문장. 재질, 색, 모양, 놓인 장소를 적고 "사람", "손"은 쓰지 않기),
  photo_query(그 장 내용과 어울리는 사진 검색어, 영어 2~4단어)
- image_prompt는 현실에 흔한 평범한 제품 모습으로 쓰고, 화려하거나 비현실적인 재질(금색, 네온 등)은 쓰지 않기
- 사진 검색어는 주방, 식재료, 조리도구, 식탁 같은 물건·공간 위주로 쓰고 사람 얼굴이 나올 법한 검색어와 브랜드명은 피해
- closing: 마지막 장 문구 (최대 30자, 저장/팔로우 유도)
- caption: 인스타 설명글 (첫 줄은 핵심 한 문장, 3~5줄, 마지막은 독자에게 묻는 질문)
- hashtags: 8개, 모두 # 로 시작, 띄어쓰기 없이
한국어로 작성해줘."""

TOOL = {
    "name": "submit_cardnews",
    "description": "완성된 카드뉴스 내용을 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "cover_title": {"type": "string"},
            "cover_sub": {"type": "string"},
            "cover_stickers": {"type": "array", "items": {"type": "string"}},
            "visual_style": {"type": "string"},
            "cover_image_prompt": {"type": "string"},
            "cover_photo_query": {"type": "string"},
            "slides": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "highlight": {"type": "string"},
                        "image_prompt": {"type": "string"},
                        "photo_query": {"type": "string"},
                    },
                    "required": ["title", "body", "image_prompt", "photo_query"],
                },
            },
            "closing": {"type": "string"},
            "caption": {"type": "string"},
            "hashtags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["cover_title", "cover_sub", "slides", "closing", "caption", "hashtags"],
    },
}


def write_content(topic: str, tries: int = 3) -> dict:
    client = anthropic.Anthropic()
    last_error = None
    for _ in range(tries):
        msg = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM,
            tools=[TOOL],
            messages=[{"role": "user", "content": PROMPT.format(topic=topic)}],
        )
        used_tool = False
        for block in msg.content:
            if block.type == "tool_use":
                used_tool = True
                data = block.input
                try:
                    validate(data)
                    return data
                except ValueError as e:
                    last_error = e
        if not used_tool:
            last_error = ValueError("도구를 호출하지 않고 글로 답했어요")
    raise ValueError(f"글 생성에 {tries}번 실패했어요: {last_error}")


def validate(d: dict) -> None:
    for key in ("cover_title", "cover_sub", "slides", "closing", "caption", "hashtags"):
        if key not in d:
            raise ValueError(f"'{key}' 항목이 없어요")
    if len(d["slides"]) != 5:
        raise ValueError("slides는 5개여야 해요")
    for s in d["slides"]:
        if not s.get("title") or not s.get("body"):
            raise ValueError("slide에 title/body가 비어 있어요")
    d["hashtags"] = [h if h.startswith("#") else f"#{h}" for h in d["hashtags"]]


TOPIC_TOOL = {
    "name": "submit_topics",
    "description": "새 카드뉴스 주제 목록을 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {"topics": {"type": "array", "items": {"type": "string"}}},
        "required": ["topics"],
    },
}


def _norm(s: str) -> str:
    return "".join(s.split())


def suggest_topics(done: list, n: int = 12) -> list:
    """이미 다룬 주제와 겹치지 않는 새 주제를 AI가 만든다 (주제 목록이 떨어졌을 때)."""
    recent = "\n".join(f"- {t}" for t in done[-80:])
    prompt = (
        f"'원룸 자취생 주방템' 카드뉴스 주제를 {n}개 새로 제안해줘.\n"
        "조건: 원룸 자취생이 궁금해할 주방·살림·요리·정리·청소·장보기·절약 주제, 목록·비교·체크리스트로 만들기 쉬운 제목, "
        "특정 브랜드명 금지, 건강 효능 단정 금지, 25자 안팎.\n"
        f"아래 주제와 같거나 비슷한 것은 제외해줘.\n{recent}\n\nsubmit_topics 도구로만 제출해줘."
    )
    client = anthropic.Anthropic()
    taken = {_norm(t) for t in done}
    for _ in range(3):
        msg = client.messages.create(
            model=MODEL, max_tokens=1200, system=SYSTEM, tools=[TOPIC_TOOL],
            messages=[{"role": "user", "content": prompt}],
        )
        for b in msg.content:
            if b.type == "tool_use":
                fresh = []
                for t in b.input.get("topics", []):
                    t = " ".join(str(t).split())
                    if t and _norm(t) not in taken:
                        taken.add(_norm(t))
                        fresh.append(t)
                if fresh:
                    return fresh
    return []


if __name__ == "__main__":
    import json
    import sys

    print(json.dumps(write_content(sys.argv[1]), ensure_ascii=False, indent=2))
