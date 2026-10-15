# R-07 자동화 기반 범용 정부지원사업 조건 매칭 상세설계

- Date: 2026-10-14
- Status: **PROPOSED / NOT APPROVED FOR IMPLEMENTATION**
- 승인 근거: Decision-004 및 사용자 최종 통합 명령. 상세설계 작성 승인이며 운영용 스키마·평가기·추출 Provider·정책 구현 승인이 아니다.
- Source of Truth: AGENTS → docs/00 → 01 → 03/04/05/07/08/10/11. 00~10의 필수 Human Review/공식 승인 Guard와 연구원 Domain 소유권 유지.

## 1. 목표와 상태 구분 [APPROVED_DESIGN]

수요기업 자유입력/증빙 → 기업·문제 분석 → 실제 DMP 기능/Capability 탐색 → 서비스 조합 → 공고 원문/구조화 조건 → 기업·공급자 Fact 비교 → 근거·부족정보 → 기존 MatchReview → 승인된 제안/후속 업무로 연결한다. 제조업·충청·울산은 검증 사례이며 분기 코드나 전용 Domain을 만들지 않는다.

| 구분 | 의미 | 현재 범위 |
|---|---|---|
| EXISTING_IMPLEMENTED | 실제 소스 및 실행 테스트로 확인 가능한 기능 | Notice HTML/PDF 후보/Evidence/Human CONFIRM, ConfirmedNoticeReader, DMP Inventory/Capability/Composition, 단순 코드 IN/NOT_IN Comparator, Snapshot/Review/Guard, Decision-004 공통 계보 |
| APPROVED_DESIGN | 사용자가 상세설계 진행을 승인 | 자동 증빙/공고 구조화 파이프라인, 범용 AST/3값 논리, 지역/기간/예외·DTO/UI/Test 설계 |
| PROPOSED_IMPLEMENTATION | 구현 승인 후 개발할 구조 | ReviewedConditionVersion/AST 저장, 조건 검토 API, 범용 평가기/사전 Adapter, Fact Provider 실제 연결 |
| PENDING_POLICY | 업무 의미·자동화 확대·숫자/시간 등 미확정 | 완전성/예외/단위/경계/기준일/Code Mapping의 업무 승인 |
| PENDING_PROVIDER_CONTRACT | 연구원·외부 제공자 계약 확인 필요 | 실제 Fact/Site/Membership/Evidence/현재성·코드체계·문서 입력 계약 |

설계상의 TRUE/FALSE/UNKNOWN은 내부 평가 의미다. 새로운 Match State·Role·Permission을 만들지 않는다. 상세설계의 Acceptance는 NOT_RUN이며 현재 테스트 PASS에 더하지 않는다.

## 2. 세 판단 차원 [APPROVED_DESIGN]

A. 서비스 적합: ImprovementVersion × CapabilityVersion/Assessment × CompositionVersion/Coverage. 해결/부분 해결/미해결/전제조건을 근거로 표현한다.
B. 지원범위 적합: 제안 서비스의 실제 제공범위와 공고의 지원목적·지원분야·비용 범위 등을 비교한다.
C. 기업·공급자 자격: 정확한 신청 주체/사업장/공급자 Fact와 필수 조건·제외·기간·예외를 비교한다.

어느 차원도 문자열 유사도·임의 가중치 점수로 합산하지 않는다. 서비스 Label 일치가 자격을 증명하지 않는다. 회사의 Fact가 공급기업 자격을 대신하지 않는다. 한 조건의 TRUE 또는 제외 비해당만으로 전체 FIT/PROPOSABLE을 만들지 않는다.

## 3. 기업 증빙 자동 추출 [APPROVED_DESIGN / PENDING_PROVIDER_CONTRACT]

Company/Site Scope 확인 → 기존 파일 입력 Port → 원본 FileAsset/해시/Private Storage → 문서 유형 후보 → Text/PDF/Table 추출 또는 지원 가능한 OCR Adapter → 위치별 Evidence → 원문 필드 후보 → 속성/단위/코드 정규화 후보 → 문서/Fact 상호 정합성 검사 → 기존 FactReview → 불변 Confirmed CompanyFactVersion → Matching 소비.

OCR/LLM Provider는 선택·설치하지 않는다. 지원하지 않는 Scan/HWP/HWPX/ZIP 등의 자료는 처리 불가/추가 원문 필요로 기록하며 내용 추정이나 성공 표시를 하지 않는다. 사업자등록증/공장등록증/인증서/기업현황은 문서 후보 목록이며 실제 지원 포맷/필수 필드는 연구원 입력·파일 계약 확인 후 확정한다.

자동화는 후보 생성·반복 검증을 담당한다. 자동 추출값이 존재하거나 서로 일치한다는 이유만으로 Company Master/Confirmed Fact를 갱신하지 않는다. 기존 확인 계약에 필요한 FactReview를 거친다. 충돌 Source를 삭제·덮어쓰지 않는다. 원문 위치를 클릭하여 사람이 확인할 필드만 수정하도록 하며 전체 재입력을 기본 경로로 만들지 않는다.

### 추출 결과 계약 초안 [PROPOSED_IMPLEMENTATION]

