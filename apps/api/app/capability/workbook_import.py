"""Bounded administrator workbook intake; classifications never create managed parents."""
from collections import Counter
from hashlib import sha256
from pathlib import PurePath
import re
from app.capability.application import fingerprint
from app.capability.asset_catalog import catalog_snapshot, _catalog_lock
from app.company.documents import parse_document, package, xml, S as XML_S, DocumentError
from app.infrastructure import capability_schema as S
from app.notice.domain import Denied

PARSER = "dmp-workbook-table-v1"
FIELDS = ("system", "feature_group", "name", "description")
HEADERS = (*FIELDS, "feature_id")
HEADER_ALIASES = {"system":"system", "시스템":"system",
    "feature_group":"feature_group", "기능그룹":"feature_group", "모듈":"feature_group",
    "name":"name", "기능명":"name", "기능":"name",
    "description":"description", "기능설명":"description", "설명":"description",
    "feature_id":"feature_id", "원천기능ID":"feature_id"}
MAX_ROWS = 5000
ID = re.compile(r"DMP-[A-F0-9]{16}\Z")
CELL = re.compile(r"([A-Z]{1,3})([1-9][0-9]{0,6})\Z")
LIMITATIONS = ["지원: 첫 행의 시스템 / 기능그룹(모듈) / 기능명(기능) / 기능설명(설명), 선택 원천기능ID와 대응 영문 헤더.",
    "원시 셀값과 시스템·기능그룹의 명시적 세로 병합만 읽습니다. 빈 셀의 분류를 임의 상속하지 않습니다.",
    "도형·이미지·스타일·날짜와 단위 해석·수식 계산은 지원하지 않습니다. 분류는 실제 모듈 소속이나 제공 검증이 아닙니다."]


def column_number(value):
    result = 0
    for char in value:
        result = result * 26 + ord(char) - 64
    return result


def semantic(data):
    return {field: data.get(field, "").strip() for field in FIELDS}


