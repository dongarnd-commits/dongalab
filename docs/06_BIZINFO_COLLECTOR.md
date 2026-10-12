# DATCO 정부지원사업 운영체계 - Bizinfo Collector Design

## 1. 목적 / 기준 / 범위

기업마당 지원사업 API 하나를 안정적으로 수집하여 Raw Source/Provenance → Normalize → Notice/NoticeVersion → Intelligence → Operations로 전달하는 구현 기준이다. 목록·상세·첨부 확보, 중복방지, 변경감지, 부분실패/재시도와 Snapshot fallback을 정의한다. Production Collector 코드는 이번 문서에 포함하지 않는다.

기준 순서는 [AGENTS](../AGENTS.md) → [00 Baseline](00_PROJECT_BASELINE.md) → [01 Architecture](01_SYSTEM_ARCHITECTURE.md) → [02 E2E](02_E2E_SYSTEM_FLOW.md) → [03 Data](03_DATA_MODEL.md) → [04 State/Action](04_STATE_ACTION_MODEL.md) → [05 Permission](05_PERMISSION_UI_MATRIX.md) → 실제 [1차 Probe](../tools/bizinfo-probe/ANALYSIS.md)/[2차 Probe](../tools/bizinfo-probe/PHASE2_ANALYSIS.md) → 이 문서다. Probe는 외부 Interface 사실의 근거이며 Domain을 자동 변경하는 권한이 아니다.

실제 DB/ORM, Queue/Cron/Cloud 제품, API Route/HTTP Error 형식, UI 상세, OCR/LLM, HWP/HWPX Parser, 다른 기관 API와 DMP 계약은 확정하지 않는다. Modular Monolith 경계를 유지한다. 전국 기관 Connector, 범용 Crawler/ETL/Rule/Workflow 플랫폼, Microservice·Kafka·Kubernetes·분산 Scheduler를 전제하지 않는다.

## 2. 실제 API 근거와 미확인 범위

아래 사실은 2026-10-12 Probe의 제한된 관찰이다. 전체 공고/모든 Parameter/시간대/장기 운영을 보장하지 않는다. 이번 설계에서 추가 API 호출은 하지 않는다.

| 항목 | 관찰된 사실 | 해석 제한 |
| --- | --- | --- |
| Endpoint | GET `https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do` | 다른 Endpoint를 추정하지 않음 |
| 인증 | Query `crtfcKey`, Backend Key로 성공 | 인증실패 응답 구조 미확인 |
| 응답 | `dataType=json`, HTTP 200, `{ "jsonArray": [...] }` | `jsonArray.item`으로 고정하지 않음 |
| Pagination | `pageIndex`, `pageUnit`, `searchCnt` | Cursor 미관찰; 모든 searchCnt 의미 미확정 |
| 종료 관찰 | searchCnt=0/pageUnit=2, totCnt=1423, pageIndex=712에 1건, 713에 빈 배열 | 1423은 당시 값이며 전체 중간 Page 순회는 미실행 |
| ID | `pblancId`와 상세페이지 공고 ID 연결 | 내부 Notice ID와 분리, 장기 안정성 미검증 |
| 상세 | API의 pblancUrl로 200/text/html, 대상 ID·파일 참조 확인 | 전체본문 추출/Selector/완전성 미검증 |
| 파일 | API의 flpthNm/printFlpthNm URL로 200, PDF prefix 확인 | 전체파일 검증/내용·역할·다중첨부 미검증 |
| 파일 응답 | application/octet-stream, Range 요청에도 200 | MIME만으로 PDF 판정 불가; Range/206 지원 추정 금지 |
| 수정신호 | 3개 공고에서 creatPnttm/updtPnttm이 다름 | 동일 공고 변경 전후/모든 변경의 갱신 보장 미검증 |
| Empty | 200 + jsonArray=[] | 정상 Empty이며 오류 아님, 빈 배열에는 totCnt 없음 |
| 오류/제한 | Rate Limit/Retry-After 확정 근거 없음 | 제한 없음이라는 뜻 아님; 429/5xx/오류코드 미검증 |

1차의 22필드는 두 공고에서 값이 있었지만 2차의 마지막 공고 flpthNm은 비어 있었다. 결측을 수용한다. 상세 HTML/파일 접근 성공은 자료 전체 확보 또는 Analyzer 입력 충분성을 증명하지 않는다. Probe의 30초/64byte 검사는 Production timeout/파일크기/검증 기준이 아니다.

## 3. 책임 / 최소 구현 경계

| 경계 | 책임 | 전달 결과 |
| --- | --- | --- |
| Bizinfo Connector | Secret 적용, fetchPage/fetchDetail/fetchAttachment, HTTP/형식/안전경계 | 응답 또는 분류된 실패, Source Metadata |
| Collector Application | 요청·Job/Page 진행, Raw 보존, Normalize/비교 조정, 확보/Retry/Snapshot | 수집근거·처리결과, Notice Domain 요청 |
| Notice Domain | 내부 Notice ID/Root, Version 생성·보존/현재 선택, Version별 원천 연결 | Notice/불변 NoticeVersion, 변경 관계 |
| File 경계 | 실제 Content 확보·검증·보관, 불변 FileAsset/StorageReference | URL 참조와 구분한 확보 파일 |
| Intelligence | 본문/파일 추출·분류, Requirement Candidate/Reason/Evidence | 검토 후보/입력 Version |
| Operations | Human Review, Confirmed Requirement, Impact 검토 | 사람 확인 업무결정 |

