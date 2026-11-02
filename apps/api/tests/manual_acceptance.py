"""Persistent synthetic UAT lifecycle. Never reads the ordinary DATABASE_URL/.env.
All children, PostgreSQL volume and private files belong to one random nonce.
Stop preserves data; explicit cleanup removes ONLY the labelled container/volume.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from uuid import uuid4
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
API, WEB = ROOT / "apps/api", ROOT / "apps/web"
BASE = ROOT / "storage/private/runtime/manual-acceptance"
LABEL = "datco.manual_acceptance"
HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def owned(nonce):
    if not re.fullmatch(r"[a-f0-9]{12}", nonce):
        raise RuntimeError("INVALID_ACCEPTANCE_NONCE")
    path = (BASE / nonce).resolve()
    if path.parent != BASE.resolve():
        raise RuntimeError("ACCEPTANCE_PATH_REJECTED")
    return path


def write(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    for attempt in range(50):
        try:
            temp.replace(path)
            return
        except PermissionError:
            if attempt == 49:
                raise
            time.sleep(.1)


def load(nonce):
    m = json.loads((owned(nonce) / "manifest.json").read_text(encoding="utf-8"))
    if (m["nonce"] != nonce or m["db"] != "datco_test_" + nonce
            or m["role"] != "datco_test_role_" + nonce
            or m["container"] != "datco-mvp-uat-" + nonce
            or m["volume"] != "datco-mvp-uat-pg-" + nonce
            or Path(m["root"]).resolve() != ROOT.resolve()):
        raise RuntimeError("ACCEPTANCE_MANIFEST_MISMATCH")
    return m


def head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def environment(m):
    out = owned(m["nonce"])
    # Do not inherit fixture flags, live-provider credentials or another DB.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("DATCO_", "OPENAI_", "ANTHROPIC_", "GEMINI_", "GOOGLE_API_", "BIZINFO_"))
           and k not in ("DATABASE_URL", "API_ORIGIN", "CAPABILITY_API_ORIGIN", "WEB_ORIGIN")}
    env.update(DATABASE_URL=m["url"], DATCO_TEST_DATABASE=m["db"],
               DATCO_TEST_DB_ROLE=m["role"], DATCO_TEST_NONCE=m["nonce"],
               DATCO_CI_SYNTHETIC="1", BIZINFO_API_KEY="",
               PYTHONPATH=str(API) + os.pathsep + str(API / "tests"),
               PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1",
               DATCO_TEST_FILES=str(out / "files"),
               DATCO_TEST_WORKER_READY=str(out / "worker-ready.json"),
               DATCO_MVP_READY=str(out / "accounts.json"),
               WEB_ORIGIN=m["origin"],
               API_ORIGIN="http://127.0.0.1:" + str(m["api_port"]),
               CAPABILITY_API_ORIGIN="http://127.0.0.1:" + str(m["api_port"]),
               DATCO_TEST_DIST_DIR=".next/datco-e2e-" + m["nonce"],
               DATCO_OCR_DOCKER_IMAGE="datco-local-ocr:pr14-v1",
               XDG_DATA_HOME=str(out / "caddy-data"),
               XDG_CONFIG_HOME=str(out / "caddy-config"))
    return env


def run(m, args, cwd=API, log="provision.log"):
    if args[0] == "npm" and os.name == "nt":
        args = ["cmd.exe", "/c", "npm.cmd", *args[1:]]
    with (owned(m["nonce"]) / log).open("a", encoding="utf-8") as output:
        subprocess.run(args, cwd=cwd, env=environment(m), stdout=output,
                       stderr=subprocess.STDOUT, creationflags=HIDDEN, check=True)


def inspect_label(kind, name, nonce):
    value = json.loads(subprocess.check_output(["docker", kind, "inspect", name], text=True))[0]
    labels = value["Config"].get("Labels", {}) if kind == "container" else value.get("Labels", {})
    if labels.get(LABEL) != nonce:
        raise RuntimeError("DOCKER_OWNERSHIP_MISMATCH")
    return value


def available(host, port):
    with socket.socket() as sock:
        sock.bind((host, port))


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def caddy_config(m):
    # Same IP on another port normally shares browser cookies. Only the UAT
    # namespaced cookie is forwarded; original datco_session is never forwarded.
    out = owned(m["nonce"]).as_posix()
    cookie = "datco_uat_" + m["nonce"]
    return f"""{{
    admin off
    auto_https disable_redirects
    skip_install_trust
    storage file_system {{
        root "{out}/tls"
    }}
}}
https://{m["host"]}:{m["https_port"]} {{
    bind {m["host"]}
    tls internal
    @private path /__test /__test/*
    @session header_regexp uat Cookie "(?:^|;[ ]*){cookie}=([^;]+)"
    route {{
        respond @private 404
        header {{
            X-DATCO-Acceptance "{m["nonce"]}"
            X-Robots-Tag "noindex, nofollow"
            Referrer-Policy "no-referrer"
        }}
        handle @session {{
            request_header Cookie "datco_session={{http.regexp.uat.1}}"
            reverse_proxy 127.0.0.1:{m["web_port"]} {{
                header_down Set-Cookie "^datco_session=" "{cookie}="
                header_down Set-Cookie "$" "; Secure"
            }}
        }}
        handle {{
            request_header -Cookie
            reverse_proxy 127.0.0.1:{m["web_port"]} {{
                header_down Set-Cookie "^datco_session=" "{cookie}="
                header_down Set-Cookie "$" "; Secure"
            }}
        }}
    }}
}}
"""



def protect_port(port):
    if not 1024 <= port <= 65535 or port in (8443, 49355, 49356):
        raise RuntimeError("PROTECTED_SERVICE_PORT")


def source_accounts(directory):
    """Read-only verification of THIS repo's labelled synthetic UAT identities."""
    import psycopg
    from sqlalchemy.engine import make_url
    from hashlib import pbkdf2_hmac
    from hmac import compare_digest
    # CLI callers start at the repository root, before child env PYTHONPATH exists.
    sys.path.insert(0,str(API))
    from mvp_portal_setup import validate_template
    path=Path(directory).resolve()
    if not re.fullmatch(r"[a-f0-9]{12}",path.name) or path.parent.name!="manual-acceptance":
        raise RuntimeError("ACCOUNT_SOURCE_NOT_OWNED_UAT")
    source=json.loads((path/"manifest.json").read_text(encoding="utf-8"))
    project=path.parents[4]
    if (Path(source["root"]).resolve()!=project or project.parent!=ROOT.parent
            or source["nonce"]!=path.name or source["db"]!="datco_test_"+path.name
            or source["role"]!="datco_test_role_"+path.name
            or source["container"]!="datco-mvp-uat-"+path.name):
        raise RuntimeError("ACCOUNT_SOURCE_OWNERSHIP_MISMATCH")
    def common(project):
        value=Path(subprocess.check_output(["git","rev-parse","--git-common-dir"],cwd=project,text=True).strip())
        return (value if value.is_absolute() else project/value).resolve()
    if common(project)!=common(ROOT):
        raise RuntimeError("ACCOUNT_SOURCE_REPOSITORY_MISMATCH")
    resource=inspect_label("container",source["container"],source["nonce"])
    mappings=resource["NetworkSettings"]["Ports"].get("5432/tcp") or []
    if not any(p["HostIp"]=="127.0.0.1" and int(p["HostPort"])==source["pg_port"] for p in mappings):
        raise RuntimeError("ACCOUNT_SOURCE_POSTGRES_PORT_MISMATCH")
    context=json.loads((path/"accounts.json").read_text(encoding="utf-8"))
    validate_template(context)
    url=make_url(source["url"])
    if url.host!="127.0.0.1" or url.port!=source["pg_port"] or url.database!=source["db"] or url.username!=source["role"]:
        raise RuntimeError("ACCOUNT_SOURCE_DATABASE_MISMATCH")
    with psycopg.connect(host=url.host,port=url.port,dbname=url.database,user=url.username,password=url.password) as connection:
        identity=connection.execute("select current_database(),current_user").fetchone()
        privileges=connection.execute("select rolsuper,rolcreatedb,rolcreaterole from pg_roles where rolname=current_user").fetchone()
        if identity!=(source["db"],source["role"]) or any(privileges):
            raise RuntimeError("ACCOUNT_SOURCE_ISOLATION_FAILED")
        rows=connection.execute("select username,role,password_hash from local_actors where username=ANY(%s)",(list(context["accounts"].values()),)).fetchall()
        expected=dict(editor="COMPANY_EDITOR",operator="DATCO_OPERATOR",admin="DATCO_ADMIN",approver="COMPANY_APPROVER")
        by_name={row[0]:row for row in rows}
        for label,username in context["accounts"].items():
            row=by_name.get(username)
            if not row or row[1]!=expected[label]:
                raise RuntimeError("ACCOUNT_SOURCE_ROLE_MISMATCH")
            salt,stored=row[2].split(":",1)
            actual=pbkdf2_hmac("sha256",context["password"].encode(),salt.encode(),600000).hex()
            if not compare_digest(actual,stored):
                raise RuntimeError("ACCOUNT_SOURCE_PASSWORD_VERIFICATION_FAILED")
    return dict(accounts=context["accounts"],password=context["password"]),path


def create(args):
    from sqlalchemy.engine import URL
    import psycopg
    from psycopg import sql
    if args.host != "10.10.10.145":
        raise RuntimeError("EXPLICIT_LOCAL_LAN_ADDRESS_REQUIRED")
    protect_port(args.https_port)
    available(args.host, args.https_port)
    template,source=(source_accounts(args.accounts_from) if getattr(args,"accounts_from",None) else (None,None))
    nonce = uuid4().hex[:12]
    out = owned(nonce)
    out.mkdir(parents=True)
    if os.name == "nt":
        sid = list(csv.reader(subprocess.check_output(
            ["whoami", "/user", "/fo", "csv", "/nh"], text=True).strip().splitlines()))[0][1]
        subprocess.run(["icacls", str(out), "/inheritance:r", "/grant:r",
                        "*" + sid + ":(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"],
                       check=True, capture_output=True, creationflags=HIDDEN)
    else:
        out.chmod(0o700)
    ports = set()
    while len(ports) < 3:
        ports.add(free_port())
    pg, api, web = sorted(ports)
    m = dict(nonce=nonce, root=str(ROOT), head=head(), host=args.host,
             https_port=args.https_port, api_port=api, web_port=web, pg_port=pg,
             origin=f"https://{args.host}:{args.https_port}",
             db="datco_test_" + nonce, role="datco_test_role_" + nonce,
             container="datco-mvp-uat-" + nonce, volume="datco-mvp-uat-pg-" + nonce,
             caddy=str(Path(args.caddy).resolve()), admin_password=secrets.token_urlsafe(32))
    m["url"] = URL.create("postgresql+psycopg", username=m["role"],
                         password=secrets.token_urlsafe(32), host="127.0.0.1",
                         port=pg, database=m["db"]).render_as_string(hide_password=False)
    if source:
        m["account_source_nonce"]=source.name
        for part in ("pki","certificates"):
            origin=(source/"tls"/part).resolve()
            if origin.exists():
                if not origin.is_relative_to((source/"tls").resolve()):
                    raise RuntimeError("UAT_TLS_SOURCE_PATH_REJECTED")
                shutil.copytree(origin,out/"tls"/part)
    if template:
        write(out/"account-template.json",template)
    write(out / "manifest.json", m)
    (out / "postgres.env").write_text("POSTGRES_USER=ci_provisioner\nPOSTGRES_DB=datco_ci_admin\nPOSTGRES_PASSWORD=" + m["admin_password"] + "\n", encoding="utf-8")
    (out / "Caddyfile").write_text(caddy_config(m), encoding="utf-8")
    for name in ("files", "inputs", "evidence", "downloads"):
        (out / name).mkdir()
    write(out / "state.json", dict(nonce=nonce, phase="PROVISIONING", head=m["head"]))
    print("ACCEPTANCE_NONCE=" + nonce, flush=True)
    run(m, [m["caddy"], "validate", "--config", str(out / "Caddyfile"), "--adapter", "caddyfile"])
    run(m, ["docker", "volume", "create", "--label", LABEL + "=" + nonce, m["volume"]])
    run(m, ["docker", "run", "-d", "--name", m["container"], "--label", LABEL + "=" + nonce,
            "--env-file", str(out / "postgres.env"), "-p", f"127.0.0.1:{pg}:5432",
            "--mount", "type=volume,source=" + m["volume"] + ",target=/var/lib/postgresql/data",
            "postgres:17"])
    inspect_label("container", m["container"], nonce)
    deadline = time.monotonic() + 90
    while subprocess.run(["docker", "exec", m["container"], "pg_isready", "-U", "ci_provisioner",
                          "-d", "datco_ci_admin"], capture_output=True, creationflags=HIDDEN).returncode:
        if time.monotonic() > deadline:
            raise RuntimeError("OWN_POSTGRES_NOT_READY")
        time.sleep(.5)
    from sqlalchemy.engine import make_url
    url = make_url(m["url"])
    with psycopg.connect(host="127.0.0.1", port=pg, dbname="datco_ci_admin",
                        user="ci_provisioner", password=m["admin_password"], autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD {}").format(sql.Identifier(m["role"]), sql.Literal(url.password)))
        admin.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(m["db"]), sql.Identifier(m["role"])))
    run(m, [sys.executable, "-c", "from isolation import require_test_database; require_test_database()"])
    print("ISOLATED_POSTGRES_READY", flush=True)
    run(m, [sys.executable, "-m", "alembic", "upgrade", "head"])
    run(m, [sys.executable, "-m", "alembic", "check"])
    run(m, [sys.executable, "tests/mvp_portal_setup.py", *(["--accounts-template",str(out/"account-template.json")] if template else [])])
    run(m, [sys.executable, "tests/manual_acceptance_seed.py", "--nonce", nonce,
            "--inventory", str(Path(args.inventory).resolve())])
    config = WEB / (".next/datco-config-" + nonce) / "tsconfig.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps(dict(extends="../../tsconfig.json",
        compilerOptions=dict(paths={"@/*": [str(WEB / "src/*")]}),
        include=[str(WEB / "next-env.d.ts"), str(WEB / "src/**/*.ts"),
                 str(WEB / "src/**/*.tsx"), str(WEB / "tests/**/*.ts"),
                 str(WEB / (".next/datco-e2e-" + nonce) / "types/**/*.ts")],
        exclude=[str(WEB / "node_modules")])), encoding="utf-8")
    print("SYNTHETIC_INPUTS_READY_BUILDING_WEB", flush=True)
    next_env = WEB / "next-env.d.ts"
    original_next_env = next_env.read_bytes()
    try:
        run(m, ["npm", "run", "build"], WEB, "build.log")
    finally:
        next_env.write_bytes(original_next_env)
    run(m, [m["caddy"], "validate", "--config", str(out / "Caddyfile"), "--adapter", "caddyfile"])
    write(out / "state.json", dict(nonce=nonce, phase="STOPPED", head=m["head"]))
    print("CREATED " + nonce + " " + m["origin"], flush=True)