def parse_workbook(filename, content):
    name = PurePath(filename.replace("\\", "/")).name
    if (name != filename or len(name) > 200 or not name.lower().endswith(".xlsx")
            or any(ord(c) < 32 for c in name)):
        raise Denied("WORKBOOK_FILENAME_INVALID", 422)
    try:
        parsed = parse_document(name, content)
        cells = {}
        for location in parsed.locations:
            match = re.fullmatch(r"XLSX sheet (.*) cell ([A-Z]{1,3}[1-9][0-9]{0,6})", location.descriptor)
            if not match:
                raise DocumentError("INVALID_CELL_LOCATION")
            sheet, address = match.groups()
            cells.setdefault(sheet, {})[address] = location.text
        sheets = []
        with package(content) as archive:
            workbook = xml(archive.read("xl/workbook.xml"))
            rels = {r.attrib["Id"]: r.attrib for r in xml(archive.read("xl/_rels/workbook.xml.rels"))}
            sheet_names = set()
            for node in workbook.iter(XML_S + "sheet"):
                sheet_name = node.get("name", "")
                if not sheet_name.strip() or sheet_name.casefold() in sheet_names:
                    raise Denied("WORKBOOK_SHEET_NAME_INVALID", 422)
                sheet_names.add(sheet_name.casefold())
                rel = rels[node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")]
                target = rel["Target"]
                path = target.lstrip("/") if target.startswith("/xl/") else "xl/" + target
                root = xml(archive.read(path))
                sheets.append((node.get("name", ""), root))
        rows, unsupported = [], []
        for sheet_index, (sheet, root) in enumerate(sheets):
            values = cells.get(sheet, {})
            columns = {}
            for address, value in values.items():
                match = CELL.fullmatch(address)
                if int(match[2]) == 1 and value.strip() in HEADER_ALIASES:
                    header = HEADER_ALIASES[value.strip()]
                    if header in columns:
                        raise Denied("WORKBOOK_DUPLICATE_HEADER", 422)
                    columns[header] = match[1]
            if not all(field in columns for field in FIELDS):
                unsupported.append(dict(sheet=sheet, row=None, reason="첫 행에 지원하는 필드명이 없어 이 시트를 등록하지 않았습니다.", reason_codes=["WORKBOOK_UNSUPPORTED_HEADERS"]))
                continue
            formulas = {cell.get("r") for cell in root.iter(XML_S + "c") if cell.find(XML_S + "f") is not None}
            merges = []
            for merge in root.iter(XML_S + "mergeCell"):
                span = merge.get("ref", "").split(":")
                if len(span) != 2 or not all(CELL.fullmatch(x) for x in span):
                    raise Denied("WORKBOOK_MERGE_INVALID", 422)
                start, end = (CELL.fullmatch(x) for x in span)
                if int(start[2]) > int(end[2]) or column_number(start[1]) > column_number(end[1]):
                    raise Denied("WORKBOOK_MERGE_INVALID", 422)
                merges.append((start[1], int(start[2]), end[1], int(end[2]), merge.get("ref")))
                if len(merges) > MAX_ROWS:
                    raise Denied("WORKBOOK_ROW_LIMIT", 422)
            for address in sorted(formulas):
                if CELL.fullmatch(address) and CELL.fullmatch(address)[1] not in columns.values():
                    unsupported.append(dict(sheet=sheet, row=int(CELL.fullmatch(address)[2]), reason="표의 지원 필드 밖 수식은 계산하지 않았습니다: " + address, reason_codes=["WORKBOOK_FORMULA_UNSUPPORTED"]))
            if next(root.iter(XML_S + "drawing"), None) is not None or next(root.iter(XML_S + "legacyDrawing"), None) is not None:
                unsupported.append(dict(sheet=sheet, row=None, reason="도형·이미지는 읽지 않았습니다. 표의 셀 자료만 비교했습니다.", reason_codes=["WORKBOOK_DRAWING_UNSUPPORTED"]))
            numbers = sorted({int(CELL.fullmatch(address)[2]) for address in values if int(CELL.fullmatch(address)[2]) > 1})
            for number in numbers:
                data, positions, issues = {}, {}, []
                for field, column in columns.items():
                    address = column + str(number)
                    source = address
                    value = values.get(address, "")
                    for first_col, first_row, last_col, last_row, span in merges:
                        if first_row <= number <= last_row and column_number(first_col) <= column_number(column) <= column_number(last_col):
                            if field in ("system", "feature_group") and first_col == last_col == column and first_row > 1:
                                source = column + str(first_row)
                                value = values.get(source, "")
                                positions[field] = dict(cell=source, merged_range=span)
                            else:
                                issues.append(dict(code="WORKBOOK_MERGE_UNSUPPORTED", message="지원하지 않는 병합 셀입니다: " + span))
                    positions.setdefault(field, dict(cell=source))
                    if source in formulas:
                        issues.append(dict(code="WORKBOOK_FORMULA_UNSUPPORTED", message="수식은 등록값으로 사용할 수 없습니다: " + address))
                    data[field] = value.strip()
                if not any(data.get(field) for field in FIELDS):
                    continue
                if any(not data.get(field) for field in ("system", "feature_group", "name")):
                    issues.append(dict(code="WORKBOOK_REQUIRED_CELL_BLANK", message="시스템·기능그룹·기능명 필수 셀이 비었습니다. 빈 분류를 임의 상속하지 않습니다."))
                if any(len(data.get(field, "")) > (500 if field != "description" else 10000) for field in FIELDS):
                    issues.append(dict(code="WORKBOOK_CELL_TOO_LONG", message="셀 텍스트가 지원 길이를 초과했습니다."))
                if data.get("feature_id") and not ID.fullmatch(data["feature_id"]):
                    issues.append(dict(code="WORKBOOK_FEATURE_ID_INVALID", message="원천기능ID 형식을 읽지 못했습니다. 기존 기능의 원천 식별자를 확인하세요."))
                row = dict(row_key=f"{sheet_index}:{number}", sheet=sheet, row=number, cells=positions,
                           data={**semantic(data), "feature_id": data.get("feature_id", "")})
                if issues:
                    unsupported.append(dict(sheet=sheet, row=number, reason=" / ".join(issue["message"] for issue in issues), reason_codes=[issue["code"] for issue in issues]))
                else:
                    rows.append(row)
                if len(rows) + len(unsupported) > MAX_ROWS:
                    raise Denied("WORKBOOK_ROW_LIMIT", 422)
        if not rows:
            raise Denied("WORKBOOK_NO_SUPPORTED_ROWS", 422)
        return dict(filename=name, file_sha256=parsed.digest, parser_version=PARSER, rows=rows,
                    unsupported=unsupported, limitations=LIMITATIONS)
    except DocumentError as exc:
        raise Denied(str(exc), 422) from None
    except (KeyError, ValueError, OSError, UnicodeError, TypeError):
        raise Denied("WORKBOOK_FORMAT_INVALID", 422) from None


def current_features(service):
    roots = {row["id"]: row for row in service.rows(S.features)}
    latest = {}
    for revision in service.rows(S.revisions):
        if revision["feature_id"] not in latest or revision["ordinal"] > latest[revision["feature_id"]]["ordinal"]:
            latest[revision["feature_id"]] = revision
    return {roots[key]["external_id"]: dict(root=roots[key], revision=revision, data=semantic(revision["data"]))
            for key, revision in latest.items()}


def compare_workbook(parsed, existing, catalog_digest):
    counts = Counter(tuple(row["data"][field] for field in FIELDS[:3]) for row in parsed["rows"])
    explicit_counts = Counter(row["data"].get("feature_id") for row in parsed["rows"] if row["data"].get("feature_id"))
    rows = []
    for row in parsed["rows"]:
        value = row["data"]
        explicit = value.get("feature_id", "")
        identity = lambda d: tuple(d[field] for field in FIELDS[:3])
        exact = [key for key, old in existing.items() if identity(old["data"]) == identity(value)]
        suspects = [key for key, old in existing.items() if old["data"]["name"] == value["name"] or
                    (value["description"] and old["data"]["description"] == value["description"])]
        target = explicit or (exact[0] if len(exact) == 1 else None)
        if explicit and explicit not in existing:
            status = "UNKNOWN_ID"
        elif (explicit and explicit_counts[explicit] > 1) or (not explicit and (len(exact) > 1 or (not exact and suspects) or counts[identity(value)] > 1)):
            status, target = "DUPLICATE_SUSPECT", None
        elif target:
            status = "SAME" if semantic(value) == existing[target]["data"] else "CHANGED"
        else:
            status = "NEW"
        candidate_ids = list(dict.fromkeys(exact + suspects))
        rows.append(dict(**row, status=status, target_feature_id=target,
            candidates=[dict(feature_id=key, **existing[key]["data"]) for key in candidate_ids[:30]],
            previous=existing[target]["data"] if target in existing else None))
    result = dict(filename=parsed["filename"], file_sha256=parsed["file_sha256"], parser_version=PARSER,
                  catalog_digest=catalog_digest, rows=rows, unsupported=parsed["unsupported"], limitations=LIMITATIONS)
    result["preview_digest"] = fingerprint(result)
    return result


class WorkbookImportApplication:
    def __init__(self, service):
        self.service = service

    def _owned(self, actor, file_sha):
        self.service.authorize(actor, True)
        records = [row for row in self.service.rows(S.audit, actor_id=actor.id)
                   if row["action"] == "UPLOAD_ASSET_WORKBOOK" and row["targets"].get("file_sha256") == file_sha]
        if not records:
            raise Denied("OBJECT_NOT_FOUND", 404)
        return records[-1]["targets"]

    def preview(self, actor, filename, content):
        service = self.service
        service.authorize(actor, True)
        parsed = parse_workbook(filename, content)
        storage_key, digest = service.files.put(content)
        if digest != parsed["file_sha256"]:
            raise Denied("REQUIRED_EVIDENCE_MISSING", 422)
        service.record(actor, "UPLOAD_ASSET_WORKBOOK", file_sha256=digest, storage_key=storage_key,
                       filename=parsed["filename"], parser_version=PARSER)
        return compare_workbook(parsed, current_features(service), catalog_snapshot(service)["digest"])

    def original(self, actor, file_sha):
        source = self._owned(actor, file_sha)
        content = self.service.files.read(source["storage_key"], file_sha)
        return content, source["filename"]

    def apply(self, actor, *, file_sha256, parser_version, catalog_digest, preview_digest, selections, key):
        service = self.service
        service.authorize(actor, True)
        if parser_version != PARSER:
            raise Denied("STALE_WORKBOOK_PREVIEW", 409)
        if not selections or len(selections) > MAX_ROWS or len({row["row_key"] for row in selections}) != len(selections):
            raise Denied("INVALID_WORKBOOK_SELECTION", 422)
        if not isinstance(key, str) or not key.strip() or len(key) > 100:
            raise Denied("INVALID_IDEMPOTENCY_KEY", 422)
        source = self._owned(actor, file_sha256)
        requested = sorted(selections, key=lambda row: row["row_key"])
        def execute():
            _catalog_lock(service)
            parsed = parse_workbook(source["filename"], service.files.read(source["storage_key"], file_sha256))
            existing = current_features(service)
            current = compare_workbook(parsed, existing, catalog_snapshot(service)["digest"])
            if current["catalog_digest"] != catalog_digest or current["preview_digest"] != preview_digest:
                raise Denied("STALE_WORKBOOK_PREVIEW", 409)
            by_key = {row["row_key"]: row for row in current["rows"]}
            plans, targets = [], set()
            for selection in requested:
                row = by_key.get(selection["row_key"])
                if row is None:
                    raise Denied("INVALID_WORKBOOK_SELECTION", 422)
                decision = selection.get("resolution")
                if row["status"] in ("DUPLICATE_SUSPECT", "UNKNOWN_ID") and not decision:
                    raise Denied("WORKBOOK_REVIEW_REQUIRED", 422)
                if decision and row["status"] not in ("DUPLICATE_SUSPECT", "UNKNOWN_ID") and decision != (row["target_feature_id"] or "NEW"):
                    raise Denied("INVALID_WORKBOOK_SELECTION", 422)
                target = decision or row["target_feature_id"] or "NEW"
                if target != "NEW" and (not ID.fullmatch(target) or target not in existing):
                    raise Denied("WORKBOOK_TARGET_NOT_FOUND", 422)
                if target == "NEW":
                    target = "DMP-" + sha256("\x1f".join(row["data"][field] for field in FIELDS[:3]).encode()).hexdigest()[:16].upper()
                    if target in existing or target in targets:
                        target = "DMP-" + sha256((file_sha256 + row["row_key"] + fingerprint(semantic(row["data"]))).encode()).hexdigest()[:16].upper()
                    if target in existing:
                        if existing[target]["data"] == semantic(row["data"]):
                            if target in targets:
                                raise Denied("WORKBOOK_DUPLICATE_TARGET", 422)
                            targets.add(target)
                            plans.append(dict(row=row, target=target, old=existing[target], changed=False))
                            continue
                        raise Denied("WORKBOOK_ID_COLLISION", 409)
                if target in targets:
                    raise Denied("WORKBOOK_DUPLICATE_TARGET", 422)
                targets.add(target)
                old = existing.get(target)
                plans.append(dict(row=row, target=target, old=old,
                                  changed=old is None or old["data"] != semantic(row["data"])))
            def selected_scope():
                return [dict(row_key=plan["row"]["row_key"], sheet=plan["row"]["sheet"],
                    row=plan["row"]["row"], cells=plan["row"]["cells"], target_feature_id=plan["target"],
                    applied_revision_id=plan.get("applied_revision_id") or plan["old"]["revision"]["id"],
                    changed=plan["changed"]) for plan in plans]
            changed = [plan for plan in plans if plan["changed"]]
            if not changed:
                service.record(actor, "APPLY_ASSET_WORKBOOK_NO_CHANGE", file_sha256=file_sha256,
                               selected_rows=[row["row_key"] for row in requested], parser_version=PARSER,
                               selected_scope=selected_scope())
                return dict(import_id=None, changed=0, unchanged=len(plans),
                            catalog_digest=current["catalog_digest"], file_sha256=file_sha256)
            batch_digest = fingerprint(dict(file_sha256=file_sha256, parser_version=PARSER,
                selections=[dict(row_key=p["row"]["row_key"], target=p["target"], data=semantic(p["row"]["data"]),
                    previous_revision=p["old"]["revision"]["id"] if p["old"] else None) for p in plans]))
            historical = service.rows(S.imports, digest=batch_digest)
            if historical:
                raise Denied("WORKBOOK_BATCH_ALREADY_APPLIED", 409)
            provenance = dict(file_sha256=file_sha256, storage_key=source["storage_key"], filename=source["filename"],
                parser_version=PARSER, rows=[dict(row_key=p["row"]["row_key"], sheet=p["row"]["sheet"],
                    row=p["row"]["row"], cells=p["row"]["cells"], feature_id=p["target"], data=semantic(p["row"]["data"])) for p in changed])
            systems = Counter(p["row"]["data"]["system"] for p in changed)
            metadata = dict(schema_version="workbook-v1", artifact_kind="ADMIN_WORKBOOK_INCREMENT",
                source_workbook=source["filename"], source_sheet=" / ".join(dict.fromkeys(p["row"]["sheet"] for p in changed)),
                source_display_date="", feature_count=len(changed), system_count=len(systems),
                group_count=len({(p["row"]["data"]["system"], p["row"]["data"]["feature_group"]) for p in changed}),
                uniqueness_rule="reviewed explicit target; no automatic fuzzy merge", system_counts=dict(systems),
                workbook_provenance=provenance)
            imported = service.add(S.imports, digest=batch_digest, metadata=metadata)
            for plan in changed:
                row, old = plan["row"], plan["old"]
                root = old["root"] if old else service.add(S.features, external_id=plan["target"])
                ordinal = old["revision"]["ordinal"] + 1 if old else 1
                raw = dict(feature_id=plan["target"], **semantic(row["data"]),
                    origin="WORKBOOK:" + file_sha256 + ":" + row["row_key"] + ":" + (old["revision"]["id"] if old else "NEW"), excel_row=row["row"],
                    availability="NEEDS_CONFIRMATION", availability_basis="ADMIN_WORKBOOK_REGISTRATION_NOT_PROVISION_VERIFICATION")
                revision = service.add(S.revisions, feature_id=root["id"], ordinal=ordinal, digest=fingerprint(raw), data=raw)
                service.add(S.members, import_id=imported["id"], feature_id=root["id"], revision_id=revision["id"])
                plan["applied_revision_id"] = revision["id"]
            service.record(actor, "APPLY_ASSET_WORKBOOK", import_id=imported["id"], file_sha256=file_sha256,
                           parser_version=PARSER, selected_scope=selected_scope(),
                           batch_digest=batch_digest, changed=len(changed), unchanged=len(plans)-len(changed))
            return dict(import_id=imported["id"], changed=len(changed), unchanged=len(plans)-len(changed),
                        catalog_digest=catalog_snapshot(service)["digest"], file_sha256=file_sha256)
        payload = ["APPLY_ASSET_WORKBOOK", file_sha256, parser_version, catalog_digest, preview_digest, requested]
        return service.command(actor, key, payload, execute)
