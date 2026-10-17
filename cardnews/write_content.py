"""주제 하나를 받아 카드뉴스 글을 Claude로 만든다. (도구 호출로 형식을 강제해 JSON 오류를 막는다)"""
import os

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

SYSTEM = """너는 '원룸 자취생 주방템' 인스타그램 계정의 카드뉴스 작가야.
독자는 처음 자취를 시작한 20대다. 쉬운 말, 짧은 문장, 친근한 말투(해요체)로 쓴다.
확인되지 않은 수치, 가격, 효능을 단정적으로 쓰지 않는다. 특정 브랜드명도 쓰지 않는다.
의학적 효능이나 과장 표현은 쓰지 않는다."""

PROMPT = """주제: {topic}

submit_cardnews 도구로 카드뉴스 내용을 제출해줘.
- cover_title: 표지 제목 (최대 22자, 숫자나 질문으로 시선 끌기)
- cover_sub: 표지 부제 (최대 20자)
- slides: 정확히 5개. 각각 title(최대 16자), body(최대 60자, 두 줄 이내)
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
            "slides": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["title", "body"],
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
            tool_choice={"type": "tool", "name": "submit_cardnews"},
            messages=[{"role": "user", "content": PROMPT.format(topic=topic)}],
        )
        for block in msg.content:
            if block.type == "tool_use":
                data = block.input
                try:
                    validate(data)
                    return data
                except ValueError as e:
                    last_error = e
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


if __name__ == "__main__":
    import json
    import sys

    print(json.dumps(write_content(sys.argv[1]), ensure_ascii=False, indent=2))
