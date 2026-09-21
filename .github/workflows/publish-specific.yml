name: Threads 지정 글 발행

# 수동 실행 전용입니다. 자동으로는 절대 실행되지 않습니다.
on:
  workflow_dispatch:
    inputs:
      post_url:
        description: "스레드에 올릴 글 주소 (예: https://jcview.com/123)"
        required: true
      custom_text:
        description: "(선택) 이 칸을 채우면 제목 자동 추출 대신 이 문구를 그대로 사용합니다"
        required: false
        default: ""

jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - name: 저장소 체크아웃
        uses: actions/checkout@v4

      - name: 파이썬 설정
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: 지정 글 발행
        env:
          POST_URL: ${{ inputs.post_url }}
          CUSTOM_TEXT: ${{ inputs.custom_text }}
          THREADS_LONG_TOKEN: ${{ secrets.THREADS_LONG_TOKEN }}
        run: python scripts/publish_specific_post.py
