"""매일 한 번 실행: 주제 선택 → 글 → 이미지 → (저장소에 올려 공개 URL 확보) → 인스타 업로드."""
import json
import os
import sys
import time
from pathlib import Path

from publish import publish_carousel
from render import render_all
from write_content import suggest_topics, write_content

ROOT = Path(__file__).parent
TOPICS = json.loads((ROOT / "topics.json").read_text(encoding="utf-8"))
STATE_FILE = ROOT / "state.json"
DRY_RUN = os.environ.get("DRY_RUN") == "1"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"posted": []}


def pick_topic(state: dict) -> str:
    """미리 만든 주제 → 이전에 AI가 만든 주제 순으로 쓰고, 다 떨어지면 AI가 새 주제를 만든다."""
    done = {p["topic"] for p in state["posted"]}
    extra = state.setdefault("extra_topics", [])
    for t in TOPICS + extra:
        if t not in done:
            return t
    new = suggest_topics(list(done) + TOPICS + extra)
    if not new:
        raise SystemExit("새 주제를 만들지 못했어요. 잠시 뒤 다시 시도돼요.")
    print(f"주제 목록이 떨어져서 AI가 새 주제 {len(new)}개를 만들었어요.")
    extra.extend(new)
    return new[0]


def public_urls(paths: list[Path]) -> list[str]:
    """이미지를 이 저장소에 커밋해 두면 raw.githubusercontent.com 주소로 열려요."""
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    return [
        f"https://raw.githubusercontent.com/{repo}/{branch}/cardnews/{p.relative_to(ROOT).as_posix()}"
        for p in paths
    ]


def wait_for_urls(urls: list[str], tries: int = 20) -> None:
    import requests

    for u in urls:
        for _ in range(tries):
            if requests.head(u, timeout=15).status_code == 200:
                break
            time.sleep(3)
        else:
            raise RuntimeError(f"이미지 주소가 열리지 않아요: {u}")


def commit_images() -> None:
    os.system("git config user.name 'cardnews-bot'")
    os.system("git config user.email 'cardnews-bot@users.noreply.github.com'")
    os.system("git add cardnews/images")
    os.system("git diff --cached --quiet || git commit -m 'add card images'")
    if os.system("git push") != 0:
        raise RuntimeError("이미지 push 실패")


def save_state(state: dict, topic: str, media_id: str) -> None:
    state["posted"].append(
        {"topic": topic, "media_id": media_id, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    )
    state["posted"] = state["posted"][-400:]
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    state = load_state()
    topic = pick_topic(state)
    print(f"주제: {topic}")

    content = write_content(topic)
    ai_note = "※ 이미지는 AI로 생성한 참고용이에요." if os.environ.get("GEMINI_API_KEY") else ""
    caption = "\n\n".join(p for p in (content["caption"].strip(), ai_note, " ".join(content["hashtags"])) if p)

    slug = time.strftime("%Y%m%d-%H%M")
    paths = render_all(content, ROOT / "images" / slug)
    print(f"이미지 {len(paths)}장 생성")

    if DRY_RUN:
        print("DRY_RUN: 업로드하지 않고 종료")
        print(caption)
        return

    commit_images()
    urls = public_urls(paths)
    wait_for_urls(urls)
    media_id = publish_carousel(urls, caption)
    print(f"업로드 완료: {media_id}")
    save_state(state, topic, media_id)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"실패: {e}", file=sys.stderr)
        raise
