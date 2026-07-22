import { useEffect, useState } from "react";
import { LoginPage } from "./features/auth/LoginPage";
import { ImageGeneratorPage } from "./features/image-generator/ImageGeneratorPage";

const API = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

type User = { id:string; username:string };

export function App() {
  const [user,setUser]=useState<User|null>(null);
  const [checking,setChecking]=useState(true);

  useEffect(()=>{
    fetch(`${API}/auth/me`,{credentials:"include"})
      .then(async response=>{
        if (response.ok) setUser(await response.json());
        else setUser(null);
      })
      .finally(()=>setChecking(false));
  },[]);

  useEffect(()=>{
    const handleUnauthorized=()=>setUser(null);
    window.addEventListener("totem:unauthorized",handleUnauthorized);
    return ()=>window.removeEventListener("totem:unauthorized",handleUnauthorized);
  },[]);

  async function logout() {
    await fetch(`${API}/auth/logout`,{method:"POST",credentials:"include"});
    setUser(null);
  }

  if (checking) return <main className="auth-loading">正在確認登入狀態…</main>;
  if (!user) return <LoginPage onLogin={setUser}/>;
  return <div className="authenticated-app"><ImageGeneratorPage onLogout={logout}/></div>;
}
