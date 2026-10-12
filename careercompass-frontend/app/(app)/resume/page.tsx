"use client";
import { DragEvent, useEffect, useRef, useState } from "react";
import { Sparkles, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Bar, Button, Card, Chips, Empty, Notice, PageHeader, ScoreRing, Spinner, fmtDate, useApi } from "@/components/ui";

const LABELS: Record<string, string> = {
  sections: "Sections", contact: "Contact info", keywords: "Keywords", quantified_achievements: "Quantified impact",
  action_verbs: "Action verbs", length: "Length", semantic_fit: "Role similarity",
};
const SEV: Record<string, "red" | "amber" | "blue"> = { high: "red", medium: "amber", low: "blue" };

function Analysis({ a, title }: { a: any; title?: string }) {
  if (!a) return null;
  const an = a.analysis ?? a;
  const rows = Object.entries(an.breakdown ?? {}).filter(([, v]: any) => v.max > 0);
  return (
    <div className="space-y-6">
      <Card title={title ?? "ATS analysis"} subtitle={an.target ? `Scored against: ${an.target}` : "General scoring (no target role set)"}>
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
          <ScoreRing value={an.ats_score} size={128} label="/ 100" />
          <div className="flex-1 space-y-3">
            {rows.map(([k, v]: any) => (
              <div key={k}>
                <div className="mb-1 flex justify-between text-xs"><span className="font-medium text-slate-700">{LABELS[k] ?? k}</span><span className="text-slate-500">{Math.round(v.score)} / {v.max}</span></div>
                <Bar value={(v.score / v.max) * 100} />
              </div>
            ))}
          </div>
        </div>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card title="Problems to fix">
          {an.problems?.length ? (
            <ul className="space-y-3">
              {an.problems.map((p: any, i: number) => (
                <li key={i} className="text-sm">
                  <div className="flex items-center gap-2"><Badge tone={SEV[p.severity] ?? "slate"}>{p.severity}</Badge><span className="font-medium text-slate-800">{p.issue}</span></div>
                  <p className="mt-1 text-slate-500">{p.fix}</p>
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-slate-500">No problems detected.</p>}
        </Card>
        <Card title="What's working">
          {an.strengths?.length ? <ul className="space-y-2 text-sm text-slate-700">{an.strengths.map((s: string) => <li key={s}>✓ {s}</li>)}</ul> : <p className="text-sm text-slate-500">—</p>}
          <div className="mt-5">
            <div className="mb-2 text-xs font-medium text-slate-500">Missing keywords for this target</div>
            <Chips items={an.missing_keywords} tone="red" max={14} />
          </div>
          <div className="mt-4">
            <div className="mb-2 text-xs font-medium text-slate-500">Skills detected</div>
            <Chips items={an.detected_skills} tone="indigo" />
          </div>
        </Card>
      </div>

      {a.ai_suggestions?.length > 0 && (
        <Card title="AI rewrite suggestions" subtitle="Replace [X%] placeholders with your real numbers; never invent results.">
          <div className="space-y-4">
            {a.ai_suggestions.map((r: any, i: number) => (
              <div key={i} className="rounded-xl bg-slate-50 p-3.5 text-sm">
                <div className="text-slate-500 line-through decoration-slate-300">{r.original}</div>
                <div className="mt-1.5 font-medium text-slate-900">{r.improved}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {a.targeted_plan && (
        <Card title={`Tailoring plan${a.job_title ? ` for ${a.job_title}` : ""}`}>
          <ul className="space-y-1.5 text-sm text-slate-700">{a.targeted_plan.action_steps?.map((s: string) => <li key={s}>• {s}</li>)}</ul>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div><div className="mb-2 text-xs font-medium text-slate-500">Add if you genuinely have them</div><Chips items={a.targeted_plan.keywords_to_add_if_true} tone="amber" /></div>
            <div><div className="mb-2 text-xs font-medium text-slate-500">Worth learning</div><Chips items={a.targeted_plan.consider_learning} tone="blue" /></div>
          </div>
        </Card>
      )}
    </div>
  );
}

export default function ResumePage() {
  const resumes = useApi<any[]>("/resumes");
  const fileRef = useRef<HTMLInputElement>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [tailored, setTailored] = useState<any>(null);
  const [jd, setJd] = useState("");
  const [busy, setBusy] = useState<"upload" | "analyze" | "tailor" | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const [loadedOnce, setLoadedOnce] = useState(false);

  useEffect(() => {
    if (loadedOnce || resumes.loading || !resumes.data?.length) return;
    setLoadedOnce(true);
    setBusy("analyze");
    api("/resumes/analyze", { method: "POST" }).then(setAnalysis).catch((e) => setErr(e.message)).finally(() => setBusy(null));
  }, [resumes.loading, resumes.data, loadedOnce]);

  async function upload(file?: File) {
    if (!file) return;
    setBusy("upload"); setErr(null); setTailored(null);
    try {
      const form = new FormData(); form.append("file", file);
      const r = await api("/resumes", { form });
      setAnalysis(r.results?.resume ?? null);
      resumes.reload();
    } catch (e: any) { setErr(e.message); } finally { setBusy(null); }
  }
  const onDrop = (e: DragEvent) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files?.[0]); };

  async function tailor() {
    setBusy("tailor"); setErr(null);
    try { setTailored(await api("/resumes/tailor", { body: { job_description: jd } })); }
    catch (e: any) { setErr(e.message); } finally { setBusy(null); }
  }

  const active = resumes.data?.[0];
  return (
    <>
      <PageHeader title="Resume intelligence" subtitle="Upload your resume to get an ATS score, fixes, and targeted advice." />
      {err && <div className="mb-4"><Notice>{err}</Notice></div>}

      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={onDrop}
        className={`rounded-2xl border-2 border-dashed p-8 text-center transition ${drag ? "border-indigo-400 bg-indigo-50" : "border-slate-300 bg-white"}`}>
        <Upload className="mx-auto text-slate-400" />
        <p className="mt-2 text-sm text-slate-600">Drag a PDF or DOCX here, or</p>
        <input ref={fileRef} type="file" accept=".pdf,.docx" hidden onChange={(e) => upload(e.target.files?.[0])} />
        <Button className="mt-3" onClick={() => fileRef.current?.click()} loading={busy === "upload"}>Choose file</Button>
        {active && <p className="mt-3 text-xs text-slate-500">Current: {active.filename} · uploaded {fmtDate(active.created_at)}</p>}
        <p className="mt-1 text-xs text-slate-400">Max 5 MB. Uploading re-runs skill gap, job matching and your roadmap.</p>
      </div>

      <div className="mt-6">
        {busy === "analyze" || busy === "upload" ? <div className="grid place-items-center py-16"><Spinner /></div>
          : analysis ? <Analysis a={analysis} />
          : !resumes.loading && <Empty title="No resume analysed yet">Upload one above to see your score.</Empty>}
      </div>

      {(active || analysis) && (
        <Card title="Tailor for a specific job" subtitle="Paste a job description to get keyword gaps and an action plan." className="mt-6">
          <textarea className="field min-h-[140px]" placeholder="Paste the job description here…" value={jd} onChange={(e) => setJd(e.target.value)} />
          <Button className="mt-3" onClick={tailor} loading={busy === "tailor"} disabled={jd.trim().length < 40}><Sparkles size={16} /> Analyse fit</Button>
          {tailored && <div className="mt-6"><Analysis a={tailored} title="ATS score for this job" /></div>}
        </Card>
      )}
    </>
  );
}
