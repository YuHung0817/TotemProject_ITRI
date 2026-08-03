import { FormEvent, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
type User = { id:string; username:string };
type SessionConflict = { challenge:string; active_since?:string };

export function LoginPage({onLogin}:{onLogin:(user:User)=>void}) {
  const [username,setUsername]=useState("");
  const [password,setPassword]=useState("");
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const [sessionConflict,setSessionConflict]=useState<SessionConflict|null>(null);

  async function submit(event:FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response=await fetch(`${API}/auth/login`,{
        method:"POST",
        credentials:"include",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({username,password}),
      });
      if (!response.ok) {
        const data=await response.json().catch(()=>({}));
        if(response.status===409&&data.detail?.code==="session_already_active"&&data.detail?.challenge){
          setSessionConflict({challenge:data.detail.challenge,active_since:data.detail.active_since});
          return;
        }
        setError(response.status===401 ? "帳號或密碼錯誤" : "登入失敗，請稍後再試");
        return;
      }
      onLogin(await response.json());
    } finally {
      setBusy(false);
    }
  }

  async function replaceSession() {
    if(!sessionConflict||busy)return;
    setBusy(true);
    setError("");
    try{
      const response=await fetch(`${API}/auth/login/replace`,{
        method:"POST",
        credentials:"include",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({challenge:sessionConflict.challenge}),
      });
      const data=await response.json().catch(()=>({}));
      if(!response.ok){
        setSessionConflict(null);
        setError(data.detail?.message??"登入確認已失效，請重新登入");
        return;
      }
      setSessionConflict(null);
      onLogin(data);
    }catch{
      setError("登入失敗，請檢查網路後再試");
    }finally{
      setBusy(false);
    }
  }

  return <main className="login-page">
    <form className="login-card" onSubmit={submit}>
      <div className="login-mark">AI</div>
      <h1>商家登入</h1>
      <p>請使用單一商家帳號登入</p>
      <label>帳號<input autoComplete="username" value={username} onChange={event=>setUsername(event.target.value)} onInvalid={event=>event.currentTarget.setCustomValidity("請輸入帳號")} onInput={event=>event.currentTarget.setCustomValidity("")} required/></label>
      <label>密碼<input type="password" autoComplete="current-password" value={password} onChange={event=>setPassword(event.target.value)} onInvalid={event=>event.currentTarget.setCustomValidity("請輸入密碼")} onInput={event=>event.currentTarget.setCustomValidity("")} required/></label>
      {error && <div className="login-error" role="alert">{error}</div>}
      <button type="submit" disabled={busy}>{busy ? "登入中…" : "登入"}</button>
    </form>
    {sessionConflict&&<div className="session-conflict-layer">
      <section className="session-conflict-dialog" role="dialog" aria-modal="true" aria-labelledby="session-conflict-title">
        <div className="session-conflict-mark" aria-hidden="true">!</div>
        <h2 id="session-conflict-title">帳號已在其他裝置登入</h2>
        <p>是否登出先前裝置，並在這台裝置繼續？</p>
        {sessionConflict.active_since&&<small>先前登入時間：{new Intl.DateTimeFormat("zh-TW",{month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hour12:false}).format(new Date(sessionConflict.active_since))}</small>}
        <div className="session-conflict-actions"><button type="button" disabled={busy} onClick={()=>setSessionConflict(null)}>取消</button><button type="button" disabled={busy} onClick={()=>void replaceSession()}>{busy?"切換中…":"登出先前登入"}</button></div>
      </section>
    </div>}
  </main>;
}