| 정보 | 내용/검증 |
|---|---|
| source | 실제 file_id, digest, Company/Site owner, document_type 후보, 발급일·Source Provider |
| extracted | field/path, raw_value, exact quotation, page/표 cell/bounding region/HTML descriptor |
| normalized | attribute_id, typed value, unit, period, code_system_id/version, normalization rule version |
| execution | 공통 Run/InputReference, 실제 extractor/provider 설정·시점·오류/미지원 사유 |
| evidence | 원본 File/SourceLocation의 정확한 연결; 추출 text는 파생자료이며 원본 대체 금지 |
| review | 후보 검토 결과/검토자·시각/사유/확인 대상 Version; 현재 FactVersion과 구분 |

사업자등록상 업태·종목에 제조가 등록되어 있음과 실제 제조업을 영위함은 별도 attribute다. 등록증의 문자열을 실제 영위 속성의 증명으로 사용하지 않는다. 소재지 역시 등록 주소와 본사/공장/수행 장소를 합치지 않는다.

## 4. Fact 소비측 계약 [PENDING_PROVIDER_CONTRACT]

다른 연구원의 Company/Site/Intake/Fact/Improvement를 재구현하지 않는다. 소비측 read-only Adapter가 실제 계약 필드를 다음 의미에 매핑한다.

- Actor/Membership/Company·Site·File Scope를 Provider가 확인한다. 브라우저 Company ID/role 주장만으로 접근을 허용하지 않는다.
- Fact Root 및 정확한 FactVersion, Company 참조, 필요한 경우 정확한 Site/SiteVersion 및 entity role.
- attribute의 의미/코드체계/버전, typed value, unit, reference period/as-of, 발급/유효 구간.
- 확인된 FactReview/확인자·시각·결과/관련 Evidence. 자동 추출 후보를 확인된 사실로 반환하지 않는다.
- current usable 및 변경/폐기/충돌 여부, 조회한 시점/Provider 버전. 이전 Version의 authorized historical read와 현재 업무 사용가능성을 구분한다.
- evidence 읽기는 별도 Scope 재검사와 hash 검증. 표/페이지 위치와 실제 원문 역추적.

Provider 미연결은 기존 503 유지. 정상 API에 TEST context나 합성 Fact를 주입하지 않는다. TEST Provider는 실제 제한된 DB·테스트 파일·합성 표시·실제 로그인/Membership을 사용하되 OPERATIONAL_PASS 근거가 아니다. 실제 필드명/코드/단위/유효성/ETag는 협업 계약 확인 전 확정하지 않는다.

## 5. 공고조건 자동 구조화 [APPROVED_DESIGN]

Collector의 기존 Notice/NoticeVersion/원문/첨부 재사용 → 기존 Notice Analyzer → Requirement 후보/Reason/SourceLocation → 기존 원문 Human Review/Confirmed RequirementVersion → 별도 구조화 후보 생성 → subject/attribute/operator/value/AST/기준일·예외 정규화 → 원문 범위 누락/부정/OR/AND/단위 정합성 검사 → 구조화 Human Review → 불변 ReviewedConditionVersion.

자료 확보/텍스트 추출/Requirement CONFIRM/구조화 조건 확인은 서로 다른 단계다. 기존 official_verified를 구조화 의미 승인으로 자동 확대하지 않는다. 후보 단계에서도 원문/Requirement 후보를 입력으로 추적할 수 있으나 Matching에 사용할 구조화 결과는 정확한 Confirmed RequirementVersion/Item 및 별도 구조화 검토에 귀속한다.

공고 전체를 반복 수집하거나 원문을 수정하지 않는다. 같은 검토된 ConditionVersion은 여러 기업의 평가에서 재사용하되 기업 Fact/Scope/현재성은 매번 확인한다. Source 또는 Requirement Version이 바뀌면 새 구조화 후보/Version을 생성하고 기존 Match Snapshot은 그대로 남긴다.

## 6. ReviewedConditionVersion 모델 [PROPOSED_IMPLEMENTATION]

Root는 공고 조건의 정체성, Version은 원문 및 검토된 해석의 불변 집합이다. 실제 Table/Column/FK는 구현 승인 후 Slice별 확정한다. docs/03의 확정 물리 모델로 옮기지 않는다.

| 필드 초안 | 의미/Guard |
|---|---|
| id / condition_id / ordinal / previous_version_id | Version/Root/순번/이전 Version, 내용 수정은 새 Version |
| notice_version_id / requirement_version_id | 실제 공고/확정 요건 Version과 현재성·Scope 일치 |
| item_bindings[] | 실제 Requirement Item + SourceLocation + quotation 범위; 복합 AST의 여러 Item 연결 허용 |
| evidence_refs[] | 공식 원문 File/Source/위치·해시·확인 근거, 추출결과만 단독 증거로 사용하지 않음 |
| subject / program_section | 신청자·공급자·사업장·사업 부문 적용범위; 특정 부문 조건을 공통 자격으로 확대 금지 |
| expression | typed AST와 node별 Evidence/원문 범위/불확실성 |
| dictionary_refs[] / policy_refs[] | 코드체계/Mapping/기간·단위/지역 정의의 정확한 Version |
| effective_interval / reference_date | 조건 적용 시점, 비교 기준일의 출처/시간대/포함 경계 |
| extraction_run / generated_at | 실제 구조화 후보 생성 실행/Rule/설정/시점 |
| structured_review_ref | 실제 별도 검토 Actor/time/action/reason 및 정확한 Version; 업무 outcome은 기존 승인 계약 결정 후 구현 |
| current_usable | 현재 Root/Source/Review/정책 입력에서 파생. 과거 Version payload를 update하지 않음 |

