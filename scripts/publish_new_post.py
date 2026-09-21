"""
티스토리 RSS를 확인해서 새 글이 있으면 스레드에 자동으로 발행하는 스크립트.

동작 방식:
1. RSS_URL(환경변수)에서 최신 글 목록을 가져온다.
2. state/last_published.txt 에 저장된 "마지막으로 발행한 글 주소"와 비교한다.
3. 새 글이 있으면 -> 스레드용 문구를 만들어 Threads API로 발행한다.
4. 발행에 성공하면 state/last_published.txt 를 최신 글 주소로 갱신한다.

여러 개의 새 글이 쌓여있어도, 이 스크립트는 "가장 최신 글 1개"만 발행한다.
(한 번에 여러 개를 올리면 스팸처럼 보일 수 있어서, 1시간마다 실행하며 하나씩 처리하는 걸 권장)
"""

import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

STATE_FILE = "state/last_published.txt"


def get_env(name, required=True, default=None):
    value = os.environ.get(name, default)
    if required and not value:
        print(f"[오류] 환경변수 {name} 가 설정되지 않았습니다.")
        sys.exit(1)
    return value


def fetch_latest_rss_item(rss_url):
    """RSS 피드에서 가장 최신 글의 (제목, 링크)를 반환한다."""
    req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read()

    root = ET.fromstring(raw)
    # 표준 RSS 2.0 구조: rss > channel > item (여러 개, 최신순)
    channel = root.find("channel")
    if channel is None:
        print("[오류] RSS 형식을 해석할 수 없습니다 (channel 태그 없음).")
        sys.exit(1)

    items = channel.findall("item")
    if not items:
        print("[오류] RSS에 글이 하나도 없습니다.")
        sys.exit(1)

    first = items[0]
    title = first.findtext("title", default="").strip()
    link = first.findtext("link", default="").strip()
    return title, link


def read_last_published():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def write_last_published(link):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(link)


def build_thread_text(title):
    """본문에는 링크 없이 제목(문구)만 올린다. 링크는 댓글로 따로 단다."""
    return title


def create_container(user_id, text, access_token, reply_to_id=None):
    import urllib.parse

    params = {"media_type": "TEXT", "text": text, "access_token": access_token}
    if reply_to_id:
        params["reply_to_id"] = reply_to_id
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        f"https://graph.threads.net/v1.0/{user_id}/threads", data=data, method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        import json

        result = json.loads(response.read())
        return result["id"]


def publish_container(user_id, creation_id, access_token):
    import urllib.parse

    data = urllib.parse.urlencode(
        {"creation_id": creation_id, "access_token": access_token}
    ).encode()
    req = urllib.request.Request(
        f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
        data=data,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        import json

        return json.loads(response.read())


def get_user_id(access_token):
    import json

    url = f"https://graph.threads.net/v1.0/me?fields=id,username&access_token={access_token}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read())
        return result["id"]


def main():
    rss_url = get_env("RSS_URL")
    access_token = get_env("THREADS_LONG_TOKEN")

    print(f"[확인] RSS 확인 중: {rss_url}")
    title, link = fetch_latest_rss_item(rss_url)
    print(f"[확인] 최신 글: {title} ({link})")

    last_published = read_last_published()
    if last_published == link:
        print("[알림] 이미 발행한 글입니다. 새로 할 일이 없습니다.")
        return

    print("[진행] 새 글 발견 -> 스레드 발행을 시작합니다.")
    text = build_thread_text(title)

    user_id = get_user_id(access_token)

    # 1) 본문(링크 없이 제목만) 발행
    creation_id = create_container(user_id, text, access_token)
    print(f"[진행] 본문 컨테이너 생성 완료 (id={creation_id}) -> 30초 대기")
    time.sleep(30)
    main_result = publish_container(user_id, creation_id, access_token)
    main_post_id = main_result["id"]
    print(f"[완료] 본문 발행 성공: {main_result}")

    # 2) 링크를 댓글(답글)로 발행
    reply_creation_id = create_container(user_id, link, access_token, reply_to_id=main_post_id)
    print(f"[진행] 댓글(링크) 컨테이너 생성 완료 (id={reply_creation_id}) -> 30초 대기")
    time.sleep(30)
    reply_result = publish_container(user_id, reply_creation_id, access_token)
    print(f"[완료] 댓글(링크) 발행 성공: {reply_result}")

    write_last_published(link)
    print("[완료] 상태 파일 갱신 완료.")


if __name__ == "__main__":
    main()