Collector는 Eligibility/지원가능 여부/필수서류/평가기준을 최종 확정하거나 다른 Domain 저장소를 직접 수정하지 않는다. Raw Source Field → Normalized Value → Confirmed Notice Requirement를 구분한다.

개념 모듈은 `collector/bizinfo`의 connector/parser/normalizer/detail-acquirer/attachment-acquirer, `collector/application`의 collect-use-case, `collector/domain`의 collection-job/result, Snapshot Import Adapter 정도다. 실제 Folder/Programming Interface는 Stack 결정 후 조정한다. GovernmentSupportSourceConnector의 의미 경계만 두고 현재 BizinfoConnector 하나를 대상으로 한다. 다른 Source는 SourceSystem/Raw Provenance/Normalize 결과 경계로 확장하며 Domain이 Bizinfo 필드명에 직접 의존하지 않게 한다.

## 4. Secret / 요청 / Job / Permission

필수 Secret은 Project Root `.env`의 `BIZINFO_API_KEY`다. Backend에서만 읽고 `.env.example`의 `BIZINFO_API_KEY=` 형태를 유지한다. Key를 Source/Frontend/Raw Payload/Snapshot/Audit에 넣거나 crtfcKey 포함 전체 URL/원문 Error로 출력하지 않는다. 요청조건 저장 전 인증 Query를 제거하며 API 응답/오류가 Secret을 반사해도 저장·로그에 남지 않도록 검사·차단한다. 불필요한 환경변수를 대량 추가하지 않는다.

1차 필수 Trigger는 DATCO_OPERATOR Manual Sync다. 05의 REQUEST_COLLECTION/G-AUTH를 Backend에서 검사하고 Source/입력범위를 확인한다. ADMIN은 OPERATOR를 자동 상속하지 않으며 EDITOR/APPROVER는 Collector 운영 불가다. 실제 HTTP/Page/Normalize/비교 실행은 System/Worker다.

CollectionJob에 Source, dataType, searchCnt, pageUnit, 시작/요청 Page 범위, 요청시각/Actor, LIVE 또는 SNAPSHOT Mode와 비밀 제외 조건을 남긴다. authenticationApplied 같은 표시가 필요해도 Key 값은 저장하지 않는다. Human Request Collection과 Worker Run Collection, 내부 Normalize Item/Compare Notice/Acquire Detail/Acquire Attachment를 분리한다.

03의 SourceSystem, CollectionJob, BackgroundJob, JobAttempt, CollectionPage를 재사용한다. 04대로 REQUEST_COLLECTION → QUEUED → START_JOB/새 Attempt → PROCESSING → SUCCEEDED/PARTIAL/FAILED다. Retry는 기존 terminal Attempt를 보존하고 새 Attempt로 실행한다. 중단된 PROCESSING은 RECOVER_INTERRUPTED_JOB에서 실행소유/완료근거를 확인하며 자동 성공으로 바꾸지 않는다.

Manual Snapshot Import는 같은 수집 Use Case의 SNAPSHOT 입력 요청으로 OPERATOR의 REQUEST_COLLECTION 권한을 검사·Audit한다. 일반 업무데이터 Import/Export의 ADMIN 권한과 구분한다. Retry Human 요청도 원 수집의 OPERATOR 권한/대상범위를 재검사하고 04 RETRY_JOB 경로로 Audit한다. 별도의 관리자 bypass는 없다. 향후 Scheduler는 승인된 실행주체/조건으로 동일 Job 경로를 호출하며 제품·주기와 신규 Human Role을 만들지 않는다.

## 5. Pagination / 종료 / 일관성

1차 구현 후보는 **순차 Page 수집**이다. 검증된 searchCnt=0 조건을 기본 출발점으로 사용하고 pageUnit은 요청조건으로 명시한다. Probe의 pageUnit=2는 관찰 근거이며 Production 효율값/허용 최대치로 확정하지 않는다. 무제한 호출을 막을 timeout/실행 Page 상한은 필수 구성 의미이며 숫자는 구현 검증 후 정한다.