FK로 보장할 수 있는 기존 Notice/Requirement/Location과 아직 없는 외부 Fact/Site 참조를 분리한다. 없는 대상 FK/가짜 행/무제한 target_type+target_id 그래프를 만들지 않는다. Review 대상은 해당 Version의 전체 사용 범위 또는 명시 부분 범위이며 미검토 노드를 충족으로 간주하지 않는다.

## 7. Subject·속성·값·연산 [APPROVED_DESIGN / PROPOSED_IMPLEMENTATION]

Subject: Company, HEAD_OFFICE, REGISTERED_ESTABLISHMENT, BRANCH, FACTORY, SITE, SUPPLIER, PROGRAM_APPLICANT, EXECUTION_LOCATION. 이는 AST 내부 적용대상 표기 제안이며 업무 Role/State가 아니다. Site가 여러 개일 때 exact/ANY/ALL/count 범위를 명시한다. 선택한 Site 하나만으로 회사의 모든 사업장을 증명하지 않는다. 빈 목록/목록 완전성 미확인은 임의 TRUE가 아닌 UNKNOWN이다.

속성은 namespace + attribute_id + semantic definition으로 표현한다. registered_business_type, actually_operated_industry, head_office_region, factory_region, incorporation_date, business_start_date, revenue, employee_count, size_category, certification, participation_history, application_period, service_scope 등은 서로 별개다. Provider가 제공하지 않는 속성은 미구현/UNKNOWN으로 남긴다.

값은 STRING/CODE/NUMBER/MONEY/DATE/INTERVAL/BOOLEAN/CODE_SET/REGION_REF로 typing한다. Decimal 문자열과 명시 unit/currency/reference period를 사용하고 float 유사값 비교로 경계를 정하지 않는다.

| 연산 | 현재 | 향후 제안/검사 |
|---|---|---|
| IN / NOT_IN | EXISTING_IMPLEMENTED: 검토된 동일 코드 포함·제외 | 의미/사전 Version/subject 일치가 선행 |
| EQ / NE | PROPOSED_IMPLEMENTATION | typed equality, 코드 Mapping 근거 검사 |
| GT/GTE/LT/LTE/BETWEEN | PROPOSED_IMPLEMENTATION | 단위·기간·양끝 포함 여부·기준일 |
| EXISTS | PROPOSED_IMPLEMENTATION | 미제공과 확인된 미보유를 구분; 완전성 없는 부재는 UNKNOWN |
| REGION_WITHIN | PROPOSED_IMPLEMENTATION | 확인된 행정 코드 계층/공고 별도 정의 Version |
| PERIOD_CONTAINS / OVERLAPS | PROPOSED_IMPLEMENTATION | 시점·시간대·경계·유효성 |
| AND/OR/NOT | PROPOSED_IMPLEMENTATION | 아래 3값 논리 및 node별 근거 |

CodeDictionaryVersion: 속성 의미, system_id/version, code/label/상하위 관계/동의어, 출처·유효기간, 공고 별도 정의를 보존한다. 서로 다른 체계의 mapping은 mapping_version + 검토 근거 + 유효기간을 가진다. 문자열 유사도/주소 접두어만으로 코드 일치나 상위지역 포함을 확정하지 않는다. 정규화 후보와 승인된 코드 Mapping은 별개다.

## 8. 조건 AST 및 예외 [APPROVED_DESIGN]

Node 종류는 PREDICATE/AND/OR/NOT. EXCEPTION은 별도 의미가 확인된 경우 명시 AND/OR/NOT 변환과 원문 범위를 기록한다. 구조상 예외 표현이 가능하다는 사실은 실제 공고 예외정책 확정이 아니다.

각 Node는 node_id, kind, children 또는 predicate, subject binding, applicable section, requirement bindings, evidence, mandatory meaning, 해석 미확정 사항을 가진다. 순서·괄호·부정·적용부문을 보존한다. leaf의 '필수' 표기를 OR 그룹 밖 독립 필수조건처럼 집계하지 않는다.

```json
{
  "id": "TEST-condition-v1",
  "requirement_version_id": "TEST-rv",
  "expression": {
    "node_id": "group-1", "kind": "OR",
    "children": [
      {"node_id": "regional-1", "kind": "PREDICATE", "subject": {"type": "HEAD_OFFICE"},
       "attribute": "administrative_region", "operator": "REGION_WITHIN",
       "value": {"definition_id": "TEST-program-defined-region", "version": "TEST-v1"},
       "evidence_refs": ["TEST-clause-location-1"]},
      {"node_id": "regional-2", "kind": "PREDICATE", "subject": {"type": "HEAD_OFFICE"},
       "attribute": "administrative_region", "operator": "REGION_WITHIN",
       "value": {"code": "TEST-region-U", "dictionary_version": "TEST-region-v1"},
       "evidence_refs": ["TEST-clause-location-2"]}
    ], "evidence_refs": ["TEST-whole-OR-clause"]
  }
}
```

