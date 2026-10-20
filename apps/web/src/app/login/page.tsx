"use client";
import {useState} from "react";
import {roleLanding} from "../../portal/types";

export default function Login() {
  const [username,setUsername]=useState("");
  const [password,setPassword]=useState("");
  const [visible,setVisible]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  return <main className="workspace-login">
    <p className="workspace-eyebrow">DATCO WORKSPACE</p>
    <h1>DATCO 정부지원사업 운영관리 시스템</h1>
    <p>기업정보 제출부터 검토·매칭·제안서까지, 내 역할에 맞는 업무를 시작하세요.</p>
    <form aria-busy={busy} onSubmit={async e=>{
      e.preventDefault(); if(busy)return;
      setBusy(true);setError("");
      try {
        const r=await fetch('/api/notice/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password}),cache:'no-store'});
        if(!r.ok)throw Error(r.status===401?'아이디 또는 비밀번호가 올바르지 않습니다. 다시 확인해 주세요.':r.status===429?'로그인 요청이 많습니다. 잠시 후 다시 시도해 주세요.':'로그인을 완료하지 못했습니다. 잠시 후 다시 시도하거나 담당자에게 문의해 주세요.');
        const actor=await r.json();if(!roleLanding[actor.role])throw Error('허용된 역할을 확인할 수 없습니다.');
        setPassword('');sessionStorage.clear();
        const channel=new BroadcastChannel('datco-session');channel.postMessage('account-change');channel.close();
        window.location.replace(roleLanding[actor.role]);
      } catch(e) {
        setError(e instanceof TypeError?'서버에 연결할 수 없습니다. 네트워크 연결을 확인하고 다시 시도해 주세요.':e instanceof Error?e.message:'로그인을 완료하지 못했습니다. 다시 시도해 주세요.');
        setBusy(false);
      }
    }}>
      <label>아이디<input autoComplete="username" required disabled={busy} value={username} onChange={e=>setUsername(e.target.value)}/></label>
      <label htmlFor="login-password">비밀번호</label>
      <div className="workspace-password"><input id="login-password" type={visible?'text':'password'} autoComplete="current-password" required disabled={busy} value={password} onChange={e=>setPassword(e.target.value)}/><button type="button" aria-controls="login-password" aria-pressed={visible} disabled={busy} onClick={()=>setVisible(!visible)}>{visible?'비밀번호 숨기기':'비밀번호 표시'}</button></div>
      {error&&<p role="alert" className="workspace-login-error">{error}</p>}
      {busy&&<p role="status">계정을 확인하고 업무 홈으로 이동하고 있습니다.</p>}
      <button className="workspace-login-submit" disabled={busy}>{busy?'로그인 중':'로그인'}</button>
    </form>
    <p className="workspace-login-help">계정에 부여된 역할과 기업 접근권한으로 연결됩니다. 계정 또는 접근권한이 필요하면 DATCO 담당자에게 문의하세요.</p>
  </main>;
}