1. pageIndex=1을 요청하고 HTTP 성공, JSON 객체, jsonArray 배열을 검증한다. 200 HTML/JSON 파싱실패/Wrapper 불일치는 Empty로 해석하지 않는다.
2. Page 결과·시각·조건·Raw를 기록한다. 배열이 비어 있으면 정상 Empty를 기록한다. 첫 Page도 Empty일 수 있지만 이전 저장 Notice를 삭제하지 않는다.
3. 항목에서 유효한 totCnt를 읽을 수 있으면 `ceil(totCnt/pageUnit)`으로 마지막 **후보**를 계산한다. 음수/비정수/항목별 불일치는 경고로 남긴다. 결측이면 count 근거 부족을 기록한다.
4. 각 Item을 독립 검증/정규화/매핑하고 observed count, unique external IDs, duplicate count를 누적한다. 같은 ID의 내용 충돌도 기록한다.
5. Short Page만으로 즉시 완전수집 판정하지 않고 다음 Page의 Empty를 확인한다. 예상 마지막 Page가 가득 차거나 total이 달라지면 실제 배열과 갱신된 기대치를 대조하며 상한 내에서 진행한다. totCnt가 없어도 Empty 또는 실행 상한까지 순회 가능하다.
6. Empty는 종료 신호다. 예상 마지막 이전의 Empty/total 변동/반복 ID 집중/건수 불일치는 전체 범위 일관성 경고로 기록한다. 실패한 Page를 성공처럼 건너뛰고 완료하지 않는다.
7. 종료 시 initial/latest expected count, observed count, unique IDs, duplicates, Short/Empty 관찰, 실패 Page, 처리 결과를 대조한다. 지정 일부 Page 실행은 해당 범위 완료로만 보고한다.

예상 건수와 unique count 일치도 원천의 시점 일관성 보장은 아니다. 수집 중 추가/삭제/정렬변동은 미확인이다. 전체 요청의 정상 종료·오류 없음·관찰 근거 일관성은 기술적 완료 기준이며 “원천 전체가 정확히 한 시점으로 완전수집됨”이라고 선언하지 않는다. 같은 Page/ID가 반복되어 진행이 없거나 상한에 닿으면 중단·PARTIAL/FAILED로 기록하고 검토한다. 누락 의심은 후속 새 수집/대조 후보이며 이번 설계에서 무한 재순회하지 않는다. 이번 실행에서 안 보인 공고를 삭제/마감으로 자동 판정하지 않는다.

## 6. Raw / Provenance / Normalize

RawSourceRecord는 SourceSystem/CollectionJob/CollectionPage, collectedAt, HTTP 상태/format, 비밀 제외 Request Condition, 원천 Payload 또는 비공개 참조, Item 위치/External ID, Parser/Normalizer 입력 규칙 Version을 추적한다. Page Payload와 Item의 위치 관계를 보존하며 식별 실패 Item도 Raw에서 찾을 수 있어야 한다. Raw는 불변 원천근거이고 분석결과가 아니다.

Production Raw에는 문의처/개인정보가 있을 수 있으므로 비공개 보관·권한검사·Retention 정책을 적용한다. 공유 Fixture는 별도 Sanitization을 수행한다. 실패 HTTP/비정상 Content도 안전한 상태/분류만 기본 기록하고 원문 보존이 필요하면 Secret 제거와 비공개 검증을 먼저 수행한다.

Normalize는 Raw Item → Validate → Source Mapping → Normalize → Compare → Notice Domain 전달 순서다. pblancId 결측/형식 불가 Item은 정상 Notice import를 차단하고 ID_MISSING 후보 오류로 격리한다. 다른 필드 결측/파싱 실패는 원문/상태와 함께 FIELD_PARSE_PARTIAL로 전달하고 전체 공고를 무조건 폐기하지 않는다. Error Category 이름과 아래 Attribute는 논리 후보이며 DB Column/API 상수가 아니다.

문자열 공백/개행/인코딩 처리와 비교 규칙을 Version으로 추적한다. HTML 문자열은 원문을 보존하고 UI에서 안전하게 표현하며 임의 삭제/과도한 정규화로 업무변경을 숨기지 않는다. 알 수 없는 Field는 Raw에 보존하고 Wrapper/필수 ID 오류와 구분한다.

## 7. 실제 Field Mapping / 업무 Version 비교

`핵심`은 Normalized 업무내용 비교 포함, `참조`는 원천/파일 참조와 검증된 내용 비교, `신호`는 확보/비교 후보 판단용, `제외`는 업무 Version 생성에서 제외다. 비교값 변경은 Change Candidate이며 최종 생성은 8절의 의미 판정에 따른다. `필수 ID` 외 모든 값의 결측 가능성을 수용한다. 1차 타입은 inqireCo/totCnt 숫자, 나머지 문자열로 관찰되었으며 미확인 타입은 검증 대상으로 분류한다.

