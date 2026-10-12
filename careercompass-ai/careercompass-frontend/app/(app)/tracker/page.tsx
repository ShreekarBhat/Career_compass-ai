"use client";
import { FormEvent, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Card, Notice, PageHeader, Spinner, Stat, fmtDate, scoreTone, useApi } from "@/components/ui";

const STATUSES = ["saved", "applied", "assessment", "interview", "offer", "rejected", "withdrawn"] as const;
const TONE: Record<string, any> = { saved: "slate", applied: "blue", assessment: "amber", interview: "indigo", offer: "green", rejected: "red", withdrawn: "slate" };

export default function TrackerPage() {
  const apps = useApi<any[]>("/applications");
  const stats = useApi<any>("/applications/analytics");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ company: "", role: "", status: "applied", deadline: "", interview_at: "", notes: "" });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => { apps.reload(); stats.reload(); };

  async function add(e: FormEvent) {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      const body: any = { company: form.company, role: form.role, status: form.status, notes: form.notes || null };
      if (form.deadline) body.deadline = new Date(form.deadline).toISOString();
      if (form.interview_at) body.interview_at = new Date(form.interview_at).toISOString();
      await api("/applications", { body });
      setForm({ company: "", role: "", status: "applied", deadline: "", interview_at: "", notes: "" }); setOpen(false); refresh();
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  async function move(id: number, status: string) {
    try { await api(`/applications/${id}`, { method: "PATCH", body: { status } }); refresh(); } catch (e: any) { setErr(e.message); }
  }
  async function del(id: number) {
    if (!confirm("Delete this application?")) return;
    try { await api(`/applications/${id}`, { method: "DELETE" }); refresh(); } catch (e: any) { setErr(e.message); }
  }

  const list = apps.data ?? [];
  const s = stats.data;
  return (
    <>
      <PageHeader title="Application tracker" subtitle="Every application, from saved to offer." actions={<Button onClick={() => setOpen(!open)}><Plus size={16} /> Add application</Button>} />
      {err && <div className="mb-4"><Notice>{err}</Notice></div>}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Tracked" value={s?.total_tracked ?? 0} />
        <Stat label="Applied" value={s?.total_applied ?? 0} />
        <Stat label="Avg match" value={s?.average_match_score != null ? `${Math.round(s.average_match_score)}%` : "—"} />
        <Stat label="Interview rate" value={`${s?.interview_conversion_pct ?? 0}%`} />
      </div>
      {s?.insights?.length > 0 && <Card className="mt-4"><ul className="space-y-1 text-sm text-slate-700">{s.insights.map((i: string) => <li key={i}>💡 {i}</li>)}</ul></Card>}

      {open && (
        <Card title="New application" className="mt-6">
          <form onSubmit={add} className="grid gap-3 sm:grid-cols-2">
            <input className="field" required placeholder="Company" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
            <input className="field" required placeholder="Role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
            <select className="field" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>{STATUSES.map((x) => <option key={x}>{x}</option>)}</select>
            <input className="field" placeholder="Notes (optional)" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            <label className="text-xs text-slate-500">Deadline<input type="datetime-local" className="field mt-1" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} /></label>
            <label className="text-xs text-slate-500">Interview at<input type="datetime-local" className="field mt-1" value={form.interview_at} onChange={(e) => setForm({ ...form, interview_at: e.target.value })} /></label>
            <div className="sm:col-span-2"><Button type="submit" loading={busy}>Save application</Button></div>
          </form>
        </Card>
      )}

      {apps.loading ? <div className="grid place-items-center py-16"><Spinner /></div> : (
        <div className="mt-6 flex gap-4 overflow-x-auto pb-4">
          {STATUSES.filter((st) => st !== "withdrawn" || list.some((a) => a.status === "withdrawn")).map((st) => {
            const col = list.filter((a) => a.status === st);
            return (
              <div key={st} className="w-72 shrink-0 rounded-2xl bg-slate-100/70 p-3">
                <div className="mb-3 flex items-center justify-between px-1">
                  <Badge tone={TONE[st]} className="capitalize">{st}</Badge><span className="text-xs text-slate-500">{col.length}</span>
                </div>
                <div className="space-y-3">
                  {col.map((a) => (
                    <div key={a.id} className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-card">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0"><div className="break-words text-sm font-semibold text-slate-900">{a.role}</div><div className="break-words text-xs text-slate-500">{a.company}</div></div>
                        {a.match_score != null && <Badge tone={scoreTone(a.match_score)}>{a.match_score}%</Badge>}
                      </div>
                      {(a.deadline || a.interview_at) && (
                        <div className="mt-2 space-y-0.5 text-xs text-slate-500">
                          {a.deadline && <div>⏰ Deadline {fmtDate(a.deadline)}</div>}
                          {a.interview_at && <div>🎤 Interview {fmtDate(a.interview_at)}</div>}
                        </div>
                      )}
                      <div className="mt-3 flex items-center gap-2">
                        <select className="field !py-1.5 text-xs" value={a.status} onChange={(e) => move(a.id, e.target.value)}>{STATUSES.map((x) => <option key={x}>{x}</option>)}</select>
                        <button onClick={() => del(a.id)} aria-label="Delete" className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600"><Trash2 size={15} /></button>
                      </div>
                    </div>
                  ))}
                  {col.length === 0 && <div className="rounded-xl border border-dashed border-slate-300 p-4 text-center text-xs text-slate-400">Empty</div>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
