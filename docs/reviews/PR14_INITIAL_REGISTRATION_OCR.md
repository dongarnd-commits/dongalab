# PR14 최초 등록·로컬 한글 OCR 구현 영향

사용자 2026-10-21 지시에 따른 C02/C03 증분이다. 기존 Company 등록/Scope/Version/Fact Guard를 유지한다.

- 등록 전 인증된 COMPANY_EDITOR가 PDF 원본을 메모리 요청으로 분석한다. Company/DB File/임시 영속 객체를 생성하지 않는다. 탭 메모리의 File은 취소/로그아웃/페이지 종료 때 폐기한다. 등록 전 원문 조회용 식별자·공유 토큰·보존정책을 신설하지 않는다.
- 텍스트 PDF는 기존 pypdf 파서를 재사용한다. 스캔 페이지만 로컬 OCR Adapter로 처리한다. Tesseract kor+eng와 PDFium 렌더러의 라이선스·Windows/Linux 호환성을 확인하고 합성 스캔으로 해상도를 비교한다. 외부 OCR/AI API 없음. PDFium은 별도 제한시간 subprocess에서 처리하여 비동기 API Thread 간 native 동시 호출을 피한다.
- 최초 등록의 서버 사업자번호 정규화/체크디지트 검사를 공통 적용한다. 기존 저장 Profile의 수정/과거 Version은 소급 거절·수정하지 않는다. 기존 테스트의 임의 번호는 유효한 합성 체크디지트로 교체하며 보안/회귀 조건은 유지한다.
- 사용자 검토 후 기존 POST /company와 동일 register Guard로 생성한다. 새 Company ID가 재조회된 후 기존 upload/parse API로 원본/근거를 보존한다. 회사 생성/문서 보존은 별도 서버 명령이다. 중간 실패 시 Company 생성 여부와 미보존 파일을 구분하며 동일 Company에서 재시도하고 중복 Company를 만들지 않는다.
- 문서 후보는 source digest/page/text를 표시하고 충돌값은 사용자가 선택한다. 대표자/업종은 기존 Profile에 저장하며 소재지는 명시적으로 확인한 경우 기존 Site API를 사용한다. 개업일은 Profile 계약이 없어 원문/후보에만 보존하고 Profile 저장으로 표시하지 않는다. Fact 자동확정 없음.
- 기존 등록된 기업의 초기 화면을 자동 덮어쓰거나 재등록하지 않는다. C07 일반 자료함/기존 개선요구/운영자 조회를 유지한다.
- Schema/Migration/Role/업무 State/Approval 변경 없음. 등록 전 권한은 기존 COMPANY_EDITOR 최초 등록 권한 안에서만 검사한다.

사용자가 제공한 상위 Private 폴더에서 실제 PDF 2개를 확인했다. 원문과 필드값을 로그/Git에 넣지 않고 로컬 검증한다. 자동화 OCR 실행·저장 검증과 사용자의 실제 정확성/수용 검수는 구분한다.


## 실행 환경 및 근거

- Tesseract 5 / kor+eng (Apache-2.0) 로컬 엔진: https://tesseract-ocr.github.io/tessdoc/Installation.html
- 언어 데이터: https://github.com/tesseract-ocr/tessdata_fast (Apache-2.0)
- PDFium 렌더러 pypdfium2 5.14.0 (Apache-2.0/BSD-3-Clause 및 PDFium 의존 라이선스 포함): https://pypdfium2.readthedocs.io/en/stable/readme.html#licensing
- PDFium은 thread-safe하지 않아 별도 문서 subprocess로 호출하며, 임시 PDF/이미지 파일 없이 stdin/stdout 바이트를 사용한다. 원문/OCR 텍스트를 프로세스 로그에 남기지 않는다.
- 기존 텍스트 PDF는 pypdf를 재사용하며 OCR을 실행하지 않는다. 스캔은 최대10페이지/페이지20M 픽셀/원본20MiB/문서50초 한도에서 OCR을 시도한다. 한도를 넘거나 엔진이 없으면 원문/직접 입력 경로를 제공한다. 미지원/실패를 OCR 성공으로 표시하지 않는다.
- 합성 스캔 및 Private 문서의 180/240/300 DPI, PSM3/4/6/11 비교 후 300 DPI/PSM4를 사용한다. 인식 정확성의 보장은 아니며 원문과 필드별 사용자 검토가 필요하다.

Linux: `apt-get install tesseract-ocr tesseract-ocr-kor` 및 기존 `uv sync --project apps/api`.