| Source Field | 의미 | Normalized Domain Attribute 후보 | 필수/결측 | Version 비교 |
| --- | --- | --- | --- | --- |
| pblancId | 외부 공고 ID | externalNoticeId | 필수 ID, 누락 import 차단 | Mapping identity, 내용 비교 제외 |
| pblancNm | 공고명 | title | 결측 표시 | 핵심 |
| jrsdInsttNm | 소관기관 | jurisdictionInstitution | 결측 허용 | 핵심 |
| excInsttNm | 수행기관 | executingInstitution | 결측 허용 | 핵심 |
| creatPnttm | 원천 등록시각 | sourceCreatedAtOriginal/candidate | 결측/시간대 미확정 | 제외: Provenance 유지 |
| updtPnttm | 원천 수정시각 | sourceUpdatedAtOriginal/candidate | 결측/변경보장 미확정 | 신호, 단독 생성 금지 |
| reqstBeginEndDe | 신청기간 원문 | periodOriginal/startCandidate/endCandidate/parseStatus | 결측/예외형식 허용 | 핵심: 원문과 파싱 의미 |
| trgetNm | 지원대상 | targetDescription | 결측 허용 | 핵심 |
| pldirSportRealmLclasCodeNm | 지원분야 대분류 | supportMajorCategory | 결측 허용 | 핵심 |
| pldirSportRealmMlsfcCodeNm | 지원분야 중분류 | supportMinorCategory | 결측 허용 | 핵심 |
| hashtags | 태그/지역 후보 | tagsOriginal/normalizedTags | 결측 허용, 지역 확정 금지 | 핵심: 비교 규칙 적용 |
| bsnsSumryCn | 사업개요 | summarySourceContent | 결측 허용, 전체본문 추정 금지 | 핵심 |
| reqstMthPapersCn | 신청방법 표현 | applicationMethodSourceContent | 결측 허용 | 핵심 |
| refrncNm | 문의/참조 표현 | contactReferenceOriginal | 결측 허용, 민감정보 주의 | 핵심, Private Raw/안전한 UI |
| rceptEngnHmpgUrl | 접수기관 홈페이지/신청 링크 | applicationReferenceUrl | 결측/URL 검증 | 참조, 자동 외부수집 없음 |
| pblancUrl | 상세 공고 링크 | detailSourceReference | 결측/대상 관계 검증 | 참조: URL 및 확보 Source 변화 |
| flpthNm | API 첨부 경로 | attachmentSourceReference | 결측 실제 관찰 | 참조: 별도 Source Role 후보 |
| fileNm | 첨부 이름 Metadata | attachmentOriginalName | 결측 허용, 안전한 저장명 분리 | 참조 Metadata |
| printFlpthNm | 본문출력파일 경로 | printSourceReference | 결측 허용, 역할 미확정 | 참조: 별도 Source Role 후보 |
| printFileNm | 본문출력파일 이름 | printOriginalName | 결측 허용 | 참조 Metadata |
| inqireCo | 조회수 | observedViewCount | 결측 허용 | 제외 |
| totCnt | 응답 범위 전체건수 | pageReportedTotal | 빈 배열에는 없음 | 제외: Page 실행근거 |

reqstBeginEndDe의 실제 `2026-10-01 ~ 2026-10-23`, `2020.01.01 ~ 2026.12.31` 형식을 파싱 후보로 지원한다. 원문·구분 결과·실패 이유를 유지하고 존재하지 않는 날짜/시각/시간대를 만들지 않는다. 자동 파싱은 Confirmed Requirement가 아니다. 상시접수/예산소진/조건부기간은 아직 미관찰이므로 후속 예외 Fixture 및 사람 확인 대상이다.

## 8. External ID / Idempotency / NoticeVersion / Impact

SourceSystem + pblancId → ExternalNoticeMapping → Internal Notice를 사용한다. 같은 Source+ID는 하나 Notice Root에만 연결하며 제목이 같아도 자동 병합하지 않는다. Notice ID는 Notice Domain이 부여한다. 기존 Mapping은 비교 경로로, 신규는 IMPORT_NEW_NOTICE로 전달한다.

같은 Page 재요청, 반복 Item, 버튼 재클릭, Job Retry/Worker 재시작, 동일 Snapshot Import에서 같은 내용의 Notice/Version을 중복 생성하지 않는다. 동일 Human Action Identity 재전송은 04대로 현재 권한/Scope를 확인한 후 기존 요청 결과를 반환하고 의도적인 새 Sync는 별도 Job/수집이력이 가능하다. Item 단위 Source+ID와 의미내용 비교는 새 Job에도 적용한다. 같은 실행에서 동일 ID·상이한 내용은 순서만으로 임의 덮어쓰지 않고 충돌을 기록/비교한다.

변경 절차는 updtPnttm 신호 확인 + 핵심 Normalized Content/기간 + Attachment Metadata + 확보된 Detail/File 내용 비교 → Change Candidate → 의미판정 → CREATE_NOTICE_VERSION 또는 KEEP_EXISTING_VERSION이다. 수정시각이 같아도 목록 핵심내용은 비교하고, 수정시각만 달라지고 의미내용이 같으면 Version을 만들지 않는다. 조회수/totCnt/수집시각/Job ID/저장위치 변화는 업무 Version 조건에서 제외한다. Hash를 쓴다면 위 비교 범위·규칙 Version이 먼저이며 알고리즘은 Open Decision이다.

URL이 같아도 실제 확보 내용이 달라질 수 있다. 재확보한 불변 FileAsset의 내용 차이는 비교 근거이며 확보 실패/미확보를 기존 내용의 삭제로 해석하지 않는다. 성공한 응답의 명시적 참조 제거와 누락/형식오류는 구분한다. 의미가 불명확하면 비교 보류/검토 사유를 남긴다. 전체 HTML의 공통 메뉴/동적 Metadata만으로 업무 Version을 만들지 않으며 본문 비교 범위는 07의 Source 분류/추출 경계와 연결한다. 미확인 Selector와 파일 재확보 주기로 모든 변경을 잡는다고 보장하지 않는다.

