# 노르딕로그 Threads 서버 운영

## 최우선 운영 상태 — 2026-11-09 중단

사용자가 오늘부터 Threads에 글을 올리지 말라고 명시 요청했다. 쇼핑·정보형을 포함해 자동 제작·게시를 중단했다. Cloudflare ACTIVE=0과 Cron 제거를 배포했고, GitHub THREADS_SHOPPING_SERVER_ACTIVE=0 / threads-shopping.yml disabled_manually 및 진행 중 실행 없음, PC threads-2 PAUSED를 확인했다. 2026-11-10 09:00·15:00 대기 글도 skipped로 변경했고 정오를 포함해 미게시 대기 글 0건을 확인했다. Worker 배포 버전은 eaaaaec3-947b-4991-ac6f-5e44ffa18999다. 기존 공개 글이나 인증정보는 삭제하지 않았다. 사용자의 명시적인 재개 지시 전에는 아래 과거 승인·일정을 실행하지 않는다. 다른 채널은 변경하지 않는다.

## 소유자와 실행 경로

2026-11-07 사용자는 PC 없이 매일 09:00·12:00·15:00 KST 발행을 요청했고, 기존 Threads 토큰의 Cloudflare 전용 Worker Secrets 저장 및 쿠팡 API 키의 본인 GitHub 전용 Actions Secrets 저장을 명시적으로 승인했다. 승인 후 이전을 완료했다. 기존 Gemini 키는 GitHub에 그대로 남아 있으며 추출·복사하지 않았다.

- 전용 서버: https://nordic-log-threads.apollo0217.workers.dev
- 서버 코드: https://github.com/hwang0217-lang/cardnews/tree/main/threads-shopping
- 준비·사전 검증·감시 작업: https://github.com/hwang0217-lang/cardnews/actions/workflows/threads-shopping.yml
- Cloudflare 계정: `9af6a1fc8a141f591e6de4563d203dee`, Worker: `nordic-log-threads`, Durable Object: `ShoppingState`
- 서버 활성 조건: Worker 변수 `ACTIVE=1`, GitHub 변수 `THREADS_SHOPPING_SERVER_ACTIVE=1`. 최종 상태는 automation.config.json 및 실제 서버 `/admin/state`로 확인한다.

이 경로는 기존 Instagram Nordic/사회이슈 및 여행 서버와 별개다. 기존 채널 워크플로·쿠키·인증정보·발행 상태를 변경하지 않는다.

## 2026-11-09 변경: 정보형 글 추가 (사용자 승인·배포 완료)

팔로워 0명 단계라 구성을 바꿨다. 09:00·15:00은 링크·상품이 없는 "자취 살림 팁" 정보/대화 글(`type:'info'`, `generate-info.mjs`), 12:00은 쇼핑 글 1건이다. 정보형 글은 쿠팡·제휴·할인·수치·체험 가장 표현을 정책 코드가 막는다. Worker 빌드 `a7d3e19c4b6f2085`, GitHub 커밋 `5993cbe`. 정보형 글의 Threads `TEXT_POST` 실제 응답은 첫 게시(2026-11-10 09:00)에서 확인해야 한다. 아래 "일일 흐름"의 3건·슬롯 설명 중 쇼핑 부분은 12:00 1건으로 읽는다. 주제는 `policy.mjs`의 `INFO_TOPIC` 한 줄로 바꾼다.

## 2026-11-09 후속 기록 (Claude Code 전담)

- 재배포 최종 빌드 `c41b8f2e7d905a63`, GitHub 커밋 `1d5bd7b`. 이후 사용자 중지 지시로 ACTIVE=0·Cron 제거 상태이며 소스에는 정보형 글 코드가 그대로 남아 있다.
- 관리 엔드포인트 추가: `/admin/skip`(아직 게시 시도 전인 queued/held 글을 operator_skipped로 건너뜀), `/admin/reviewed-copy`는 정보형 글 문안 교체도 지원한다.
- 재개 시 순서: 쇼핑 글의 행사-상품 불일치 개선 → Worker ACTIVE=1과 GitHub THREADS_SHOPPING_SERVER_ACTIVE=1 동시 활성 → 첫 정보형 글의 `TEXT_POST` 실제 게시를 원장으로 확인. `TEXT_POST` 실응답은 아직 미검증이다.
- 이 프로젝트의 운영 담당은 Claude Code다. Codex `threads-2`는 재활성화하지 않는다.

## 일일 흐름