위 JSON은 합성 설계 예시이며 실제 행정구역 코드/정책이 아니다. '충청권 OR 울산'의 공고 정의와 인정 소재지가 확인됐을 때 대응할 수 있다. '울산 본사 AND 실제 제조업 영위'는 AND의 두 다른 속성 leaf. '제조업 제외, 특정 인증기업 예외'는 허용 자격식 OR(NOT(manufacturing), valid_exception_certification)로 표현할 수 있으나 예외가 해당 제외만 완화하는지 다른 필수조건도 완화하는지 원문 검토가 먼저다. 인증 미확인이면 제조기업의 제외 leaf만 보고 성급하게 종합 MISMATCH를 만들지 않는다.

AST validation: group별 arity, NOT 자식 1개, 비순환/제한 깊이·노드 수, 지원된 typed operator, 실제 Item/Location/Version 일치, 출처/검토 누락, 예외 적용범위/서로 충돌하는 해석을 검사한다. 한계를 넘는 표현을 평평한 문장 목록으로 몰래 단순화하지 않고 UNKNOWN/검토 대상으로 반환한다.

## 9. 3값 논리 [APPROVED_DESIGN]

| A | B | AND | OR |
|---|---|---|---|
| TRUE | TRUE | TRUE | TRUE |
| TRUE | FALSE | FALSE | TRUE |
| TRUE | UNKNOWN | UNKNOWN | TRUE |
| FALSE | TRUE | FALSE | TRUE |
| FALSE | FALSE | FALSE | FALSE |
| FALSE | UNKNOWN | FALSE | UNKNOWN |
| UNKNOWN | TRUE | UNKNOWN | TRUE |
| UNKNOWN | FALSE | FALSE | UNKNOWN |
| UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

NOT TRUE=FALSE, NOT FALSE=TRUE, NOT UNKNOWN=UNKNOWN. 비교 속성 부재/충돌/기간 만료/사전 불일치/예외 미확인/미지원 연산은 UNKNOWN이며 0/없음/FALSE로 보정하지 않는다.

평가는 모든 leaf와 사용 입력/증거를 보존한다. TRUE OR UNKNOWN의 그룹은 TRUE여도 UNKNOWN leaf를 삭제하지 않는다. 그 leaf의 부족정보는 해당 OR 그룹에 한해 비차단일 수 있으나 다른 필수 그룹이나 공급자격의 차단을 제거하지 않는다. FALSE AND UNKNOWN은 FALSE이나 외부 예외가 해당 AND를 완화하는지 미확정이면 전체 사업판정은 검토 대기다.

의사코드(설계 설명 전용): evaluate(predicate)=검토된 typed 값/정책/코드/기준일로 T/F/U; evaluate(AND)=F가 있으면 F, 모두 T면 T, 나머지 U; evaluate(OR)=T가 있으면 T, 모두 F면 F, 나머지 U; evaluate(NOT)=T↔F, U→U. 이 엔진은 이번에 운영 코드로 구현하지 않는다.

## 10. 지역·소재지 계층 [APPROVED_DESIGN / PENDING_PROVIDER_CONTRACT]

Address evidence → 실제 주소 normalization candidate → 검토된 행정구역 코드/유효 기준일 → 사전 계층/공고 정의와 비교한다. 시·도/시·군·구/하위 구역 코드를 지원 가능한 관계로 모델링하되 현재 실제 코드 제공자·버전·계약은 PENDING이다.

충청권을 고정 문자열 배열로 정의하지 않는다. 공고가 정한 지역 집합/하위 포함 규칙을 ConditionVersion의 별도 region_definition_version으로 고정하고, 근거가 없으면 UNKNOWN이다. 대전/세종/충남/충북 포함 여부를 공고 확인 없이 추정하지 않는다. 울산 역시 실제 코드와 기준일·계층 및 인정 소재지 유형을 확인한다.

본사/등록 사업장/지점/공장/수행 장소 각각 SiteVersion/속성/증빙을 소비한다. 부산 본사·울산 공장을 본사 울산으로 판정하지 않는다. 본사 또는 공장 인정이라는 조건이면 각각의 predicate에 서로 다른 subject를 연결한다. 동일 회사의 Site 존재, 해당 Site의 기준일 유효성 및 필수 인허가/원문 조건을 확인한다.

행정구역 개편과 코드 매핑 변경은 사전의 새 Version이다. 과거 Snapshot은 당시 dictionary/mapping/region_definition/Fact/Condition Version을 고정하며 재조회 때 최신 사전으로 조용히 다시 평가하지 않는다. 새 평가가 필요하면 새 Run/후보와 stale 영향 검토를 생성한다.

## 11. 기간·단위·업력·예외 [PENDING_POLICY]

공고의 기준일 종류(공고일/접수일/마감일/협약일 등), DATE와 timestamp, 시간대, 포함 경계, 설립일과 개업일, 휴업/재개/합병의 업력 의미, 매출 결산기간과 단위·통화, 근로자 집계 범위/시점, 인증 발급/만료/유예·동등인증을 정책 Version으로 명시한다. 승인된 정책이 없으면 계산을 추정하지 않는다.

