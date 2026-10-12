"use client";
import { useEffect, useState } from "react";
import { Bookmark, ExternalLink, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Card, Chips, Empty, Notice, PageHeader, Spinner, scoreTone } from "@/components/ui";

export default function JobsPage() {
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState<Record<number, boolean>>({});
  const [minScore, setMinScore] = useState(0);

  async function load(refresh: boolean, min = minScore) {
    refresh ? setRefreshing(true) : setBusy(true);
    setErr(null);
    try { setData(await api("/jobs/discover", { body: { refresh, limit: 15, min_score: min } })); }
    catch (e: any) { setErr(e.message); } finally { setBusy(false); setRefreshing(false); }
  }
  useEffect(() => { load(false); /* eslint-disable-next-line */ }, []);

  async function save(id: number) {
    try { await api(`/jobs/${id}/save`, { method: "POST" }); setSaved((s) => ({ ...s, [id]: true })); }
    catch (e: any) { setErr(e.message); }
  }

  return (
    <>
      <PageHeader title="Job matches" subtitle={data?.role ? `Ranked for ${data.role}` : "Ranked against your profile"}
        actions={<Button variant="secondary" onClick={() => load(true)} loading={refreshing}><RefreshCw size={16} /> Fetch new jobs</Button>} />
      <div className="mb-5 flex items-center gap-3 text-sm text-slate-600">
        <label htmlFor="min">Minimum match</label>
        <input id="min" type="range" min={0} max={90} step={10} value={minScore}
          onChange={(e) => setMinScore(+e.target.value)} onMouseUp={() => load(false)} onTouchEnd={() => load(false)} onKeyUp={() => load(false)} />
        <span className="w-10 font-medium">{minScore}%</span>
      </div>
      {err && <div className="mb-4"><Notice>{err}</Notice></div>}
      {busy ? <div className="grid place-items-center py-20"><Spinner /></div>
        : !data?.jobs?.length ? <Empty title="No matches yet">Upload a resume and set a target role, then fetch new jobs.</Empty>
        : (
          <div className="space-y-4">
            {data.jobs.map((j: any) => (
              <Card key={j.job_id}>
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-base font-semibold text-slate-900">{j.title}</h3>
                      {j.remote && <Badge tone="blue">Remote</Badge>}
                      {j.level && <Badge>{j.level}</Badge>}
                    </div>
                    <p className="mt-0.5 text-sm text-slate-500">{j.company} · {j.location || "Location n/a"} · <span className="text-slate-400">{j.source}</span></p>
                    {j.explanation && <p className="mt-3 text-sm text-slate-700">{j.explanation}</p>}
                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <div><div className="mb-1.5 text-xs font-medium text-slate-500">You have</div><Chips items={j.matched_skills} tone="green" /></div>
                      <div><div className="mb-1.5 text-xs font-medium text-slate-500">Missing</div><Chips items={j.missing_skills} tone="red" /></div>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-4 sm:flex-col sm:items-end">
                    <div className="text-right">
                      <div className={`text-3xl font-semibold ${{ green: "text-emerald-600", amber: "text-amber-600", red: "text-rose-600" }[scoreTone(j.match) as "green" | "amber" | "red"]}`}>{j.match}%</div>
                      <div className="text-xs text-slate-400">match</div>
                    </div>
                    <div className="flex gap-2">
                      <Button variant={saved[j.job_id] ? "secondary" : "primary"} disabled={saved[j.job_id]} onClick={() => save(j.job_id)}><Bookmark size={15} /> {saved[j.job_id] ? "Saved" : "Save"}</Button>
                      {j.url && <a href={j.url} target="_blank" rel="noreferrer"><Button variant="secondary" type="button"><ExternalLink size={15} /></Button></a>}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
    </>
  );
}