새 Version은 당시 Raw/Normalized 비교 규칙/Source·File 연결과 이전 Version 관계를 보존한다. 기존 Version 내용을 덮어쓰지 않고 Notice Domain이 현재 Version을 선택한다. 미완전 Source는 확보범위를 명시한다. Source 보강이 실제 새 업무내용을 제공하면 새 Version 후보이고 동일 내용 재확보/저장 성공만으로 중복 Version을 만들지 않는다. 확보 이력과 불변 Version 참조를 분리하고 과거 분석이 실제 사용한 File ID를 바꾸지 않는다.

새 NoticeVersion → Change Event/Impact Candidate → 04 ImpactAssessment/ImpactTarget → Human Review → Reanalysis/Re-review/Reapproval로 연결한다. 기존 Proposal/Case/Approval을 자동 변경하지 않는다. 영향은 실제 적용관계로 판별하고 Impact 검토 완료와 후속조치 완료를 구분한다.

## 9. Detail / Attachment / 파일 안전경계

Detail은 API pblancUrl을 사용한다. 공식 Bizinfo HTTPS Domain, 대상 pblancId 관계를 검사하고 HTML 확보 결과·시각·HTTP/형식·SourceReference/Content 참조를 남긴다. SourceReference → 실제 확보 FileAsset(HTML 논리 Content 가능) → FileStorageReference로 구분하고 NoticeSourceReference의 Version 관계를 유지한다. 본문 추출 Selector/완전성 판단은 07과 후속 검증에 남긴다.

Attachment는 flpthNm/printFlpthNm의 **API 제공 URL을 그대로 사용**한다. atchFileId/fileSn 규칙으로 URL을 조합하지 않는다. 두 Source Field/Role Candidate를 각각 보존하고 print file을 신청서식/전체본문으로 확정하지 않는다. Source URL/Role Candidate/원본 Filename Metadata/HTTP Result/Content-Type/검증/확보 FileAsset/NoticeVersion을 추적한다. URL 존재 ≠ 실제 파일 확보 ≠ 추출 성공 ≠ Requirement 확인이다.

03의 NoticeAttachmentReference는 여러 개 가능하지만 Bizinfo 다중첨부 표현은 미확정이다. 미확인 배열/구분자 Parser 또는 HTML href 전부를 첨부 목록으로 만들지 않는다. API가 준 확인된 참조만 기본 확보하고 HWP/HWPX/압축파일은 후속 지원범위 검증으로 남긴다.

Production 다운로드는 공식 Host 허용, HTTPS/포트/URL 검증, Redirect 각 대상 재검사, 사설·로컬 주소 접근 차단, timeout/최대 전송크기, Streaming/실제 수신량 제한, Content-Type + File Signature 검사, 저장 실패/불완전 파일 격리, 중복 Content 식별을 요구한다. 외부 신청 링크는 자동 다운로드 대상이 아니다. Header의 Content-Length/Range 지원만 신뢰하지 않으며 크기·시간 숫자는 근거 확인 후 설정한다. Filename은 Metadata로 보존하되 경로 이동/스크립트 실행에 사용하지 않고 안전한 저장키를 사용한다. HTML/바이너리를 실행하지 않는다.

실제 바이트가 바뀌면 새 FileAsset이고 기존 ID를 덮어쓰지 않는다. 동일 내용의 중복 보관은 식별 가능하게 하되 Notice/Source 귀속을 보존한다. 저장 성공·검증 완료 전에는 확보 성공으로 표시하지 않는다. Global Notice Source와 Company Private File 접근을 분리하고 Global 원천이라도 Raw 개인정보/운영 로그는 기업에게 자동 공개하지 않는다.

## 10. 결과 분류 / Retry / 일관성 경계

SUCCEEDED는 지정된 범위·확보 작업이 끝나고 안전하게 저장·검증되었으며 실패/미처리/미해결 일관성 경고가 없는 기술적 결과다. 본문 의미 추출/Requirement Confirmed/Match Ready/Proposal Ready를 뜻하지 않는다. 첨부 참조가 없으면 NOT_PROVIDED 의미로 기록하고 필수 다운로드 실패와 구분한다. 아래 세부 표시는 결과 분류 의미이며 새로운 Job State를 추가하지 않는다.

| 상황 | Job 결과 기준 | 복귀/기록 |
| --- | --- | --- |
| 정상 Empty, 요청범위와 모순 없음 | SUCCEEDED 가능 | Empty Page 기록, 기존 Notice 삭제 없음 |
| 목록 성공/Detail 실패 | PARTIAL | Notice 유지, 해당 Source 확보 재시도 후보 |
| 목록 성공/Attachment 실패 | PARTIAL | 참조·실패 보존, 해당 파일 재확보 후보 |
| 일부 Page 성공/일부 Page 실패·중단 | PARTIAL | 성공 저장 유지, 실패/미수집 범위 명시 |
| Raw 성공/일부 Item Normalize·ID 오류 | PARTIAL | 실패 Item 격리, 다른 Item 처리 유지 |
| Notice 저장 성공/Source 보강 실패 | PARTIAL | 저장 Notice/Version 유지, 확보 실패 별도 |
| 전체 범위 일관성 경고/상한 도달, 일부 정상 처리 있음 | PARTIAL | 누락 의심/중복/total 변동 검토 |
| Key/입력 설정 불가, 첫 응답 형식불가 등 실행 진행 불가 | FAILED | 안전한 원인, 구성/Parser 수정 필요 |
| 모든 Item import 실패, 정상 Empty가 아님 | FAILED | Raw 확보 사실은 별도 유지 |
| 핵심 저장/감사 일관성 보장 불가 | 성공 선언 금지; 부분 보존 가능 시 PARTIAL, 아니면 FAILED | 완료근거 재조정/복구 검토 |

