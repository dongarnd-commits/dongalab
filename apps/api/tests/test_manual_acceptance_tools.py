"""Fail-closed tooling checks; no PostgreSQL, Docker or product state writes."""
import json
from pathlib import Path
import pytest
import manual_acceptance as uat


@pytest.mark.parametrize("nonce", ["", "../datco_test", "a" * 11, "a" * 13, "G" * 12, "datco_test_3366ee3e9236"])
def test_rejects_unowned_identifier(nonce):
    with pytest.raises(RuntimeError, match="INVALID_ACCEPTANCE_NONCE"):
        uat.owned(nonce)


def sample():
    nonce = "a123456789bc"
    return dict(nonce=nonce, root=str(uat.ROOT), head="approved-head", db="datco_test_" + nonce,
                role="datco_test_role_" + nonce, container="datco-mvp-uat-" + nonce,
                volume="datco-mvp-uat-pg-" + nonce, url="postgresql+psycopg://synthetic",
                api_port=45101, web_port=45102, host="10.10.10.145", https_port=8444,
                origin="https://10.10.10.145:8444")


@pytest.mark.parametrize("key", ["nonce", "db", "role", "root", "container", "volume"])
def test_manifest_cannot_target_another_resource(tmp_path, monkeypatch, key):
    m = sample()
    monkeypatch.setattr(uat, "BASE", tmp_path)
    out = uat.owned(m["nonce"])
    out.mkdir()
    m[key] = "not-this-environment"
    (out / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(RuntimeError, match="ACCEPTANCE_MANIFEST_MISMATCH"):
        uat.load("a123456789bc")


def test_environment_drops_live_keys_and_success_fixture_flags(monkeypatch):
    for key in ("DATABASE_URL", "DATCO_CI_ADMIN_URL", "DATCO_TEST_COMPANY", "DATCO_TEST_PROPOSAL",
                "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "BIZINFO_API_KEY"):
        monkeypatch.setenv(key, "MUST_NOT_PROPAGATE")
    env = uat.environment(sample())
    assert env["DATABASE_URL"] == sample()["url"]
    assert env["BIZINFO_API_KEY"] == ""
    for key in ("DATCO_TEST_COMPANY", "DATCO_TEST_PROPOSAL", "DATCO_CI_ADMIN_URL", "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        assert key not in env
    assert env["WEB_ORIGIN"] == sample()["origin"]
    assert env["DATCO_TEST_FILES"].endswith("files")
    assert "manual-acceptance" in env["DATCO_TEST_FILES"]


def test_gateway_is_separate_and_namespaces_cookie():
    config = uat.caddy_config(sample())
    assert "admin off" in config and "skip_install_trust" in config
    assert ":8443" not in config and ":8444" in config
    assert "datco_uat_a123456789bc" in config
    assert "request_header -Cookie" in config
    assert 'request_header Cookie "datco_session={http.regexp.uat.1}"' in config
    assert 'header_down Set-Cookie "^datco_session="' in config
    assert 'header_down Set-Cookie "$" "; Secure"' in config
    assert "respond @private 404" in config
    assert str(uat.owned(sample()["nonce"])).replace("\\\\", "/") in config or "/manual-acceptance/" in config


def test_cleanup_requires_stopped_and_explicit_nonce(tmp_path, monkeypatch):
    m = sample()
    monkeypatch.setattr(uat, "BASE", tmp_path)
    out = uat.owned(m["nonce"])
    out.mkdir()
    uat.write(out / "manifest.json", m)
    uat.write(out / "state.json", dict(phase="RUNNING"))
    monkeypatch.setattr("sys.argv", ["manual_acceptance.py", "cleanup", "--nonce", m["nonce"], "--confirm", m["nonce"]])
    monkeypatch.setattr(uat, "run", lambda *a, **k: pytest.fail("must not mutate Docker"))
    with pytest.raises(RuntimeError, match="STOP_AND_EXPLICIT"):
        uat.main()
    uat.write(out / "state.json", dict(phase="STOPPED"))
    monkeypatch.setattr("sys.argv", ["manual_acceptance.py", "cleanup", "--nonce", m["nonce"], "--confirm", "wrong"])
    with pytest.raises(RuntimeError, match="STOP_AND_EXPLICIT"):
        uat.main()

@pytest.mark.parametrize("port", [8443, 49355, 49356, 80, 65536])
def test_protected_service_ports_rejected(port):
    with pytest.raises(RuntimeError, match="PROTECTED_SERVICE_PORT"):
        uat.protect_port(port)


def test_own_staging_and_uat_ports_permitted():
    uat.protect_port(8444)
    uat.protect_port(8445)


def test_account_template_only_allows_four_synthetic_identities():
    from mvp_portal_setup import validate_template
    valid = dict(accounts={label: "TEST_MVP_" + label + "_a123456789bc"
                           for label in ("editor", "operator", "admin", "approver")},
                 password="synthetic-unit-only-not-a-live-password")
    validate_template(valid)
    for invalid in (
        dict(valid, accounts={**valid["accounts"], "editor": "actual-company-user"}),
        dict(valid, accounts={k: v for k, v in valid["accounts"].items() if k != "admin"}),
        dict(valid, password=""),
    ):
        with pytest.raises(RuntimeError):
            validate_template(invalid)


@pytest.mark.parametrize("phase,confirmation", [("RUNNING", "a123456789bc"), ("STOPPED", "wrong")])
def test_rebind_requires_stopped_exact_owned_nonce(tmp_path, monkeypatch, phase, confirmation):
    m=sample()
    monkeypatch.setattr(uat, "BASE", tmp_path)
    out=uat.owned(m["nonce"]);out.mkdir()
    uat.write(out/"manifest.json",m);uat.write(out/"state.json",dict(phase=phase))
    before=(out/"manifest.json").read_bytes()
    monkeypatch.setattr("sys.argv",["manual_acceptance.py","rebind","--nonce",m["nonce"],
                                   "--confirm",confirmation,"--https-port","8444"])
    monkeypatch.setattr(uat,"available",lambda *a: pytest.fail("must not inspect or bind service ports"))
    monkeypatch.setattr(uat,"inspect_label",lambda *a: pytest.fail("must not act on Docker"))
    with pytest.raises(RuntimeError,match="STOP_AND_EXPLICIT"):
        uat.main()
    assert (out/"manifest.json").read_bytes()==before


def test_ci_diagnostics_redact_request_secrets_and_preserve_failure():
    from ci_run import redact_test_output
    message="read ECONNRESET\n - cookie: session=synthetic-cookie\n - authorization: Bearer synthetic-token\nsynthetic-password"
    env={"DATCO_REACCEPTANCE_CONTEXT":json.dumps({"password":"synthetic-password"})}
    result=redact_test_output(message,env)
    assert "ECONNRESET" in result
    for value in ("synthetic-cookie","synthetic-token","synthetic-password"):
        assert value not in result
    assert result.count("[REDACTED]")==3
    assert redact_test_output("FAIL required check",{})=="FAIL required check"


def test_account_source_cli_imports_api_without_inherited_pythonpath(tmp_path):
    import os, subprocess, sys
    tests=Path(__file__).resolve().parent
    code="import sys;from pathlib import Path;sys.path.insert(0,"+repr(str(tests))+");import manual_acceptance as uat\ntry:uat.source_accounts(Path('not-an-owned-source'))\nexcept RuntimeError as error:\n assert str(error)=='ACCOUNT_SOURCE_NOT_OWNED_UAT'\nelse:raise AssertionError('invalid source accepted')"
    env=dict(os.environ,DATABASE_URL="postgresql+psycopg://unused:unused@127.0.0.1:1/unused")
    env.pop("PYTHONPATH",None)
    result=subprocess.run([sys.executable,"-B","-c",code],cwd=tmp_path,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_repository_common_dir_from_non_utf8_cli(tmp_path):
    import os,subprocess,sys
    tests=Path(__file__).resolve().parent
    code="import sys;sys.path.insert(0,"+repr(str(tests))+");import manual_acceptance as uat;result=uat.repository_common_dir(uat.ROOT);assert result.is_dir();assert result.name=='.git'"
    env=dict(os.environ,PYTHONUTF8="0",PYTHONIOENCODING="utf-8")
    env.pop("PYTHONPATH",None)
    result=subprocess.run([sys.executable,"-B","-c",code],cwd=tmp_path,env=env,capture_output=True,encoding="utf-8")
    assert result.returncode==0,result.stderr
