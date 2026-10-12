"use client";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { Badge, Button, Card, Chips, Empty, Notice, PageHeader, Spinner, fmtDate, useApi } from "@/components/ui";

export default function RoadmapPage() {
  const rm = useApi<any>("/roadmap");
  const [weeks, setWeeks] = useState(12);
  const [hours, setHours] = useState(10);
  const [known, setKnown] = useState("");
  const [busy, setBusy] = useState<"gen" | "adj" | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function generate() {
    setBusy("gen"); setErr(null); setMsg(null);
    try { await api("/roadmap/generate", { body: { weeks, hours_per_week: hours } }); await rm.reload(); }
    catch (e: any) { setErr(e.message); } finally { setBusy(null); }
  }
  async function adjust(e: FormEvent) {
    e.preventDefault();
    const skills = known.split(",").map((s) => s.trim()).filter(Boolean);
    if (!skills.length) return;
    setBusy("adj"); setErr(null); setMsg(null);
    try {
      const r = await api("/roadmap/adjust", { body: { known_skills: skills, weeks, hours_per_week: hours } });
      setMsg(r.response ?? "Roadmap updated."); setKnown(""); await rm.reload();
    } catch (e: any) { setErr(e.message); } finally { setBusy(null); }
  }

  const data = rm.data?.roadmap;
  return (
    <>
      <PageHeader title="Learning roadmap" subtitle={rm.data ? `${rm.data.target_role} · version ${rm.data.version} · generated ${fmtDate(rm.data.created_at)}` : "A personalised, dependency-ordered weekly plan."} />
      <Card className="mb-6">
        <div className="grid gap-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
          <label className="text-sm"><span className="mb-1.5 block font-medium text-slate-700">Duration: {weeks} weeks</span>
            <input type="range" min={4} max={26} value={weeks} onChange={(e) => setWeeks(+e.target.value)} className="w-full" /></label>
          <label className="text-sm"><span className="mb-1.5 block font-medium text-slate-700">Study time: {hours} h/week</span>
            <input type="range" min={3} max={40} value={hours} onChange={(e) => setHours(+e.target.value)} className="w-full" /></label>
          <Button onClick={generate} loading={busy === "gen"}>{rm.data ? "Regenerate" : "Generate roadmap"}</Button>
        </div>
        <form onSubmit={adjust} className="mt-5 flex flex-col gap-2 border-t border-slate-100 pt-5 sm:flex-row">
          <input className="field" placeholder="I already know… (e.g. PyTorch, Docker)" value={known} onChange={(e) => setKnown(e.target.value)} />
          <Button type="submit" variant="secondary" loading={busy === "adj"} disabled={!known.trim()}>Adapt plan</Button>
        </form>
      </Card>
      {err && <div className="mb-4"><Notice>{err}</Notice></div>}
      {msg && <div className="mb-4"><Notice kind="success">{msg}</Notice></div>}

      {rm.loading ? <div className="grid place-items-center py-16"><Spinner /></div>
        : !data ? <Empty title="No roadmap yet">Set a target role (Skill gap page), then generate one here.</Empty>
        : (
          <>
            <ol className="relative space-y-5 border-l-2 border-indigo-100 pl-6">
              {data.milestones?.map((m: any, i: number) => (
                <li key={i} className="relative">
                  <span className="absolute -left-[33px] top-5 h-3.5 w-3.5 rounded-full border-2 border-white bg-indigo-500 ring-4 ring-indigo-100" />
                  <Card>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <Badge tone="indigo">Week {m.weeks}</Badge>
                        <h3 className="text-base font-semibold text-slate-900">{m.focus}</h3>
                      </div>
                      {m.estimated_hours != null && <span className="text-xs text-slate-500">~{m.estimated_hours} hours</span>}
                    </div>
                    {m.tasks?.length > 0 && <ul className="mt-3 space-y-1.5 text-sm text-slate-700">{m.tasks.map((t: string) => <li key={t}>• {t}</li>)}</ul>}
                    {m.resources?.length > 0 && (
                      <div className="mt-4 space-y-2 rounded-xl bg-slate-50 p-3.5">
                        <div className="text-xs font-medium text-slate-500">Recommended resources</div>
                        {m.resources.map((r: any, j: number) => (
                          <div key={j} className="text-sm"><span className="font-medium text-slate-800">{r.title}</span>{r.content && <span className="text-slate-500"> — {r.content}</span>}</div>
                        ))}
                      </div>
                    )}
                  </Card>
                </li>
              ))}
            </ol>
            {data.skills_deferred?.length > 0 && (
              <Card title="Deferred to a later phase" subtitle="Not enough time in this plan: increase weeks or hours per week to include them." className="mt-6">
                <Chips items={data.skills_deferred} tone="amber" />
              </Card>
            )}
          </>
        )}
    </>
  );
}
