"use client";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getRefreshToken, getToken, setTokens } from "@/lib/api";
import { Button, Notice } from "@/components/ui";

const FEATURES = [
  "Resume intelligence with ATS scoring",
  "Job matching ranked by skills and semantics",
  "Skill-gap analysis and adaptive roadmaps",
  "AI mock interviews with scored feedback",
  "Application tracking and Telegram alerts",
];

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { if (getToken() || getRefreshToken()) router.replace("/dashboard"); }, [router]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      const r = mode === "login"
        ? await api("/auth/login-json", { body: { email, password } })
        : await api("/auth/register", { body: { email, password, full_name: name } });
      setTokens(r.access_token, r.refresh_token);
      router.replace("/dashboard");
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-slate-900 p-12 text-white lg:flex">
        <div className="text-xl font-semibold">Career Compass <span className="text-indigo-400">AI</span></div>
        <div>
          <h1 className="text-4xl font-semibold leading-tight">An autonomous AI assistant for your career.</h1>
          <ul className="mt-8 space-y-3 text-slate-300">
            {FEATURES.map((f) => <li key={f} className="flex items-center gap-3"><span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />{f}</li>)}
          </ul>
        </div>
        <div className="text-xs text-slate-500">Final-year project · Multi-agent system with LangGraph, RAG and pgvector</div>
      </div>
      <div className="grid place-items-center px-6 py-12">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">{mode === "login" ? "Welcome back" : "Create your account"}</h2>
            <p className="mt-1 text-sm text-slate-500">{mode === "login" ? "Sign in to continue." : "Start building your career profile."}</p>
          </div>
          {mode === "register" && <input className="field" placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} />}
          <input className="field" type="email" required placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className="field" type="password" required minLength={8} placeholder="Password (min 8 characters)" value={password} onChange={(e) => setPassword(e.target.value)} />
          {err && <Notice>{err}</Notice>}
          <Button type="submit" loading={busy} className="w-full">{mode === "login" ? "Sign in" : "Create account"}</Button>
          <p className="text-center text-sm text-slate-500">
            {mode === "login" ? "New here?" : "Already have an account?"}{" "}
            <button type="button" className="font-medium text-indigo-600 hover:underline" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(null); }}>
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