Windows: 시스템 전역 설치 대신 `docker build -t datco-local-ocr:pr14-v1 infra/ocr`로 전용 로컬 엔진 이미지를 준비하고 API 프로세스 환경에 `DATCO_OCR_DOCKER_IMAGE=datco-local-ocr:pr14-v1`을 설정한다. 실제 처리 컨테이너는 네트워크 없음/읽기전용/권한 제거/리소스 제한으로 실행하며 Private 경로를 mount하지 않는다. 원본은 파이프로만 전달한다. 기존 DB 컨테이너를 변경하지 않는다.

등록 전 선택 문서는 탭 메모리이며 분석 요청 취소/탭 종료/로그아웃 후 영구 임시 파일이 남지 않는다. 서버에서 이미 시작된 로컬 분석은 제한시간 안에 종료한다. Company 생성 뒤에는 원본·근거 보존 서버 명령을 이어서 수행한다. v1.2에서는 사용자의 추가 클릭 없이 자동 연결하며 부분 실패 때만 재시도를 표시한다. 원본 보존 실패/추출 실패를 구분하고 기존 생성 Company에서 재시도한다. 등록 후 기존 Private FileProvider의 저장/DB 실패 시 미참조 파일 보존 정책은 기존 계약을 유지하며 신규 삭제 정책을 도입하지 않는다.

OCR 엔진 자체에도 독립 watchdog(15초, 종료 지연2초)을 두어 부모 분석 요청이 종료되더라도 엔진이 무한 실행되지 않게 한다. Linux는 coreutils timeout, Windows 로컬 컨테이너는 이미지 entrypoint timeout을 사용한다.

## 사용자 검수 v1.2 — 2026-10-21

- C02는 단일 PDF 선택/드롭 영역과 문서 분석·선택 취소·직접 입력 버튼으로 시작한다. 후보별 선택·중복 업로드 안내·기술 설명·연락처/기업현황/사업장 등록 체크·최종 체크박스를 제거한다. 사용자가 최종 입력폼을 확인한 후 누르는 기업정보 등록이 기존 기업 사실확인 기록의 명시적 실행이다. 운영자 Fact 확정은 수행하지 않는다.
- 업태·종목은 기존 industry 문자열 안에 `업태: …\n종목: …`으로 구분해 저장한다. 여러 명시된 값을 줄바꿈으로 유지하고 입력 수정·재로그인 조회를 검증한다. 새 필드/Requirement Kind/DB Migration은 없다. 일반 업종 라벨에서 업태/종목을 추정 분류하지 않는다.
- 기존 OCR 포트를 재사용하여 스캔 1페이지에서 두 분류 라벨이 부족할 때만 표 보완 읽기(180 DPI/PSM6)를 수행한다. 첫 300 DPI/PSM4 원문을 교체하지 않으며 추가 원문·실제 파라미터/페이지를 Evidence로 보존한다. 보완 결과에서는 업태/종목만 소비하고 상호/번호 등을 덮어쓰지 않는다. 45초 잔여시간·기존 엔진 watchdog/자원/권한 제한을 지키며 보완 실패가 주 분석 결과를 없애지 않는다.
- 입력폼 소재지가 있으면 기존 Site API로 본사 사업장을 보존한다. 추가 사업장은 C04에서 입력한다. 연락처/기업현황의 기존 Profile 기능은 C04에 그대로 있다. 개업일/법인번호의 전용 저장 필드는 추가하지 않았으며 최초 등록폼에 저장 가능한 것처럼 노출하지 않는다.
- 기업정보 등록 한 번으로 기존 Company 등록 → 선택 Context 준비 → 원본/근거/기업 확인 기록 → 재조회 순으로 이어진다. Context 변경 전의 요청을 재사용하지 않는다. 실패 시 실제 생성 Company를 유지하고 같은 기업에서 재시도한다. 원본 저장 전 단순 기업 생성만으로 전체 성공을 표시하지 않는다. 등록 후 새로고침·세션 종료로 메모리 파일선택이 사라진 경우는 기존 C07 보완 경로를 사용한다.
- 실제 Private 등록증명원의 업태/종목 라벨을 보완 인식한다. 다른 등록증에서 OCR이 읽지 못한 항목·라벨 없는 표의 연속 행은 임의 추정하지 않는다. 원본 확인과 사용자 직접 입력이 필요하며 원문 보존과 모든 항목의 자동 추출 정확성은 별개다.
