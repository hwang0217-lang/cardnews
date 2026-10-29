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
- cover_title: 표지 제목 (최대 22자). 이번 표지의 시선 끄는 방식: {hook}. 매번 "N가지"로만 끝내지 말고 방식을 지켜서 써
- cover_sub: 표지 부제 (최대 20자)
- cover_stickers: 표지 사진 위에 붙일 짧은 문구 2개 (각각 최대 12자, 예: "원룸 필수템만!")
- visual_style: 모든 사진이 공유할 분위기 한 줄 (영어, 예: "light oak countertop, warm morning light, cream and sage color palette")
- cover_image_prompt: 표지 사진에 찍힐 대상을 구체적으로 묘사한 영어 한두 문장
  (예: "a stack of three clear glass meal prep containers with snap-on lids on a light oak kitchen counter")
- cover_photo_query: 표지 배경 사진 검색어 (영어 2~4단어, 예: "cozy small kitchen")
- slides: 정확히 5개. 각각 title(최대 16자), body(최대 60자, 두 줄 이내),
  highlight(body 안에 글자 그대로 들어 있는 핵심 구절 하나, 최대 14자),
  emoji(그 장 제목에 어울리는 이모지 정확히 1개, 예: 🍳 🧽 🥄 🧊 💡),
  image_prompt(그 장이 말하는 실제 물건 하나를 구체적으로 묘사한 영어 한두 문장. 재질, 색, 모양, 놓인 장소를 적고 "사람", "손"은 쓰지 않기),
  photo_query(그 장 내용과 어울리는 사진 검색어, 영어 2~4단어)
- image_prompt는 현실에 흔한 평범한 제품 모습으로 쓰고, 화려하거나 비현실적인 재질(금색, 네온 등)은 쓰지 않기
- 사진 검색어는 주방, 식재료, 조리도구, 식탁 같은 물건·공간 위주로 쓰고 사람 얼굴이 나올 법한 검색어와 브랜드명은 피해
- closing: 마지막 장 문구 (최대 30자, 저장/팔로우 유도)
- caption: 인스타 설명글. 첫 줄은 사람들이 검색할 만한 핵심 단어(예: 자취, 원룸, 주방, 냄새, 정리)가 들어간 한 문장,
  3~5줄, 중간에 "저장해두면 나중에 편해요"처럼 저장을 부르는 한 줄, 마지막은 독자가 댓글로 답하기 쉬운 짧은 질문.
  내용에 어울리는 이모지를 전체에서 2~4개만 자연스럽게 섞는다 (예: 🍳 📌 💡). 줄마다 붙이거나 같은 이모지를 반복하지 않는다.
- hashtags: 정확히 5개, 모두 # 로 시작, 띄어쓰기 없이. 넓은 태그 2개(예: #자취, #원룸) + 이 주제만의 구체 태그 3개(예: #주방기름때)
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
                        "emoji": {"type": "string"},
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


HOOKS = (
    "숫자 + 손해 피하기 (예: 이거 모르면 매달 3만 원 새요)",
    "독자에게 직접 던지는 질문 (예: 냉동실 아직도 이렇게 써요?)",
    "흔한 오해 뒤집기 (예: 밀폐용기 이렇게 쓰면 오히려 냄새나요)",
    "전과 후 대비 (예: 정리 전 vs 정리 후, 딱 하나 바꿨어요)",
    "버려도 되는 것 · 꼭 필요한 것 (예: 사지 마세요, 이것만 있으면 돼요)",
    "한 줄 결론부터 (예: 결론: 프라이팬은 하나면 충분해요)",
)


def pick_hook(topic: str) -> str:
    return HOOKS[sum(map(ord, topic)) % len(HOOKS)]


def write_content(topic: str, tries: int = 4) -> dict:
    client = anthropic.Anthropic()
    last_error = None
    for attempt in range(tries):
        prompt = PROMPT.format(topic=topic, hook=pick_hook(topic))
        prompt += ("\n\n주제에 숫자(예: 7가지)가 있어도 slides는 반드시 5개로 구성하고, 필요하면 항목을 묶거나 대표 항목만 골라줘."
                   "\nslides, closing, caption, hashtags를 빠뜨리지 말고 모든 항목을 채워서 한 번에 제출해줘.")
        if last_error:
            prompt += f"\n(이전 시도 실패 이유: {last_error})"
        msg = client.messages.create(
            model=MODEL,
            max_tokens=4500,  # 항목이 많아서 짧으면 중간에 잘려 slides가 빠져요
            system=SYSTEM,
            tools=[TOOL],
            messages=[{"role": "user", "content": prompt}],
        )
        if msg.stop_reason == "max_tokens":
            print(f"글 생성이 길이 제한으로 잘렸어요 (시도 {attempt + 1}/{tries})")
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
        # 이모지는 한 개만 쓰고, 이상하게 길면 버린다 (없어도 발행에는 문제없음)
        em = (s.get("emoji") or "").strip()
        s["emoji"] = em if 0 < len(em) <= 8 and not any(c.isascii() and c.isalnum() for c in em) else ""
    d["hashtags"] = [h if h.startswith("#") else f"#{h}" for h in d["hashtags"]][:5]


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


