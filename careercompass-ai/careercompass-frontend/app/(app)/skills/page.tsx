"use client";
import { FormEvent, useState } from "react";
import { X } from "lucide-react";
import { api } from "@/lib/api";
import RolePicker from "@/components/RolePicker";
import { Badge, Bar, Button, Card, Empty, Notice, PageHeader, Spinner, Stat, useApi } from "@/components/ui";

export default function SkillsPage() {
  const profile = useApi<any>("/profile");
  const role: string | null | undefined = profile.data?.target_role;
  const gap = useApi<any>(role ? "/skills/gap" : null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function declare(e: FormEvent) {
    e.preventDefault();
    const skills = text.split(",").map((s) => s.trim()).filter(Boolean);
    if (!skills.length) return;
    setBusy(true); setErr(null); setOk(null);
    try {
      const r = await api("/profile/skills", { body: { skills } });
      setOk(r.pipeline?.response ?? "Skills added. Your roadmap and matches were updated.");
      setText(""); profile.reload(); gap.reload();
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  async function remove(name: string) {
    try { await api(`/profile/skills/${encodeURIComponent(name)}`, { method: "DELETE" }); profile.reload(); gap.reload(); }
    catch (e: any) { setErr(e.message); }
  }

  if (profile.loading) return <div className="grid place-items-center py-24"><Spinner /></div>;
  const g = gap.data;

  return (
    <>
      <PageHeader title="Skill gap" subtitle="Your current capabilities against what your target role asks for." />
      <Card title="Target role" className="mb-6"><RolePicker value={role} onChanged={() => profile.reload()} /></Card>
      {err && <div className="mb-4"><Notice>{err}</Notice></div>}

      {!role ? <Empty title="No target role yet">Pick one above to see your gaps.</Empty>
        : gap.loading ? <div className="grid place-items-center py-16"><Spinner /></div>
        : g && (
          <>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <Stat label="Overall match" value={`${g.overall_match_pct}%`} />
              <Stat label="Strong skills" value={g.strong?.length ?? 0} />
              <Stat label="Gaps" value={g.missing?.length ?? 0} />
              <Stat label="Listings analysed" value={g.reference?.jobs_analyzed ?? 0} />
            </div>
            <div className="mt-6 grid gap-6 lg:grid-cols-3">
              <Card title="Proficiency vs requirements" subtitle="Sorted by priority. Priority = importance × gap × market demand." className="lg:col-span-2">
                <div className="space-y-4">
                  {[...(g.bars ?? [])].sort((a: any, b: any) => b.priority - a.priority).map((b: any) => (
                    <div key={b.skill}>
                      <div className="mb-1 flex items-center justify-between gap-2 text-sm">
                        <span className="font-medium text-slate-800">{b.skill}</span>
                        <span className="flex items-center gap-2 text-xs text-slate-500">
                          {b.market_frequency_pct > 0 && <Badge tone="blue">{b.market_frequency_pct}% of jobs</Badge>}
                          {b.proficiency}%
                        </span>
                      </div>
                      <Bar value={b.proficiency} />
                    </div>
                  ))}
                </div>
              </Card>
              <div className="space-y-6">
                <Card title="Insights">
                  {g.insights?.length ? <ul className="space-y-2 text-sm text-slate-600">{g.insights.map((i: string) => <li key={i}>• {i}</li>)}</ul> : <p className="text-sm text-slate-500">—</p>}
                </Card>
                <Card title="I already know…" subtitle="Tell the agent and your roadmap adapts.">
                  <form onSubmit={declare} className="space-y-2.5">
                    <input className="field" placeholder="e.g. PyTorch, Docker" value={text} onChange={(e) => setText(e.target.value)} />
                    <Button type="submit" loading={busy} className="w-full" disabled={!text.trim()}>Update my profile</Button>
                  </form>
                  {ok && <div className="mt-3"><Notice kind="success">{ok}</Notice></div>}
                  {profile.data?.declared_skills?.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-1.5">
                      {profile.data.declared_skills.map((s: string) => (
                        <span key={s} className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700">
                          {s}<button onClick={() => remove(s)} aria-label={`Remove ${s}`}><X size={12} /></button>
                        </span>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            </div>
          </>
        )}
    </>
  );
}