7년 이내/50명 이하/100억 미만은 boundary와 unit/reference period가 확인된 합성 검증 예시다. 아직 보편적인 공식 판정규칙이 아니다. 월/연 계산·윤년·반올림·환율·매출 단위 환산은 정책 승인 및 근거가 필요하다. 공고 신청기간과 Fact 문서 유효기간도 서로 다르다. 현재 Comparator의 valid_from/valid_until 검사는 입력 Fact의 비교 기준일 유효성만 검사하며 업력/접수마감 엔진 구현이 아니다.

미해결 예외가 있으면 독립 leaf의 충돌을 최종 제외로 집계하지 않는다. 예외가 확인되면 해당 범위에서만 완화하며 다른 필수 그룹은 유지한다. 제외조건 여러 개는 각각 Evidence를 보존한다.

## 12. 자동화와 Human Review [APPROVED_DESIGN]

A. 자동 비교 가능: 기존 확인 계약을 통과한 Fact, 별도 검토된 의미 일치 ConditionVersion, 지원 연산/사전/기준일, 해결된 예외 → 자동 조건 비교와 양측 Evidence. 최종 MatchReview는 계속 별도다.
B. 자동 분석 후 검토 필요: 후보 불명확/충돌/등록·실제 영위 구분/지역 정의/단위/예외/부문 모호 → 원문/추출 후보/변경 차이/확인 질문을 제공. 확인 대상만 검토하고 전체를 재입력시키지 않는다.
C. 공식 Human Review 필수: 기존 Fact 확인, Notice 공식 확인, Matching/Proposal/Approval/Proceed 등 FROZEN Guard는 그대로 적용한다. 자동화 성능이 높다는 이유로 승인 경로를 제거하지 않는다.

같은 ConditionVersion을 여러 회사에서 재사용하여 구조화 검토 중복을 줄인다. Company별 Fact 검증/자료 접근/최종 매칭 검토는 대체하지 않는다. 자동 승인 확대는 별도 PENDING_POLICY이며 이번 상세설계/코드 변경으로 확정하지 않는다.

## 13. 기존 Comparator DTO 매핑 [EXISTING_IMPLEMENTED / PROPOSED_IMPLEMENTATION]

| 소비측 기존 내부 DTO | 제안 연결 | 제약 |
|---|---|---|
| ConfirmedFact.version_id/company_id/site_id | 실제 CompanyFactVersion/Company/Site | TEST 값이 아닌 권위 있는 Provider 매핑 필요 |
| attribute/value | 의미·사전 Version이 확인된 leaf 속성/코드값 | 기존 string 값은 동일 코드 의미에서만 사용 |
| review_id/evidence_refs/confirmed/current_valid | 실제 FactReview/Evidence/현재성 | 추출 후보나 truthy 문자열 금지 |
| valid_from/valid_until | 정책으로 확인된 Fact 유효 구간 | 기준일 의미가 확정된 경우만 비교 |
| ReviewedCondition.requirement_version_id/item_id/evidence_id | 실제 검토된 Item/SourceLocation | 원문 CONFIRM과 별도 구조화 검토 모두 필요 |
| attribute/operator/values | 단일 leaf IN/NOT_IN | 복합 AST/지역/수치/예외를 flatten하여 전달 금지 |
| review_id/reviewed/current_valid/as_of/mandatory | 구조화 검토/현재성/기준일/독립 필수조건 | 그룹 내부 leaf를 독립 필수로 승격 금지 |
| ComparisonInputs | 고정 Fact/조건 묶음 | Actor/Company/File Scope는 소비 전에 Provider/서비스 검증 |

기존 Comparator는 코드 포함/제외에 대한 자동 결과 생성과 버전/증거 보존을 재사용한다. 단일 검토된 동일 의미 leaf만 기존 Adapter로 전달한다. 지역 계층/AST/수치/기간/예외는 미래 평가기와 승인된 정책이 필요하며 현재 기능처럼 표시하지 않는다. 분해 가능한 leaf라도 그룹 종합을 계산하지 못하면 leaf 결과만 제공하고 그룹은 UNKNOWN이다.

내부 TRUE/FALSE/UNKNOWN ↔ CONFIRMED_SATISFIED/CONFIRMED_CONFLICT/UNKNOWN. MatchCandidate 집계는 지원범위/서비스/자격의 확인 범위와 필수 그룹/예외 해소를 함께 검토한다. 기존 명확한 hard conflict → MISMATCH 후보, 필수 부족 → NEED_MORE_INFO를 보존한다. 미래 FIT/PARTIAL_FIT 완전성 정책 및 PROPOSABLE Guard 세부 확장은 PENDING_POLICY. 선정확률/자동 제안/자동 승인 없음.

## 14. 입력·출력 DTO 및 API 초안 [PROPOSED_IMPLEMENTATION]

EvaluationInput: Actor의 허용 Context, Company/Site/신청주체, ImprovementVersion, 정확한 CompositionVersion/CapabilityVersion/Assessment, Confirmed FactVersion[], ReviewedConditionVersion, Dictionary/Mapping/Policy Versions, reference date와 출처, input fingerprint/idempotency identity. 서버 reader가 모두 검증하여 고정하며 Client의 확인 플래그를 신뢰하지 않는다.
EvaluationOutput: 공통 Run, typed MatchInputSnapshot, Node result tree, leaf의 attribute/operator/value/code/unit/date, 사용 FactVersion/ConditionVersion/Item/Location/Evidence, comparison reason/unknown reason, missing information/차단 여부, 세 판단 차원, 미해결 예외·충돌, 실제 MatchCandidate 및 Review 참조. 원본/표·페이지 역추적 및 이전 Snapshot 불변.

