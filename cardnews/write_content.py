"""주제 하나를 받아 카드뉴스 글(JSON)을 Claude로 만든다."""
import json
import os
import re

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

SYSTEM = """너는 '원룸 자취생 주방템' 인스타그램 계정의 카드뉴스 작가야.
독자는 처음 자취를 시작한 20대다. 쉬운 말, 짧은 문장, 친근한 말투(해요체)로 쓴다.
확인되지 않은 수치, 가격, 효능을 단정적으로 쓰지 않는다. 특정 브랜드명도 쓰지 않는다.
의학적 효능이나 과장 표현은 쓰지 않는다. 반드시 JSON만 출력한다."""

PROMPT = """주제: {topic}

아래 JSON 형식으로만 답해줘.
{{
  "cover_title": "표지 제목 (최대 22자, 숫자나 질문으로 시선 끌기)",
  "cover_sub": "표지 부제 (최대 20자)",
  "slides": [
    {{"title": "소제목 (최대 16자)", "body": "설명 (최대 60자, 두 줄 이내)"}}
  ],
  "closing": "마지막 장 문구 (최대 30자, 저장/팔로우 유도)",
  "caption": "인스타 설명글 (첫 줄은 핵심 한 문장, 3~5줄, 마지막은 독자에게 묻는 질문)",
  "hashtags": ["#태그", "..."]
}}
조건:
- slides는 정확히 5개
- hashtags는 8개, 모두 # 로 시작, 띄어쓰기 없이
- 한국어로 작성"""


def write_content(topic: str) -> dict:
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=SYSTEM,
        messages=[{"role": "user", "content": PROMPT.format(topic=topic)}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text")
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError(f"JSON을 찾지 못했어요: {text[:200]}")
    data = json.loads(match.group(0))
    validate(data)
    return data


def validate(d: dict) -> None:
    for key in ("cover_title", "cover_sub", "slides", "closing", "caption", "hashtags"):
        if key not in d:
            raise ValueError(f"'{key}' 항목이 없어요")
    if len(d["slides"]) != 5:
        raise ValueError("slides는 5개여야 해요")
    for s in d["slides"]:
        if not s.get("title") or not s.get("body"):
            raise ValueError("slide에 title/body가 비어 있어요")


if __name__ == "__main__":
    import sys

    print(json.dumps(write_content(sys.argv[1]), ensure_ascii=False, indent=2))
