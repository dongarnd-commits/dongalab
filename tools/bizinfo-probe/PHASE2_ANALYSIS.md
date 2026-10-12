# 기업마당 API 2차 최소 Probe

## 1. 범위와 실제 근거

검증일 2026-10-12 (Asia/Seoul). Node.js v24.19.0, 추가 패키지 없음. 기존 probe.cjs에 `--phase2` 진입점만 추가하고 phase2.cjs에서 기존 Key 읽기/items/Sanitization을 재사용했다. 기본 1차 실행기능과 당시 observations/sample/ANALYSIS는 유지했다.
AGENTS, Baseline, Architecture, 기존 Probe/README/분석/관찰/샘플, .gitignore, .env.example를 확인했다. 실제 Key는 존재 여부만 확인하고 출력하지 않았다. Branch main. 기준문서/Collector/DB/Schema/E2E 문서는 수정/생성하지 않았다.
공식 API 근거는 1차에 확인한 [지원사업 API 안내](https://www.bizinfo.go.kr/apiDetail.do?id=bizinfoApi)를 재사용했다. Endpoint를 새로 추측하거나 파일 URL을 조합하지 않았다.
실제 근거는 phase2-observations.json의 HTTP/배열/시각/HTML 구조/파일 헤더 관찰이며, 이하 종료조건/Version/Retry 제안은 Production 정책 확정이 아니다.

## 2. 호출 내역과 최소화

| 순서 | 요청 | 결과 |
| --- | --- | --- |
| 1 | 기존 API, searchCnt=0, pageUnit=2, pageIndex=1 | 200 JSON, 2건, totCnt=1423 |
| 2 | 같은 조건, pageIndex=ceil(1423/2)=712 | 200 JSON, 1건, totCnt=1423 |
| 3 | 같은 조건, pageIndex=713 | 200 JSON, 0건, jsonArray=[] |
| 4 | 1차 sample-page1의 pblancUrl 그대로 GET | 200 HTML, 공고 ID 확인, redirect 없음 |
| 5 | 같은 샘플 flpthNm 그대로 Range GET | 200, PDF 앞부분 64바이트 검사 후 취소 |
| 6 | 같은 샘플 printFlpthNm 그대로 Range GET | 200, PDF 앞부분 64바이트 검사 후 취소 |

총 Network Request 6회. 중간 페이지 순회, 추가 공식 문서 조회, 재시도, 상세 대량조회, 고의 오류 호출은 없었다. 파일 서버는 Range 요청에 206/Content-Range가 아닌 200을 반환했다. 검사/보관한 prefix는 64바이트이고 전체 전송량이 64바이트였다고 주장하지 않는다. 스트림을 즉시 취소했으며 바이너리를 Repository에 저장하지 않았다.

## 3. Pagination 종료조건 — CONFIRMED (관찰된 요청 조건)

pageUnit=2에서 첫 응답 2건, 계산된 마지막 712페이지 1건, 다음 713페이지는 `{ "jsonArray": [] }`와 HTTP 200이었다. 첫/마지막 totCnt=1423은 계산과 일치한다. 빈 결과에는 항목이 없어 totCnt도 없다.
이번 범위에서 searchCnt=0은 공식 문서의 전체 제공 옵션을 사용하면서 pageUnit으로 응답 건수를 제한할 수 있었다. 1차 searchCnt=2에서도 totCnt=1423이었으므로 searchCnt를 전체건수나 마지막 페이지 판별값으로 삼지 않는다. 모든 파라미터 조합에서의 searchCnt 의미는 여전히 미확정이다.
Collector 종료조건 후보는 현재 검색조건의 totCnt/pageUnit으로 마지막 후보를 계산하고 배열 길이/빈 결과와 대조하는 것이다. 짧은 페이지/빈 배열은 이번 조건의 종료 신호지만, 수집 중 추가/삭제/정렬 변화나 다른 필터에서는 달라질 수 있으므로 일관성·중복검사·실행 상한 정책은 후속 설계가 필요하다. 전체 1423건 순회 성공을 의미하지 않는다.

## 4. 상세/본문 — PARTIALLY_CONFIRMED

기존 공고 `PBLN_000000000127088`의 pblancUrl이 HTTP 200, `text/html;charset=UTF-8`로 접근됐다. 응답 HTML 81,318바이트는 메모리에서만 검토했고 저장하지 않았다. HTML에서 같은 pblancId와 API의 두 파일 식별자를 찾았다. redirect는 없었다.
HTML에는 사업개요/첨부파일/신청서 표현, table 2개, 파일 관련 href/src 후보 3개가 있었다. 이는 원문과 파일 영역으로 연결 가능한 구조 근거이며 자유텍스트의 완전성, 본문 길이 비교나 Production 추출 selector를 검증한 것은 아니다. 사이트 공통 UI나 기타 링크가 섞일 수 있어 href 수를 첨부파일 개수로 확정하지 않는다.
API는 개요/기간/기관/대상/신청방법/참조를 제공한다. 실제 공고·서식 요구사항을 분석하려면 상세페이지 보완 및 첨부파일 분석 경로가 필요하다. 페이지 접근 성공만으로 bsnsSumryCn보다 더 상세한 전체본문 추출이나 Analyzer 입력의 충분성을 확정하지 않는다.

## 5. 첨부와 print file

| 필드 | 실제 접근 | Content-Type | Content-Length | 형식 근거 | 역할 판정 |
| --- | --- | --- | --- | --- | --- |
| flpthNm / fileNm | 200, redirect 없음 | application/octet-stream | 130041 | 앞부분 %PDF-, Content-Disposition 확장자 pdf | 실제 파일 접근 CONFIRMED, 서식/문서 역할 미확정 |
| printFlpthNm / printFileNm | 200, redirect 없음 | application/octet-stream | 399346 | 앞부분 %PDF-, Content-Disposition 확장자 pdf | 실제 파일 접근 CONFIRMED, 의미 PARTIALLY_CONFIRMED |

직접 접근 URL은 API 응답의 기업마당 getImageFile.do 링크를 그대로 재사용했다. atchFileId/fileSn 값은 관찰된 참조일 뿐 임의 생성 규칙이 아니다. 상세 HTML에도 두 file ID가 존재해 같은 공고와 연결됨을 확인했다.
공식 명세의 print 필드 설명은 본문출력파일 참조이며 실제 PDF 접근은 확인됐다. PDF 내용은 읽지 않았으므로 공고문 출력파일/상세본문/신청서식/기타 생성파일 중 정확한 역할을 확정하지 않는다. Analyzer에 입력할 파일 후보지만 역할 분류와 텍스트/서식 추출은 후속 검증이다.
실제 파일 경로 하나 이상 확보는 CONFIRMED. 다중 첨부 목록 구조, HWP/HWPX/압축파일 처리, 링크 유효기간, 파일 내용 변경은 UNCONFIRMED이다. 전체파일/바이너리/파일명 원문/문의처는 저장하지 않았다.

## 6. 변경감지 신호 — PARTIALLY_CONFIRMED

| 공고 ID | creatPnttm | updtPnttm | 관찰 |
| --- | --- | --- | --- |
| PBLN_000000000127088 | 2026-10-08 14:07:33 | 2026-10-08 15:22:02 | 서로 다름 |
| PBLN_000000000127087 | 2026-10-08 13:42:13 | 2026-10-08 15:22:02 | 서로 다름 |
| PBLN_000000000092578 | 2023-11-03 13:53:04 | 2023-11-16 10:43:31 | 서로 다름 |

3개 공고에서 두 시각이 달랐다. 앞 2건 기간은 `2026-10-01 ~ 2026-10-23`, 마지막은 `2020.01.01 ~ 2026.12.31`로 형식도 다르다. 3건 모두 개요/print 파일이 있고 마지막 공고의 flpthNm은 비어 있었다. 결측/형식 차이를 수용해야 한다.
updtPnttm이 존재하며 등록시각과 다를 수 있다는 사실만 확인했다. 과거/현재 동일 공고 내용 비교나 실제 수정 이벤트 추적을 하지 않았으므로 모든 업무변경/파일내용변경을 보장한다는 주장은 불가하다. 시간대/변경 원인도 미확정이다.
전략 후보 A(updtPnttm 우선 + 핵심 Content 비교)는 실행 후보 선별에 활용 가능, B(정규화 핵심 필드 + Attachment metadata 비교)는 실제 업무변경 평가에 필요하다. C(Content Hash)는 필요 시 검토하되 알고리즘과 정규화/Version 정책은 확정하지 않는다. inqireCo/totCnt를 업무 Version 변경으로 취급하지 않는다.

## 7. 오류/호출제한 — PARTIALLY_CONFIRMED

실제 Empty Result는 200 JSON `{ "jsonArray": [] }`다. 오류 코드/메시지가 아니라 정상 빈 결과로 구분할 수 있다.
6개 응답에서 ratelimit/retry-after 계열 Header가 관찰되지 않았다. 공식 문서에서 확정한 Rate/Daily Limit, Throttling, 서버 timeout도 없다. 제한이 없다는 결론은 내리지 않는다.
고의 인증실패/잘못된 Parameter/429/5xx는 유도하지 않았다. 인증오류와 비정상 응답 형식은 UNCONFIRMED. 실제 서버 Retry-After 근거가 없으므로 Retry 횟수/대기 정책은 확정하지 않는다. Probe의 30초 timeout과 Network Request 한계는 로컬 안전장치다.

## 8. Architecture Fit-Gap 재평가

분류는 CONFIRMED(실제 경로/응답), PARTIALLY_CONFIRMED(부분 관찰), UNCONFIRMED(검증 안 됨), INTERNAL_RESPONSIBILITY(API가 아닌 내부 정책)이다. CONFIRMED는 Production 구현 완료가 아니다.

| 항목 | 분류 | 실제 근거/Architecture 관계 | E2E 확정 범위와 후속 Collector 설계 |
| --- | --- | --- | --- |
| External Notice ID | CONFIRMED | API/상세가 pblancId로 연결 | Source+External ID 참조; 장기 안정성은 추적 |
| Raw Source | INTERNAL_RESPONSIBILITY | API JSON/상세 HTML/파일 prefix 관찰 | 인증 제외 provenance 보존; 비공개 Raw·개인정보 정책 |
| Normalization | PARTIALLY_CONFIRMED | jsonArray, 필드/기간 형식 차이, 결측 | 매핑 입력 정의 가능; 예외형식/검증 정책 |
| Notice | PARTIALLY_CONFIRMED | 실제 목록필드와 원문/파일 연결 | 내부 생성 경로 표현; ID/저장 검증은 내부 |
| NoticeVersion | INTERNAL_RESPONSIBILITY | updtPnttm은 내부 Version 자체가 아님 | 신호+내용비교/검토 경로; Version 정책 |
| Application Period | PARTIALLY_CONFIRMED | 두 날짜 문자열 형식 | 원문기간 보존/파싱 후보; 상시/조건부/시간대 |
| Original Detail Source | CONFIRMED | 200 HTML/ID/파일 참조 연결 | 상세 접근 경로; 본문 selector/완전성은 미확정 |
| Attachments | PARTIALLY_CONFIRMED | 두 API URL에서 PDF prefix 확인 | 파일 확보 경로; 전체 검증/역할/다중파일/포맷 |
| Duplicate Detection | INTERNAL_RESPONSIBILITY | pblancId 사용 가능 | 내부 ID 매핑/idempotency; 동시 import 검증 |
| Change Detection | PARTIALLY_CONFIRMED | 다른 creat/updt 사례 3건 | 실제 수정신호+내부 비교 정책; 보장/파일변경 검증 |
| Pagination Termination | CONFIRMED | 1423/2→712 1건→713 빈 배열 | 관찰 조건 종료 설명; 데이터 변동/필터/searchCnt |
| Collection Job | INTERNAL_RESPONSIBILITY | Web와 분리 원칙 유지 | 실행/결과/중단/로그 정책 |
| Retry Boundary | UNCONFIRMED | 빈 결과만 실제 관찰, 오류/Retry-After 없음 | 빈 결과와 오류 구분; 429/5xx/timeout 정책 |
| Snapshot Import | PARTIALLY_CONFIRMED | 1차 실제 구조 샘플, 동일 parser 진입 가능 | 동일 Normalize 경로; 의미검증 Fixture 추가 |
| Notice/Form Analyzer Input | PARTIALLY_CONFIRMED | 개요/메타데이터/상세/실제 PDF 경로 | 파일 확보→추출 후보→Human Review; 역할/정확도/지원포맷 |

UNCONFIRMED 세부: 다중첨부 목록, 전체본문 추출 규칙, 파일별 역할, HWP/HWPX, 호출제한과 오류 응답. 핵심 Architecture 변경은 필요하지 않다. 실제 신호/결측/기간형식 및 종료/추출 정책은 후속 Collector/Intelligence 설계에서 구체화한다.

## 9. E2E Readiness

- Q1 목록 → Notice: YES. 실제 ID/필드/배열을 근거로 입력과 내부 정규화/저장 책임을 설명할 수 있다.
- Q2 Notice → Notice/Form Analyzer: YES (경로 수준). 개요/기간/원문/파일 확보와 추출 Candidate/Human Review 경로를 표현할 수 있다. Analyzer 충분성/추출 성공은 미확정으로 표시해야 한다.
- Q3 최소 현실적 원문/첨부 경로: YES. 기존 공고 상세 HTML 200과 API 파일 URL 2개의 PDF prefix 확인.
- Q4 Pagination 종료: YES. 관찰 조건에서 마지막 1건/다음 빈 배열을 실제 응답으로 설명 가능.
- Q5 변경감지: YES. updtPnttm/등록시각 차이 + 내부 핵심 Content/첨부 비교 정책 필요로 표현 가능.

**최종 판정: READY_FOR_E2E (경로와 책임 설계 기준).** Production Collector 완료나 전체 문서 분석 성공을 뜻하지 않는다. 검증된 현실 경로를 사용하고 남은 정책/추출/오류 범위를 후속 확정 필요로 명시하면 E2E 문서 작성을 시작할 수 있다.
추출 selector, 서식 역할, 지원포맷, 변경보장, Retry/Rate Limit, 동시성/변동 Pagination은 후속 Collector/Intelligence/Test 과제이며 경로 수준 E2E 작성의 Blocker는 아니다.

## 10. 보안/파일/검증

Key/인증 URL/원문 오류/문의처/전체 HTML/바이너리는 출력 또는 저장하지 않았다. 결과 저장 전 Key 원문과 URL 인코딩 문자열 포함 여부를 검사한다. 실제 파일명은 확장자만 기록하고 날짜/ID/건수/구조 통계만 남긴다.
probe.cjs/phase2.cjs 구문 및 --check, 기존 sample parser를 오프라인으로 확인한다. 1차 실행기능을 확인하려고 불필요한 API 호출을 반복하지 않는다.
변경영역은 tools/bizinfo-probe 내부뿐이며 1차 ANALYSIS/observations/sample과 기존 기준문서는 유지했다. Git add/commit/push, Branch 변경, package 설치, Production Module 구현은 없다.
