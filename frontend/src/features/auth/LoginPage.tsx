import { FormEvent, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
type User = { id:string; username:string };

export function LoginPage({onLogin}:{onLogin:(user:User)=>void}) {
  const [username,setUsername]=useState("");
  const [password,setPassword]=useState("");
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);

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
        setError(response.status===401 ? "帳號或密碼錯誤" : "登入失敗，請稍後再試");
        return;
      }
      onLogin(await response.json());
    } finally {
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
  </main>;
}
