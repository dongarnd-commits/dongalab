from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac, sha256
from hmac import compare_digest
import secrets
from app.notice.domain import Actor, Denied

def hash_password(password):
    salt=secrets.token_hex(16)
    digest=pbkdf2_hmac("sha256",password.encode(),salt.encode(),600000).hex()
    return salt+":"+digest

def login(store,username,password):
    users=store.rows("actors",username=username)
    # Equal hash work for missing users; errors never contain submitted input.
    stored=users[0]["password_hash"] if users else "missing:"+("0"*64)
    salt,digest=stored.split(":",1)
    actual=pbkdf2_hmac("sha256",password.encode(),salt.encode(),600000).hex()
    if not users or not compare_digest(actual,digest):
        raise Denied("LOGIN_DENIED",401)
    token=secrets.token_urlsafe(32)
    store.add("sessions",actor_id=users[0]["id"],token_hash=sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc)+timedelta(hours=8))
    store.add("audits",actor_id=users[0]["id"],action="LOGIN",reason="Local demo session")
    return token

def authenticated(store,token):
    if not token:
        raise Denied("AUTHENTICATION_REQUIRED",401)
    sessions=store.rows("sessions",token_hash=sha256(token.encode()).hexdigest())
    if not sessions or sessions[0]["expires_at"]<=datetime.now(timezone.utc):
        raise Denied("AUTHENTICATION_REQUIRED",401)
    user=store.get("actors",sessions[0]["actor_id"])
    return Actor(user["id"],user["role"])