제안 Endpoint(아직 미구현): 기존 권한이 허용하는 운영자 Context의 조건 후보 조회/구조화 검토/Version history; 현재 조건으로 평가 요청; 평가 결과·과거 Snapshot/Node Evidence 조회. path/명명/공통 Request·response/typed FK는 R-07 구현 승인 후 확정한다. 현재 구현된 /capability/assessments·reassess·matches·review 및 공통 계보와 혼동하지 않는다.

POST는 trusted origin/session/idempotency/expected Source·Condition Version을 검사한다. Permission 숨김만으로 보호하지 않는다. 동일 요청 replay와 새 입력 재평가를 구분한다. Scope 없음은 DENY, 미연결 Provider는 기존 503, stale는 기존 Version Guard, 자료 부족은 UNKNOWN 결과/추가정보이며 API 성공을 업무 확정으로 표시하지 않는다.

## 15. 운영자 UI 초안 [PROPOSED_IMPLEMENTATION]

기업 증빙: 문서 유형·원문 페이지/표 ↔ 추출 후보 ↔ 현재 Fact/충돌/기간을 나란히 표시. 검토할 필드만 조정하며 확인 대상 Version을 표시한다.
공고 구조화: Requirement Item·공식 원문 ↔ AST 트리/subject/부문/속성/연산·값·단위/기준일/예외 ↔ 정규화 후보·불확실성. 원문 확인과 구조화 확인의 검토 기록을 구분한다. OR/AND·예외 누락 경고 및 변경 Version 비교.
매칭: 세 판단 차원의 독립 결과, group/leaf TRUE/FALSE/UNKNOWN, 필수 충돌과 적용 예외, 근거 양측, 누락정보·확인 질문, 실행/입력 Version·현재성·기존 관리자 검토상태. 이전 Run/Review/Snapshot에 접근해도 현 결과로 위장하지 않는다.

권한 없음은 기존 Action 숨김, 조건 불충족은 disabled와 이유. 최종 제안가능·공식 제출·선정은 기존 Guard/근거를 따른다. 가짜 버튼/Mock 결과/자동 FIT·선정확률을 추가하지 않는다. 수요기업 Evidence는 자기 Scope만 제공하고 타기업 파일 URL/추론값을 노출하지 않는다.

## 16. Evidence·Version·감사 [APPROVED_DESIGN]

NoticeVersion → RequirementVersion/Item → SourceLocation/공식 Review → 구조화 후보 Run → 별도 구조화 Review/ConditionVersion → MatchInputSnapshot/Run/Node 결과 → MatchReview를 추적한다. Company 문서 → 추출 후보/FactReview → FactVersion/Evidence도 동일 Snapshot에 고정한다. R-04 공통 계보는 실행 메타데이터를 공유하고 실제 도메인 결과/검토 의미는 별도 typed 관계로 유지한다.

Version 변경: 새 Source/Fact/조건/사전/정책/Capability 입력으로 새 Run/후보를 생성한다. 이전 승인·검토·원문·Snapshot을 덮어쓰지 않는다. 참조 관계로 stale/영향 대상을 파생하며 기존 상태/권한을 변경하지 않는다. 공통 Audit에는 Actor/time/action/typed IDs/변경 fingerprint를 기록하고 Secret/원문 개인정보를 무조건 복제하지 않는다.

원문 Evidence의 File/digest/위치 유효성, 서로 다른 기업/Version/기간·사업부문의 연결, 변경된 URL/저장소를 재확인한다. 잘못된 참조는 비교 전에 차단한다. 부족근거는 결과에 남겨 추후 정보를 요청할 수 있게 하며 의미가 확인되지 않은 값을 임의 수치로 보정하지 않는다.

## 17. 상세설계 검증 사례 [APPROVED_DESIGN; 미래 Acceptance 모두 NOT_RUN]

공통 테스트 계약: 각 사례는 TEST NoticeVersion N1, RequirementVersion R1/Item I*, 별도 구조화 검토 ConditionVersion C1, 필요한 확인 FactVersion F*, 사전 D1/정책 P1/기준일 T1, 해당 Company/Site Scope를 사용한다. 공고 원문 E-N*, 기업 증빙 E-F*, 구조화 검토 E-C*를 실제 위치·해시로 연결한다. 각 행의 기업/공고 의미는 합성 Fixture 정의이며 공식 정부 정책이 아니다. 실제 값·코드·시간경계는 Fixture manifest에 명시하고 누락이면 U로 판정한다.

