# 기업마당 API 최소 Probe 분석

## 1. 검증 범위와 근거

검증일: 2026-10-12 (Asia/Seoul). Runtime: Node.js v24.19.0, 추가 패키지 없음.
AGENTS, Project Baseline, System Architecture, .gitignore, .env.example를 확인했다. 로컬 .env가 ignore되고 Key가 비어 있지 않음을 값 출력 없이 검사했다.
Repository에는 실제 API 명세/Endpoint가 없어 [공식 지원사업 API 안내](https://www.bizinfo.go.kr/apiDetail.do?id=bizinfoApi)로 요청방식을 확인했다.
공식 문서 확인, 실제 응답 관찰, 후속 설계 제안은 구분한다. 기준문서/Schema/Collector는 변경하거나 구현하지 않았다.

제한 환경 첫 실행은 연결 단계에서 실패해 응답을 확보하지 못했다. 권한을 확대한 실행에서 실제 GET 요청 2회가 성공했다. 최초 실패의 원인을 서버 오류나 인증실패로 단정하지 않는다. 원문 오류는 Secret 노출 방지를 위해 출력하지 않았다.

## 2. 실제 요청/응답

- Endpoint: `https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do`, GET.
- 인증: 로컬 Key를 query parameter `crtfcKey`로 전달. 실제 인증 성공. 인증실패 Response는 확인하지 않았다.
- 공통 요청: `dataType=json`, `searchCnt=2`, `pageUnit=1`. `pageIndex=1`과 `2`만 요청.
- 두 응답 모두 HTTP 200, `application/json; charset=UTF-8`. 크기 2585/2424 bytes.
- 실제 wrapper는 `{ "jsonArray": [ ... ] }`. 공식 문서의 예시 `jsonArray.item` 구조와 다르므로 예시만으로 parser를 확정하면 안 된다.
- 첫 ID는 `PBLN_000000000127088`, 둘째는 `PBLN_000000000127087`. 페이지별 1건으로 순서가 달라 pageIndex 동작을 확인했다.
- 두 항목의 `totCnt`는 숫자 1423이다. `searchCnt=2`와 별개인 값이 반환됐다. 전체/검색범위/조회제한 사이 정확한 의미와 마지막 페이지는 이 최소 검증으로 확정하지 않는다.
- Cursor는 관찰되지 않았다. `pageIndex/pageUnit`은 공식 명세 및 두 페이지 응답으로 확인했다. 실제 마지막 페이지/빈 페이지는 호출하지 않았다.

## 3. 실제 필드와 해석 범위

두 항목 모두 다음 22개 필드를 가지며 모두 값이 있었다. 숫자는 `inqireCo`, `totCnt`, 나머지는 문자열이다. 필드 이름의 의미는 공식 명세와 대조했으며 전체 공고에서 항상 존재/유효함을 증명한 것은 아니다.

| 용도 | 실제 필드 | 확인/제한 |
| --- | --- | --- |
| 공고 ID | pblancId | 내부 ID와 별도로 External ID 후보. 장기 안정성/Source 간 중복은 미검증 |
| 공고명 | pblancNm | 문자열 |
| 기관 | jrsdInsttNm, excInsttNm | 소관/수행기관 |
| 등록/수정시각 | creatPnttm, updtPnttm | 두 필드 모두 실제 값 존재. 수정 의미/갱신 보장/시간대는 후속 확인 |
| 신청기간 | reqstBeginEndDe | 첫 항목은 `2026-10-01 ~ 2026-10-23`. 개별 시작/종료 필드 없음 |
| 지원대상 | trgetNm | 문자열 |
| 분야 | pldirSportRealmLclasCodeNm, pldirSportRealmMlsfcCodeNm | 대분류/중분류 표현 |
| 태그/지역 후보 | hashtags | 실제 소문자 h. 별도 지역 필드는 관찰되지 않음. 태그 지역 추출은 별도 검증 |
| 사업개요 | bsnsSumryCn | 값 존재. 전체 상세본문과 동일하다고 단정하지 않음 |
| 신청방법/문의/신청 URL | reqstMthPapersCn, refrncNm, rceptEngnHmpgUrl | 실제 값 존재. 문의처/외부 URL은 샘플에서 마스킹 |
| 공고 원문 URL | pblancUrl | 기업마당 상세 페이지 링크 존재 |
| 첨부 | flpthNm, fileNm | 경로/파일명 값 존재. 실제 다운로드/형식/다중 첨부 구조 미검증 |
| 본문출력파일 | printFlpthNm, printFileNm | 별도 파일 경로/파일명. 전체본문/신청서식 포함 여부 미검증 |
| 조회수/전체건수 | inqireCo, totCnt | 숫자. 조회수는 업무내용 변경과 분리해야 함 |

별도 상태, version, update flag, 신청시작일/종료일, 독립 지역 필드와 상세본문 전용 필드는 두 응답에서 관찰되지 않았다. API 전체에서 제공되지 않는다고 단정하지 않는다.
첨부/원문 링크 존재만 확인했으며 파일/상세 Endpoint를 호출하지 않았다. Notice/Form Analyzer에는 개요/신청방법/기간/대상/분류/태그, 원문/첨부 참조와 Source Version을 전달할 수 있다. 완전한 요구사항/서식 분석에는 원문과 첨부 확보 검증이 더 필요하다.

## 4. 오류/제한/변경감지

인증 실패, 잘못된 Parameter, 빈 결과, HTTP Error/API Error Code/Message 구조는 확인하지 않았다. 실제 Key를 변경하거나 고의 오류 호출은 하지 않았다.
Rate Limit/Daily Limit/Throttling을 나타내는 응답 Header는 두 응답에서 발견되지 않았으며 공식 안내에서 확정된 제한값도 확인하지 못했다. 제한이 없다는 의미는 아니다. Probe의 30초 timeout은 클라이언트 설정으로 서버 규정이 아니다.
`updtPnttm`은 변경감지 신호 후보이나 실제 동일 공고 전후 응답을 비교하지 않아 신뢰성을 확정할 수 없다. 공고 내용/기간/첨부의 비교가 필요할 수 있으며 Hash 기반 Change Detection은 선택 가능성만 남기고 알고리즘을 확정하지 않는다. 조회수 `inqireCo`와 전체건수 `totCnt` 등 변동 메타데이터를 업무 Version 생성 조건에 무조건 포함하지 않는다.

## 5. Architecture Fit-Gap

A: 그대로 적용 가능, B: 약간 조정 필요, C: 추가 검증 필요, D: API 관찰범위에서 제공되지 않아 내부/별도 처리 필요.

| 항목 | 분류 | 근거와 후속 조치 |
| --- | --- | --- |
| External Notice ID | A/C | pblancId 관찰. Source+pblancId 매핑 개념 적용, 장기 안정성/다른 Source 충돌 확인 |
| Internal Notice ID | D | 관찰범위에 내부 ID 없음. 내부 Domain에서 부여 |
| Raw Source | A | 응답/Source/수집시각/요청조건(인증 제외)을 추적하는 경계 적용 |
| Normalization | B | 실제 jsonArray 배열과 22개 필드/타입 기준 매핑. 공식 예시 wrapper 차이 반영 |
| Notice | A | 제목/기관/기간/대상/개요/링크 제공. 개별 값의 결측 허용 필요 |
| NoticeVersion | D/C | 명시적 Version 관찰 안 됨. 내부 Version 정책 및 수정신호 검증 필요 |
| Original URL | A/C | pblancUrl 존재. 상세 조회/본문 확보 미검증 |
| Attachments | C | 두 종류 파일 경로/명칭 존재. 다운로드/다중파일/파일변경/서식 여부 확인 필요 |
| Duplicate Detection | A/C | External ID 기반 매핑 가능. 동일 공고 재수집/동시 import 미검증 |
| Change Detection | C | updtPnttm 존재, 실제 변경/갱신보장 미검증. 내용비교 정책 검토 |
| Pagination | B/C | pageIndex/pageUnit 실제 확인. searchCnt/totCnt 의미 및 끝 판단 추가 확인 |
| Collection Job | A | 수집을 Web 조회와 분리하는 경계 유지. 이번 Probe는 Job 구현 아님 |
| Retry | A/C | 경계 유지. 오류 응답/429/5xx/제한 및 재시도 정책은 미검증 |
| Snapshot Import | A/C | 실제 구조 샘플로 동일 parser/Normalize 설계 가능. 텍스트 마스킹 샘플은 의미 분석 Demo 자료로 불충분 |

현재 핵심 Architecture와 충돌하지 않는다. 기준문서 자동수정 없이 후속 Collector 설계에 실제 wrapper, 수정필드, 기간 문자열, 첨부 종류, Pagination 제한을 반영해야 한다.

## 6. E2E 설계 질문별 답변

1. 공고 식별: pblancId를 Source와 연결하는 External ID 후보로 사용, 내부 ID는 별도.
2. 목록 Pagination: pageIndex/pageUnit으로 두 페이지 확인, 전체 순회/끝 판단은 후속 검증.
3. 신규/기존: 저장된 Source/External ID와 비교하는 내부 설계 가능, 반복수집 실행 검증은 별도.
4. 수정: updtPnttm 및 내용/기간/첨부 비교 후보. 갱신 의미/보장은 미확정.
5. 본문: bsnsSumryCn은 개요, pblancUrl/printFlpthNm은 원문 참조. 전체본문 확보는 미검증.
6. 첨부: flpthNm/fileNm 및 printFlpthNm/printFileNm. 다운로드/서식 구조 미검증.
7. 신청기간: reqstBeginEndDe 문자열, 예외기간/상시접수/시간대는 미검증.
8. 원문 URL: pblancUrl 존재.
9. Raw 최소 보존: 인증정보를 제외한 응답, Source, 수집시각, 비밀 제외 요청조건/페이지, HTTP 상태/형식, External ID, 원문/첨부 참조. 응답에 개인정보가 있을 수 있어 비공개 보관/공유 Sanitization 구분 필요.
10. Analyzer 입력: 관찰된 개요/신청방법/기간/대상/분류/태그와 원문/파일 참조. Source/입력 Version과 연결.
11. Snapshot: 실제 JSON 구조로 동일 Normalize 진입 가능. 현재 마스킹 샘플은 구조 확인용으로 실제 의미분석 검증은 별도.
12. 수정할 가정: 공식 예시가 실제 wrapper와 동일하다는 가정 제거, 수정시각 필드 활용은 검증 전 후보로 유지. 핵심 시스템 경계 변경 불필요.

**최종 답: NO (전체 구간을 추측 없이 확정하기에는 부족).** 목록 → 내부 Notice의 관찰된 필드와 검토 경로는 근거 있게 작성 가능하나 전체 Pagination, 변경감지 보장, 원문/첨부 다운로드와 서식 분석 입력은 추가 검증이 필요하다. 이 미확정 경계를 명시한 E2E 초안은 작성할 수 있다.

## 7. 산출물과 보안 한계

Probe, 사용설명, observations, 페이지별 1건의 Sanitized Sample 2개, 이 분석문서만 생성했다. 실제 Key/인증 Header/문의처를 기록하지 않는다. Raw는 메모리에서 분석하고 공유 샘플은 문자열을 보수적으로 마스킹했다. 샘플의 updtPnttm 값은 마스킹되어 있고 존재/타입은 observations에 남는다.
이 Probe의 안전장치는 Production 보안 설계나 Collector 구현을 대체하지 않는다. 기존 기준문서 변경, 패키지 설치, DB/Schema 생성, 대량수집, Git add/commit/push/Branch 변경은 하지 않았다.