기존의 성공 Notice가 있다는 이유만으로 이번 실패 Job을 PARTIAL로 만들지 않는다. 이번 Attempt의 실제 정상 처리·보존 범위로 판단한다. Partial/Failure는 정상 결과를 무조건 Rollback하지 않는다.

| 실패 종류 | Retry 판단 후보 | 경계 |
| --- | --- | --- |
| Network timeout/일시 연결·서버 실패 | Retry Candidate | 실패 Page/Source 단위 또는 새 실행, 호출상한 준수 |
| 실제 429/5xx/Retry-After를 향후 관찰 | 서버/정책 근거 확인 후 Retry Candidate | 현재 Bizinfo의 동작/숫자는 미확인 |
| 인증/Parameter 구성 오류 | 구성 확인 | Key를 반복 변경하거나 무한 Retry하지 않음 |
| Wrapper 불일치/ID 누락/영구 파싱문제 | Review/Code Fix Candidate | 동일 입력 반복으로 해결 추정 금지 |
| 파일 형식/크기/Host 안전검사 실패 | 정책/원천 검토 | 안전검사 우회 금지 |
| 저장 일시실패/Worker 중단 | 완료근거 대조 후 복구/Retry | 성공 Item/Version 중복 생성 금지 |

Retry Count/Backoff/Jitter/호출 Rate 숫자는 확정하지 않는다. 제한이 없다고 가정하지 않고 1차 순차 요청·불필요한 재호출 억제·호출횟수 관찰을 기본으로 한다. Retry는 Attempt 오류를 보존하고 대상/조건을 명시한다. 변동 Page는 과거 실패 Page만 재요청했다고 전체 범위를 일관되게 회복했다고 선언하지 않으며 필요 시 새 전체 수집/대조한다.

한 Item 실패가 다른 정상 Item을 제거하지 않는다. Notice Root와 Mapping 생성, Version과 생성근거/참조, 중요한 변경과 Audit/Impact 연결은 일관되게 보장한다. 동시 import에서도 Source+ID와 동일 내용 Version이 중복되지 않게 한다. 물리 Lock/Transaction/Queue는 구현 선택이며 전체 Job을 하나의 거대한 Transaction으로 묶지 않는다. Job 요약은 저장된 Page/Item/확보 결과와 일치해야 한다.

## 11. Live / Snapshot / Manual Sync / 관측

Live Connector → Raw Source, Snapshot Import → 같은 Raw Source 형식 → **동일 Parser/Normalizer/Mapping/비교/Notice Domain** 경로를 사용한다. Snapshot만 완성 Notice를 DB에 직접 넣거나 승인/분석결과를 자동 주입하지 않는다. Mode/원래 Source/관찰시각/Import 시각/Fixture 식별을 구분하고 운영중인 최신 데이터가 오래된 Snapshot으로 자동 후퇴하지 않도록 실행 대상을 격리한다. Demo의 Local 데이터 범위에 Import하며 Live 실패를 Snapshot 성공으로 덮어쓰지 않는다.

Snapshot은 검증·Sanitization된 구조/원천을 입력으로 사용한다. 동일 Source+External ID는 같은 매핑 정책을 통과하고 재Import는 중복 Root/동일 Version을 만들지 않는다. 포함된 HTML/파일 자산은 같은 검증/확보 기록 경로에 연결하며 미포함 자료를 확보 성공으로 위장하지 않는다. API Key/PII가 섞인 Snapshot은 import/share 전에 차단한다.

현재 sample-page1/2는 자유텍스트가 마스킹된 구조 Fixture다. Parser 회귀 근거로 사용 가능하지만 의미 있는 Notice/Form Analysis/E2E Demo에 충분하다고 가정하지 않는다. 09 Demo에서 의미검증된 Sanitized 원천/파일 Fixture를 준비할 수 있다. Snapshot fallback은 명시적 Mode 선택이며 자동 조용한 전환을 기본으로 하지 않는다.

Manual Sync는 요청 결과/Job 진행/완료 요약을 제공하고 기존 Notice 조회와 분리한다. 향후 Scheduler도 같은 CollectionJob/Collector/Normalize를 사용하고 별도 Batch 업무로직을 만들지 않는다. UI 세부는 08로 넘긴다.

