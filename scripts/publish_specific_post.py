"""
지정한 글 주소(URL)를 스레드에 발행하는 스크립트.
(자동 RSS 감지와는 별개로, 원하는 글을 골라서 수동으로 올릴 때 사용)

동작 방식:
1. POST_URL(입력받은 글 주소)을 연다.
2. <title> 태그에서 글 제목을 가져온다. (CUSTOM_TEXT가 주어지면 그걸 그대로 사용)
3. 스레드에 발행한다.

state/last_published.txt 는 건드리지 않는다.
(이건 "자동 감지용 기록"이라, 수동 발행은 그 기록에 영향을 주지 않아야 자동화가 꼬이지 않음)
"""

import os
import re
import sys
import time
import urllib.request


def get_env(name, required=True, default=None):
    value = os.environ.get(name, default)
    if required and not value:
        print(f"[오류] 환경변수 {name} 가 설정되지 않았습니다.")
        sys.exit(1)
    return value


def fetch_title(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        html = response.read().decode("utf-8", errors="ignore")
    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = match.group(1).strip()
    # 티스토리 제목 뒤에 " :: 블로그이름" 같은 게 붙는 경우가 많아서 앞부분만 사용
    title = re.split(r"\s*[:|·]{1,2}\s*", title)[0].strip()
    return title


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
    post_url = get_env("POST_URL")
    custom_text = get_env("CUSTOM_TEXT", required=False, default="")
    access_token = get_env("THREADS_LONG_TOKEN")

    if custom_text.strip():
        title = custom_text.strip()
        print(f"[확인] 직접 입력한 문구 사용: {title}")
    else:
        print(f"[확인] 글 제목 가져오는 중: {post_url}")
        title = fetch_title(post_url)
        if not title:
            print("[오류] 글 제목을 가져오지 못했습니다. CUSTOM_TEXT를 직접 입력해주세요.")
            sys.exit(1)
        print(f"[확인] 가져온 제목: {title}")

    text = build_thread_text(title)

    user_id = get_user_id(access_token)

    # 1) 본문(링크 없이 제목/문구만) 발행
    creation_id = create_container(user_id, text, access_token)
    print(f"[진행] 본문 컨테이너 생성 완료 (id={creation_id}) -> 30초 대기")
    time.sleep(30)
    main_result = publish_container(user_id, creation_id, access_token)
    main_post_id = main_result["id"]
    print(f"[완료] 본문 발행 성공: {main_result}")

    # 2) 링크를 댓글(답글)로 발행
    reply_creation_id = create_container(user_id, post_url, access_token, reply_to_id=main_post_id)
    print(f"[진행] 댓글(링크) 컨테이너 생성 완료 (id={reply_creation_id}) -> 30초 대기")
    time.sleep(30)
    reply_result = publish_container(user_id, reply_creation_id, access_token)
    print(f"[완료] 댓글(링크) 발행 성공: {reply_result}")


if __name__ == "__main__":
    main()