1. KST 06:45 GitHub에서 최근 7일 공식 뉴스룸 자료를 수집하고 서로 다른 분야의 관심 계기를 고른다. 08:10 보조 일정은 최초 스케줄 자체가 누락됐을 때만 사용하며 같은 날짜의 모델 생성 실패를 자동으로 반복하지 않는다.
2. 기존 Gemini 모델 `gemini-3.5-flash-lite`를 최대 3회 호출하여 자료 선택, 실제 쿠팡 상품 매칭·문안, 실제 이미지 기반 독립 검수를 수행한다. 별도 모델 전환·유료 한도 상향·서비스 구매를 하지 않는다. 코드 수정 원인이 실제로 확인된 운영자 복구는 새 리비전별로 제한하여 기록한다.
3. 공식 쿠팡 API에서 정확한 상품 ID·itemId·vendorItemId와 원본 광고 사진을 가져온다. 회원 계정으로 공식 제휴 단축 링크를 생성하고 원본 대상과 대조한다. 가짜 링크나 다른 사람의 파트너스 링크를 사용하지 않는다.
4. 사진은 원본 광고 API 이미지 1장. 쿠팡 공식 광고 이미지 도메인에서 공식 `*.coupangcdn.com` HTTPS 이미지 서버로 이동하는 경우만 최대 3회 따른다. 고객 리뷰 복제·사진 편집·자가 촬영/사용 경험 가장은 금지한다.
5. 08:25·11:25·14:25에는 해당 슬롯의 정확한 상품 옵션과 원문 근거를 다시 조회한다. 검증이 90분 이상 오래됐으면 Worker가 게시를 보류한다. API 검색에 없다는 사실을 품절이나 인기 급증으로 해석하지 않는다.
6. Cloudflare 서버의 매분 타이머가 08:50·11:50·14:50부터 사진 컨테이너를 준비하고, 09:00·12:00·15:00 슬롯이 되면 게시한다. 플랫폼 처리에 따라 실제 완료는 지정 시각 이후 수초 이상 걸릴 수 있다. 지연 15분이 넘으면 몰아서 게시하지 않는다.
7. API로 실제 사진·문안·계정·게시물 주소를 다시 조회해 `published_verified`만 성공으로 기록한다. 상품·동일 문안·슬롯의 중복을 차단한다. `publish_requested`/`ambiguous_publish_result`에서는 피드 대조만 하며 맹목적으로 다시 게시하지 않는다.
8. 09:20·12:20·15:20에는 GitHub 읽기 전용 감시가 타이머와 실제 게시 원장을 확인한다. 실패 실행은 GitHub Actions 실패로 남는다. 개인 GitHub 알림 수신 설정과 메일 실제 수신 여부는 별개다.

## 문안

친구 같은 반말과 소량 이모지. 최신 행사·관심 계기를 먼저 쓰고 상품으로 자연스럽게 이어진다. 링크 바로 위에 `물어보는 분들 많아서 링크 남겨 둘게`, 링크 다음 줄에 `쿠팡 제휴 링크 포함 · 구매 시 수수료를 받습니다.`를 넣는다. 전체 500 코드포인트 이내다. 이 위치는 사용자의 문안 승인 기록이며 법적 적합성을 별도로 보장하지 않는다.

## 인증정보

- Threads 토큰: Cloudflare `THREADS_TOKEN`; 갱신된 토큰은 암호화된 서버 저장소에만 보관한다. 갱신은 발급/직전 갱신 후 36시간 이상인 첫 07시대 점검에서 수행한다. 답글 권한은 사용하지 않는다.
- 쿠팡 키: GitHub `THREADS_SHOPPING_COUPANG_ACCESS`, `THREADS_SHOPPING_COUPANG_SECRET`.
- 연결 관리 키: Cloudflare `ADMIN_KEY`, GitHub `THREADS_SHOPPING_ADMIN_KEY`. 로컬 사본은 `.secrets/server-admin.dpapi.json`의 Windows DPAPI 암호문만 보관한다.
- 원본 키·토큰·관리 키를 명령행 인수·채팅·공개 코드·로그로 출력하지 않는다.

## 점검과 변경

`scripts/Test-ServerConnection.ps1 -Operation Check`는 계정 확인, `-Operation State`는 키를 출력하지 않는 원장 조회다. `-Operation Prepare -PostKey YYYY-MM-DD-HHmm`는 미래 게시물의 비공개 사진 컨테이너만 준비한다. 추가 시험 게시를 하지 않는다.

실제 예약 변경·중지는 Worker와 GitHub 두 운영 변수를 함께 확인한다. PC용 Codex `threads-2`를 다시 활성화하거나 로컬 Publish-ThreadsSample.ps1로 서버와 같은 글을 별도 게시하지 않는다. 소스 변경은 기존 정상 게시물과 원장을 보존하고, 테스트→비활성 상태 검증→배포·활성 확인 순서를 따른다.