운영 관측은 요청·실행 시작/종료시각, Source/Mode/Actor, 요청 Page 범위/조건, 수집 Page 수/호출횟수, Raw Item/unique ID/duplicate/기대건수, 신규·기존 Notice/새 Version/변경없음, Item Partial/Failed, Detail/Attachment 성공·실패, Retry Attempt/미처리 범위를 포함한다. 숫자 합계와 실제 결과를 대조할 수 있어야 한다.

REQUEST_COLLECTION/Manual Snapshot Import/Retry 요청은 Human Audit, System 실행은 CollectionJob/JobAttempt/Page Result/Notice import·Version 결과로 추적한다. Log는 Source/Job ID/Page/필요 External ID/Error Category/Attempt/시각 중심이다. Key·전체 인증 URL·개인 연락처 원문·민감 Raw/Private File 내용·원문 Error를 복제하지 않는다. 민감정보 없이 Debug할 수 있는 상관관계를 유지한다.

## 12. 구현순서 / Probe 관계 / Test Matrix

권장 구현순서는 Bizinfo Connector → Raw Fetch/Pagination → Raw Provenance → Normalizer → Source+ID Mapping → 신규 Notice → 기존 비교/NoticeVersion → Detail → Attachment → Partial/Error/Retry → Snapshot Import → Manual Sync 연결 → 통합 Test다. 오류·보안·Unit/Fixture 검증은 각 단계에서 함께 수행한다. Scheduler/다른 Source부터 만들지 않는다.

`tools/bizinfo-probe/`는 실제 API 구조/회귀/향후 변화 조사 도구로 유지한다. Production Collector는 Application 기능이며 Probe를 무리하게 병합하지 않는다. 관찰된 Field/Response를 근거로 재사용하되 Probe의 최소 검사와 Production 확보/영속성/안전요건을 구분한다.

아래는 **구현 후 실행할 Test 기준**이며 이번 문서 작업에서 API/Test 실행을 완료한 뜻이 아니다. Unit/Fixture는 외부 호출 없이 기본 수행하고 Integration은 승인된 제한 범위의 Live/저장/File 경로로 분리한다. 모든 Test에서 외부 API를 호출하지 않는다.

| Test | 입력 / 유형 | 기대결과 |
| --- | --- | --- |
| A 1 Page 정상 | 실제 Wrapper Fixture + 제한 Live Integration | Raw/Item/Notice 저장·근거 연결 |
| B 여러 Page | Page Fixture | 순차 순회/건수·ID 누적 |
| C 마지막 Short | short Page Fixture | 다음 종료검증 진행 |
| D 다음 Empty | 200/jsonArray=[] Fixture | 정상 종료, 오류와 구분 |
| E 동일 공고 재수집 | 같은 ID/내용 | 같은 Root/Version, 수집이력 보존 |
| F 새 공고 | 미매핑 Source+ID | Mapping/Root/최초 Version 일관 생성 |
| G 변경 없음 | 조회수/totCnt/수정시각만 변화 | 업무 Version 생성 안 함 |
| H 변경 후보 | 기간/핵심내용/검증된 파일 차이 | 의미판정→새 Version 또는 보류, 이전 보존 |
| I 첨부 없음 | flpthNm 빈값 | NOT_PROVIDED, 정상 목록 유지 |
| J Detail 실패 | HTTP/형식/ID 불일치 주입 | PARTIAL/안전한 실패·재확보 경로 |
| K Attachment 실패 | 저장/크기/Signature 실패 주입 | 성공 FileAsset 표시 금지/PARTIAL |
| L 일부 Page 실패 | 중간 Page 오류 | 성공 Item 유지, 누락범위/PARTIAL |
| M Snapshot Import | Sanitized Raw Fixture | 같은 수집근거/매핑/Version 경로 |
| N Live/Snapshot 동일 Normalize | 동일 Raw 입력의 두 Mode | 동일 Normalized 업무내용/Mode 구분 |
| O Key 노출 없음 | 가짜 Secret 반사/인증URL/원문 Error 주입 | Log/Raw/Audit/Snapshot에 Secret 없음 |
| P 중복 Job/Retry | 같은 요청 재전송/중단 재실행 | 요청 중복 억제/Attempt 보존/성공 Item 중복 없음 |
| Q Source+pblancId 중복 없음 | 동시 저장 Integration | 하나 Mapping/Notice, 같은 내용 중복 Version 없음 |
| R Change Impact | 새 Version 생성 후 저장 경로 | 원천→Version→Impact 추적, 기존 Decision 자동변경 없음 |

추가 Fixture로 totCnt 결측/변동·반복 ID·조기 Empty·실행상한, ID 누락/타입오류, 기간 예외, URL Redirect/사설주소/경로이동, Snapshot 오래된 입력, Raw 저장/감사 실패를 검증한다. 미관찰 예외 Fixture는 API 실제 동작 증명과 구분한다.

## 13. 정합성 Validation A~T / Conflict

문서상 검토 결과다. 실제 Collector/다운로드/DB/권한 실행 테스트는 후속 구현에서 수행한다.