| ID | 입력 공고조건 / 기업 Fact | 속성·연산/체계·시점 | 기대 / 부족 사유 / 검토 | 현재 구현·미래 Acceptance |
|---|---|---|---|---|
| AUTO-01 | 등록 제조업 제외 / 등록 업종 Fact 확인 | registered_business_type NOT_IN; 같은 D1/T1 | 충돌; 양측 근거; MatchReview 별도 | 기존 단순 코드 비교 재사용 가능, 운영 등록업종 매핑 NOT_RUN |
| AUTO-02 | 실제 제조 영위 제외 / 등록 제조만 확인 | operated_industry와 registered_type 구분 | U; 실제 영위 증빙 필요; 의미 검토 | 의미 Adapter/정책 미래, 서로 대체하면 FAIL |
| AUTO-03 | 대상기업 조건 / 확인 Fact 없음 | 해당 attribute / T1 | U; Fact/E-F 필요; 확인 요청 | 기존 UNKNOWN 검증됨, 운영 Case NOT_RUN |
| AUTO-04 | 구조화 미검토 조건 / Fact 확인 | C 후보만 존재 | U; E-C 확인 필요; 원문 CONFIRM만으로 평가 금지 | 기존 reviewed guard 검증됨; 운영 조건 Review NOT_RUN |
| AUTO-05 | 동일 기간 속성 / 증빙 F1/F2 값 충돌 | 같은 attribute/unit/T1 | U; 충돌 자료 검토, 자동 덮어쓰기 금지 | 단순 코드 충돌 검증됨, 연구원 Provider NOT_RUN |
| AUTO-06 | 필수 속성 / F1 유효기간 종료 | T1에서 expiry | U; 현재 유효 Fact 필요 | 기존 유효성 검증됨, 운영 기간 정책 NOT_RUN |
| AUTO-07 | 제조 제외·인증 예외 / 제조 T, 인증 U 또는 유효 T | OR(NOT(manufacturing),valid_cert); D1/P1/T1 | 인증 U면 U, T면 그 그룹 T; 다른 필수조건 유지 | AST/예외 미래; leaf 충돌만 MISMATCH면 FAIL |
| AUTO-08 | 타기업 F/E 참조 | Company/Site/File Scope | DENY; 값/파일 미노출 | 기존 Scope 검증됨, 운영 Provider NOT_RUN |
| AUTO-09 | F1으로 평가 후 F2 변경 | Snapshot F1, 새 입력 F2 | 과거 유지·stale·새 평가 | 기존 stale 검증됨, 운영 FK 매핑 NOT_RUN |
| AUTO-10 | C1 평가 후 C2 변경 | C1/R1와 C2/R2 구분 | 과거 AST/근거 유지, 새 평가 필요 | ConditionVersion 미래, history/Review 불변 Acceptance |
| AUTO-11 | 서비스 A 적합 / 자격 필수 그룹 F | 세 차원 독립 | 자격 충돌 상쇄 금지, 최종 Review | 기존 분리 보호, 범용 그룹집계 NOT_RUN |
| AUTO-12 | 서비스/기업조건 T / 공급자 Fact 없음 | SUPPLIER subject 독립 | U/NEED_MORE_INFO, 전체 FIT 금지 | 기존 부족정보 유지, 공급자 계약 NOT_RUN |
| REG-A | 충청권 인정·충북 Fact / 정의에 충북 명시 포함 | REGION_WITHIN D1/공고 지역 정의 C1/T1 | T; 정의/E-N와 Fact/E-F 필요 | 지역 계층 미래 NOT_RUN |
| REG-B | 울산 본사 인정 / 울산 본사 Fact | HEAD_OFFICE region D1/T1 | T; 해당 subject 확인 | 미래, 본사 증빙 연결 필수 |
| REG-C | 울산 본사만 인정 / 부산 본사·울산 공장 | HEAD_OFFICE predicate, FACTORY별도 | 본사 조건 F; 공장으로 대체 금지; 예외 검토 | 미래 NOT_RUN |
| REG-D | 울산 공장도 인정 / 부산 본사·울산 공장 | OR(HEAD_OFFICE,FACTORY), SiteVersion | 해당 그룹 T; 다른 조건 유지 | 미래, 실제 공장 Fact/E-F 필요 |
| REG-E | 충청권 OR 울산 / T,U 또는 U,U | OR; 확인된 D1·subject/T1 | T,U→T; U,U→U; 모든 leaf 근거 보존 | 미래 NOT_RUN |
| REG-F | 충청권 AND 제조업 / T,T 또는 T,U | AND; region/operated_industry 분리 | T,T→T; T,U→U | 미래, 두 속성 의미 일치 필수 |
| REG-G | 지역조건 / 소재지 누락·만료 | region/D1/T1 | U; 유효 소재지 자료 필요 | 미래 NOT_RUN |
| REG-H | 충청권 정의 불명확 / 주소 확인 | region_definition 미확정 | U; 임의 지역 확대·축소 금지 | 미래, 정의 검토 필요 |
| LOGIC-01 | OR(T,U) | AST C1, 두 leaf E-N/E-F | T; U leaf 보존; 최종 Review 별도 | 미래 pure truth-table Acceptance |
| LOGIC-02 | OR(F,U) | 동일 | U; 부족 leaf 확인 | 미래 NOT_RUN |
| LOGIC-03 | AND(F,U) | 동일 | F; 외부 예외 미확정이면 종합 보류 | 미래 NOT_RUN |
| LOGIC-04 | AND(T,U) | 동일 | U; 부족 leaf 확인 | 미래 NOT_RUN |
| LOGIC-05 | NOT(U) | 동일 | U; unknown을 부정으로 확정 금지 | 미래 NOT_RUN |
| POLICY-01 | 창업 7년 이내 / 설립·개업 날짜 | date/tenure; 기준일·포함 경계 P1 | P1확인 전 U; 경계일/윤년 검증 | PENDING_POLICY/NOT_RUN |
| POLICY-02 | 매출 100억 미만 / 기간·단위 다른 매출 | MONEY/LT; unit/currency/reference period | 정규화 정책 미확인 U; 명시 단위·기간만 비교 | PENDING_POLICY/NOT_RUN |
| POLICY-03 | 인증 보유 예외 / 만료·갱신·유예 | certification/interval/P1/T1 | 유효/동등성 확인 전 U; 적용범위 검토 | PENDING_POLICY/NOT_RUN |
| POLICY-04 | 여러 필수/예외 조건 중첩 | AND/OR/NOT AST + subject/policy | 그룹별 T/F/U·근거·차단, leaf 평탄화 금지 | 미래 property/negative Acceptance |