def wait_url(url, processes, deadline=120):
    until = time.monotonic() + deadline
    while time.monotonic() < until:
        if any(p.poll() is not None for p in processes):
            raise RuntimeError("ACCEPTANCE_CHILD_EXITED")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return json.load(response) if url.endswith("/identity") else response.status
        except (OSError, ValueError):
            time.sleep(.25)
    raise RuntimeError("ACCEPTANCE_SERVICE_TIMEOUT")


def serve(m):
    out = owned(m["nonce"])
    if head() != m["head"]:
        raise RuntimeError("SOURCE_HEAD_CHANGED_REBUILD_REQUIRES_REVIEW")
    inspect_label("container", m["container"], m["nonce"])
    children, logs = [], []
    def spawn(label, command, cwd):
        log = (out / (label + ".log")).open("a", encoding="utf-8")
        logs.append(log)
        children.append(subprocess.Popen(command, cwd=cwd, env=environment(m),
                        stdout=log, stderr=subprocess.STDOUT, creationflags=HIDDEN))
    try:
        run(m, ["docker", "start", m["container"]])
        for port in (m["api_port"], m["web_port"]):
            available("127.0.0.1", port)
        available(m["host"], m["https_port"])
        ready = out / "worker-ready.json"
        ready.unlink(missing_ok=True)
        spawn("api", [sys.executable, "-m", "uvicorn", "manual_acceptance_server:app",
                      "--host", "127.0.0.1", "--port", str(m["api_port"])], API)
        identity = wait_url("http://127.0.0.1:" + str(m["api_port"]) + "/__test/identity", children)
        if identity["database"] != m["db"] or identity["db_user"] != m["role"] or identity["nonce"] != m["nonce"]:
            raise RuntimeError("API_IDENTITY_MISMATCH")
        spawn("worker", [sys.executable, "tests/isolated_worker.py"], API)
        until = time.monotonic() + 45
        while not ready.exists():
            if children[-1].poll() is not None or time.monotonic() > until:
                raise RuntimeError("WORKER_NOT_READY")
            time.sleep(.2)
        worker = json.loads(ready.read_text(encoding="utf-8"))
        if worker["database"] != m["db"] or worker["db_user"] != m["role"]:
            raise RuntimeError("WORKER_IDENTITY_MISMATCH")
        spawn("web", ["node", "node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1",
                      "--port", str(m["web_port"])], WEB)
        wait_url("http://127.0.0.1:" + str(m["web_port"]), children)
        spawn("gateway", [m["caddy"], "run", "--config", str(out / "Caddyfile"), "--adapter", "caddyfile"], ROOT)
        time.sleep(3)
        if any(p.poll() is not None for p in children):
            raise RuntimeError("ACCEPTANCE_CHILD_EXITED")
        write(out / "state.json", dict(nonce=m["nonce"], phase="RUNNING", supervisor=os.getpid(),
              children=[p.pid for p in children], head=m["head"], origin=m["origin"]))
        while not (out / "stop.request").exists():
            if any(p.poll() is not None for p in children):
                raise RuntimeError("ACCEPTANCE_CHILD_EXITED")
            time.sleep(.5)
    except Exception as exc:
        write(out / "state.json", dict(nonce=m["nonce"], phase="FAILED", reason=type(exc).__name__))
        raise
    finally:
        for process in reversed(children):
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   capture_output=True, creationflags=HIDDEN)
                else:
                    process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
        for log in logs:
            log.close()
        if (out / "stop.request").exists():
            (out / "stop.request").unlink()
            write(out / "state.json", dict(nonce=m["nonce"], phase="STOPPED", head=m["head"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "start", "serve", "status", "stop", "rebind", "cleanup"))
    parser.add_argument("--nonce")
    parser.add_argument("--host", default="10.10.10.145")
    parser.add_argument("--https-port", type=int, default=8444)
    parser.add_argument("--caddy")
    parser.add_argument("--inventory")
    parser.add_argument("--accounts-from", type=Path)
    parser.add_argument("--confirm")
    parser.add_argument("--confirm-prompt", action="store_true")
    args = parser.parse_args()
    if args.action == "create":
        create(args)
        return
    m = load(args.nonce)
    out = owned(args.nonce)
    state = json.loads((out / "state.json").read_text(encoding="utf-8"))
    if args.action == "status":
        print(json.dumps(state, ensure_ascii=False))
    elif args.action == "start":
        if state["phase"] not in ("STOPPED",):
            raise RuntimeError("ONLY_STOPPED_ENVIRONMENT_CAN_START")
        if head() != m["head"]:
            raise RuntimeError("SOURCE_HEAD_CHANGED")
        write(out / "state.json", dict(nonce=args.nonce, phase="STARTING"))
        with (out / "supervisor.log").open("a", encoding="utf-8") as log:
            subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "serve", "--nonce", args.nonce],
                             cwd=ROOT, env=environment(m), stdout=log, stderr=subprocess.STDOUT,
                             creationflags=HIDDEN, start_new_session=os.name != "nt")
        until = time.monotonic() + 150
        while time.monotonic() < until:
            state = json.loads((out / "state.json").read_text(encoding="utf-8"))
            if state["phase"] == "RUNNING":
                print("RUNNING " + m["origin"])
                return
            if state["phase"] == "FAILED":
                raise RuntimeError("SUPERVISOR_FAILED_SEE_PRIVATE_LOG")
            time.sleep(.5)
        raise RuntimeError("START_TIMEOUT_REVIEW_PRIVATE_STATE")
    elif args.action == "serve":
        serve(m)
    elif args.action == "stop":
        if state["phase"] == "STOPPED":
            print("ALREADY_STOPPED_DATA_PRESERVED")
            return
        if state["phase"] != "RUNNING":
            raise RuntimeError("REVIEW_FAILED_OR_STARTING_STATE_BEFORE_STOP")
        (out / "stop.request").write_text(args.nonce, encoding="utf-8")
        until = time.monotonic() + 45
        while time.monotonic() < until:
            state = json.loads((out / "state.json").read_text(encoding="utf-8"))
            if state["phase"] == "STOPPED":
                run(m, ["docker", "stop", m["container"]])
                print("STOPPED_DATA_PRESERVED")
                return
            time.sleep(.5)
        raise RuntimeError("STOP_TIMEOUT_NO_UNVERIFIED_PID_KILL")
    elif args.action == "rebind":
        if state["phase"]!="STOPPED" or args.confirm!=args.nonce:
            raise RuntimeError("STOP_AND_EXPLICIT_NONCE_CONFIRMATION_REQUIRED")
        protect_port(args.https_port)
        available(m["host"],args.https_port)
        inspect_label("container",m["container"],args.nonce)
        previous=m["origin"]
        m["https_port"]=args.https_port
        m["origin"]="https://"+m["host"]+":"+str(args.https_port)
        write(out/"manifest.json",m)
        (out/"Caddyfile").write_text(caddy_config(m),encoding="utf-8")
        guide=out/"RUNBOOK.md"
        if guide.exists():
            guide.write_text(guide.read_text(encoding="utf-8").replace(previous,m["origin"]),encoding="utf-8")
        print("OWN_UAT_PORT_UPDATED_DATA_AND_CREDENTIALS_PRESERVED")
    elif args.action == "cleanup":
        if args.confirm_prompt:
            args.confirm = input("Type this acceptance nonce to remove its own DB volume: ").strip()
        if state["phase"] != "STOPPED" or args.confirm != args.nonce:
            raise RuntimeError("STOP_AND_EXPLICIT_NONCE_CONFIRMATION_REQUIRED")
        inspect_label("container", m["container"], args.nonce)
        inspect_label("volume", m["volume"], args.nonce)
        run(m, ["docker", "rm", "-f", m["container"]])
        run(m, ["docker", "volume", "rm", m["volume"]])
        write(out / "state.json", dict(nonce=args.nonce, phase="REMOVED",
              note="Private inputs, findings and evidence retained; DB volume removed."))
        print("OWN_DATABASE_REMOVED_PRIVATE_EVIDENCE_RETAINED")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("ACCEPTANCE_ACTION_FAILED: " + type(error).__name__ + "; inspect the protected runtime logs.", file=sys.stderr)
        sys.exit(1)
