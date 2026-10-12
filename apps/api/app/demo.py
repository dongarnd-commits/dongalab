# CLI-only sanitized input loader; never seeds Candidate/Review/Confirmed results.
import argparse
import json
from hashlib import sha256
from pathlib import Path
from app.core.config import ROOT
from app.infrastructure.database import get_session_factory
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure.local_auth import hash_password
from dotenv import dotenv_values

FIXTURES=Path(__file__).resolve().parents[1]/"fixtures/notice"

def load_input(store,files,name,external_key=None):
    metadata=json.loads((FIXTURES/(name+".json")).read_text(encoding="utf-8"))
    key=external_key or metadata["external_key"]
    existing=store.rows("notices",external_key=key)
    if existing:
        notice=store.get("notices",existing[0]["id"],True)
        current=next(v for v in store.rows("versions",notice_id=notice["id"]) if v["ordinal"]==notice["current_ordinal"])
        current_sources=store.rows("sources",version_id=current["id"])
        expected={r["name"]:sha256((FIXTURES/r["file"]).read_bytes()).hexdigest() if r.get("file") else None for r in metadata["sources"]}
        actual={r["name"]:r["digest"] for r in current_sources}
        if expected==actual and current["metadata"]==metadata["metadata"]:
            return notice
        ordinal=notice["current_ordinal"]+1
        store.change("notices",notice["id"],current_ordinal=ordinal)
    else:
        ordinal=1
        notice=store.add("notices",external_key=key,title=metadata["title"],current_ordinal=ordinal)
    version=store.add("versions",notice_id=notice["id"],ordinal=ordinal,mode="DEMO_TEST",
        metadata=metadata["metadata"])
    for reference in metadata["sources"]:
        data=(FIXTURES/reference["file"]).read_bytes() if reference.get("file") else None
        storage,digest=files.put(data) if data is not None else (None,None)
        store.add("sources",version_id=version["id"],name=reference["name"],media_type=reference["media_type"],
            provenance="Synthetic DEMO/TEST notice source; not a real government notice",
            storage_key=storage,digest=digest)
    store.add("audits",actor_id=None,notice_version_id=version["id"],action="IMPORT_NEW_NOTICE" if ordinal==1 else "CREATE_NOTICE_VERSION",reason="Input-only synthetic DEMO/TEST fixture")
    return notice

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--fixture",choices=["normal","conflict","partial"],default="normal")
    args=parser.parse_args()
    env=dotenv_values(ROOT/".env")
    username=env.get("DEMO_OPERATOR_USER","operator")
    password=env.get("DEMO_OPERATOR_PASSWORD")
    if not password:
        raise SystemExit("Configure DEMO_OPERATOR_PASSWORD in ignored root .env; values are never printed.")
    with get_session_factory().begin() as session:
        store=SqlNoticeStore(session)
        if not store.rows("actors",username=username):
            store.add("actors",username=username,role="DATCO_OPERATOR",password_hash=hash_password(password))
        notice=load_input(store,LocalPrivateFiles(ROOT/"storage/private/notice"),args.fixture)
        print("DEMO/TEST input prepared; notice id:",notice["id"])

if __name__=="__main__":
    main()