미래 테스트는 개별 결과뿐 아니라 영속성·새로고침·정확한 Version·타기업 차단·변경/재평가·중복 요청·Provider 미연결·지원하지 않는 연산/잘못된 AST를 검증한다. 설계 표를 실제 실행 PASS로 보고하지 않는다.

## 18. 구현 Slice와 Acceptance [PROPOSED_IMPLEMENTATION]

S1 소비 계약: 연구원 Fact/Site/Membership/Evidence 계약 확인, read-only Adapter, 실패/Scope/기간·코드 매핑 Fixture. 기존 503 우회 없음.
S2 구조화 후보: 기존 Notice 입력/공통 계보·Source 재사용, 의미/subject/AST 후보·불확실성, 자동 Confirm 없음. 실제 원문/표/부문·OR/AND/부정 누락 검증.
S3 별도 검토 Version: 승인된 최소 물리 관계/Migration 및 공식·구조화 검토 구분, immutable History/stale/권한. 원문 CONFIRM을 대신하지 않음.
S4 사전·정책 Adapter: 코드/지역 계층/Mapping/기준일·단위 Version 및 유효성, 미확정 의미 UNKNOWN. 공고별 데이터 정의를 코드 분기로 구현하지 않음.
S5 범용 pure evaluator: bounded AST/3값 논리/예외·수치·기간, node별 Evidence/UNKNOWN. 실제 코드와 합성 정책 Fixture를 구분하고 결정적 truth-table/경계/property tests.
S6 Snapshot/API/UI 통합: 세 차원·분석/업무 Review 분리, 실제 PostgreSQL/파일/권한·Version, 새 Fact/Condition/사전 입력 stale, 과거 평가 재조회.
S7 운영 검증: 실제 Provider/확인된 실제 공고·기업 Evidence의 업무 정확성 검수, 기존 대표 Demo와 전체 격리 회귀, 승인된 배포/Migration 절차.

각 Slice의 구현 권한/물리 계약/업무 정책을 승인받은 뒤 개발한다. 모든 Slice의 필수 Acceptance가 실제 실행되어야 운영 통합 PASS를 주장할 수 있다. 전체 SYSTEM_ACCEPTANCE는 기존 09/10 E2E 요구로 별도 판단한다.

## 19. 추가 승인 및 협업 대기 [PENDING_POLICY / PENDING_PROVIDER_CONTRACT]

- R-07 운영용 Condition Root/Version/Node/Review/Input/Evidence typed 관계와 Migration 승인. 기존 도메인 행에 없는 FK/State를 임의 추가하지 않음.
- 별도 구조화 Review Action/API와 기존 Permission/필수 확인 계약의 세부 연결 승인. 자동 승인 확대는 별도 정책 요청.
- 범용 평가기/사전·Mapping Version 제공자·단위·기간·예외·완전성/차단 집계 정책 승인.
- 실제 Company/Site/Fact/Review/Evidence/현재성 Provider 계약·팀 책임·조회 오류/갱신·Scope 합의. 기존 연구원 코드 변경은 이번 범위 밖.
- 파일 입력/추출 지원 포맷·OCR/LLM 필요성과 보안/운영비/실제 계약은 후속 결정. 이번 작업에서 Provider 도입 없음.
- 운영 데이터 Migration/배포/Git 반영은 별도 승인 대상.

## 20. 자체 정합성 판정 [APPROVED_DESIGN]

범용 subject/typed attribute/value/dictionary/AST는 제조업·지역 고정 분기 없이 지원대상을 표현한다. 지역 정의·인증 예외·기간·단위·입력완전성을 외부 검증 데이터/정책 Version에 귀속한다. 기존 IN/NOT_IN은 유지하고 미지원 식은 UNKNOWN/검토 대상으로 남긴다. 기존 State/Permission/Source of Truth/공식 Human Review를 보존한다.

R07_AUTOMATION_DESIGN 및 GENERIC_CONDITION_MODEL의 설계 정합성은 문서 검토로 판단할 수 있다. DOCUMENT_EXTRACTION/CONDITION_EXTRACTION/운영 범용 엔진은 **NOT_IMPLEMENTED**, OPERATIONAL_INTEGRATION은 **BLOCKED**. 설계 완성은 운영 구현·실제 업무 정확성 PASS 또는 SYSTEM ACCEPTANCE가 아니다.
