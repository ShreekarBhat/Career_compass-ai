"use client";
import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Notice, PageHeader, Spinner } from "@/components/ui";

type Msg = { role: "user" | "agent"; text: string; steps?: any[]; results?: any };
const SUGGESTIONS = ["I want to become an ML Engineer", "What skills am I missing?", "Find me internships that match my profile", "Create a 12 week roadmap", "I already know PyTorch", "Start a mock interview"];
const LINKS: Record<string, [string, string]> = { job_discovery: ["/jobs", "View jobs"], planner: ["/roadmap", "Open roadmap"], skill_gap: ["/skills", "Skill gap"], resume: ["/resume", "Resume report"], interview: ["/interview", "Go to interview"], tracker: ["/tracker", "Open tracker"] };

export default function ChatPage() {
  const [msgs, setMsgs] = useState<Msg[]>([{ role: "agent", text: "Hi! I'm your career agent. Tell me your goal, ask about skills, jobs or your roadmap, and I'll route it to the right specialist agents." }]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  async function send(message: string) {
    if (!message.trim() || busy) return;
    setMsgs((m) => [...m, { role: "user", text: message }]); setText(""); setBusy(true); setErr(null);
    try {
      const r = await api("/agent/chat", { body: { message } });
      setMsgs((m) => [...m, { role: "agent", text: r.response, steps: r.steps, results: r.results }]);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  const onSubmit = (e: FormEvent) => { e.preventDefault(); send(text); };

  return (
    <>
      <PageHeader title="Career agent" subtitle="One conversation, many specialist agents behind it." />
      <div className="flex h-[calc(100vh-15rem)] min-h-[420px] flex-col rounded-2xl border border-slate-200 bg-white shadow-card">
        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {msgs.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${m.role === "user" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-800"}`}>
                <div className="whitespace-pre-wrap">{m.text}</div>
                {m.steps && m.steps.length > 0 && (
                  <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-slate-200 pt-2.5">
                    <span className="text-[11px] text-slate-500">Agents:</span>
                    {m.steps.map((s: any, j: number) => <Badge key={j} tone={s.ok ? "indigo" : "red"}>{s.agent} · {s.ms}ms</Badge>)}
                  </div>
                )}
                {m.results && (
                  <div className="mt-2 flex flex-wrap gap-3">
                    {Object.keys(LINKS).filter((k) => m.results[k]).map((k) => <Link key={k} href={LINKS[k][0]} className="text-xs font-medium text-indigo-600 hover:underline">{LINKS[k][1]} →</Link>)}
                  </div>
                )}
              </div>
            </div>
          ))}
          {busy && <div className="flex items-center gap-2 text-sm text-slate-500"><Spinner className="h-4 w-4" /> Agents are working…</div>}
          <div ref={end} />
        </div>
        <div className="border-t border-slate-200 p-4">
          {msgs.length < 3 && <div className="mb-3 flex flex-wrap gap-2">{SUGGESTIONS.map((s) => <button key={s} onClick={() => send(s)} className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:border-indigo-300 hover:text-indigo-600">{s}</button>)}</div>}
          {err && <div className="mb-3"><Notice>{err}</Notice></div>}
          <form onSubmit={onSubmit} className="flex gap-2">
            <input className="field" placeholder="Ask anything about your career…" value={text} onChange={(e) => setText(e.target.value)} maxLength={2000} />
            <Button type="submit" disabled={busy || !text.trim()}><Send size={16} /></Button>
          </form>
        </div>
      </div>
    </>
  );
}