| 검증 | 근거 | 결과 |
| --- | --- | --- |
| A Endpoint/인증/Wrapper | 2절 실제 GET/crtfcKey/jsonArray | 반영 |
| B Backend Secret | 4절 Key 경계 | 반영 |
| C pageIndex/pageUnit | 2/5절 관찰과 후보 알고리즘 구분 | 반영 |
| D totCnt 고정·완전성 오해 금지 | 당시 1423/일관성 검사/시점보장 없음 | 반영 |
| E Empty 정상 | HTTP 성공+배열 검증 후 Empty | 반영 |
| F 외부/내부 ID 분리 | Source+pblancId→Mapping→Notice | 반영 |
| G 재수집 중복 금지 | Root/의미내용 idempotency | 반영 |
| H Raw/Normalize 분리 | Raw 불변 근거/정규화 규칙 | 반영 |
| I 기간 원문 보존 | 두 실제 형식/파싱 후보 | 반영 |
| J updtPnttm≠Version | 신호+내용 의미판정 | 반영 |
| K inqireCo/totCnt 제외 | Field Matrix | 반영 |
| L pblancUrl Detail | 관계검사/HTML 확보 | 반영 |
| M API 파일 URL 사용 | 임의 조합 금지 | 반영 |
| N URL≠확보 | SourceReference/FileAsset/추출 구분 | 반영 |
| O Partial/Failed | 10절 Classification Matrix | 반영 |
| P Rate/Retry 숫자 추정 금지 | 미확인 표시/Open Decision | 반영 |
| Q Live/Snapshot 동일 Normalize | 11절 공통 경로 | 반영 |
| R Version→Impact | 8절/04 업무 검토 경로 | 반영 |
| S 기술 성공≠Requirement 확정 | Collector/Intelligence/Operations 분리 | 반영 |
| T 범용 플랫폼 방지 | Bizinfo 하나/최소 Source 경계 | 반영 |

상위문서와의 Conflict는 발견하지 않았다. 실제 Wrapper가 공식 예시와 다른 것은 기존 Probe 근거를 반영하며 Domain 변경을 요구하지 않는다. 새로운 Entity/State/Role을 추가하지 않았고 03의 Source/File 관계, 04 Job/Notice/Impact Action, 05 Human/Worker 권한을 유지한다.

## 14. Open Decision / 착수 판단

| ID | 미확정 | 구현 출발점 / 확인 경계 |
| --- | --- | --- |
| OD-01 | DB/ORM 및 물리 일관성 방식 | 논리 Mapping/Version/Audit 정합성은 확정, Stack 선택 후 구현 |
| OD-02 | Queue/실행기 제품 | 단일 수집 Use Case/Attempt 경로, 분산 실행 전제 없음 |
| OD-03 | Scheduler 제품/주기 | Manual Sync 우선, 향후 같은 경로 |
| OD-04 | Retry Count/Backoff/Jitter | 실패 분류·Attempt 보존 확정, 숫자는 검증 후 설정 |
| OD-05 | 공식 Rate Limit/오류 응답 | 순차 호출/호출횟수 관측, 미확인 제한 없음 추정 금지 |
| OD-06 | searchCnt의 전체 의미/Production pageUnit | 관찰된 searchCnt=0로 출발, 실제 요청량 검증 후 결정 |
| OD-07 | 변동 Pagination 대조·재수집 세부 | 상한/일관성 경고/누락범위는 필수, 보정 방식 후속 확인 |
| OD-08 | Hash 알고리즘/상세 의미 비교·재확보 주기 | 핵심 업무필드 비교 확정, 파일/HTML 비교 범위는 07과 검증 |
| OD-09 | 다중첨부 실제 표현 | 확인된 두 참조만, 모델은 다수 허용 |
| OD-10 | HWP/HWPX/압축 등 지원 | 확보/분류/미지원 상태 구분, Parser는 07/실제 Fixture |
| OD-11 | HTML 추출 Selector/본문 완전성 | Collector 자료확보, 추출은 07 |
| OD-12 | 파일크기/timeout/실행상한 수치 | 제한 적용은 필수, 실제 측정 후 수치 결정 |
| OD-13 | Raw Retention/개인정보 상세정책 | Private Raw/공유 Sanitization 확정, 운영정책 후속 |
| OD-14 | 다른 Source Connector | 공통 Source/Raw/Normalize 경계만, 현재 상세설계 제외 |

**Collector 실제 구현 착수: READY.** 검증된 목록 입력, 핵심 Mapping/Raw/Normalize/idempotency/Version 및 실패·Source 확보 경로로 최소 구현을 시작할 수 있다. Production 배포 완료 판정은 아니다. Stack·안전제한 수치 선택과 미확인 API/파일 동작의 단계별 검증은 해당 기능 구현·배포 전 수행한다.

**07_INTELLIGENCE_DESIGN 전에 Collector 구현을 반드시 끝내야 하는가: NO.** Collector의 NoticeVersion/Raw/SourceReference/실제 확보 FileAsset 및 확보상태를 입력 경계로 07의 추출·분류·Candidate/Evidence/Human Review를 병행 설계할 수 있다. Fixture로 입력 계약을 검토하되 실제 자료 확보/추출 충분성·전체 E2E 완료는 후속 통합 검증으로 확인한다.
