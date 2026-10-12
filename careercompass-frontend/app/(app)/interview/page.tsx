"use client";
import { useState } from "react";
import { Mic } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Bar, Button, Card, Chips, Notice, PageHeader, ScoreRing } from "@/components/ui";

const DIMS: [string, string][] = [
  ["technical_knowledge", "Technical knowledge"], ["communication", "Communication"],
  ["confidence", "Confidence"], ["answer_relevance", "Answer relevance"],
];

function Scores({ s }: { s: any }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {DIMS.map(([k, label]) => (
        <div key={k}>
          <div className="mb-1 flex justify-between text-xs"><span className="font-medium text-slate-700">{label}</span><span className="text-slate-500">{s[k]}%</span></div>
          <Bar value={s[k] ?? 0} />
        </div>
      ))}
    </div>
  );
}

export default function InterviewPage() {
  const [session, setSession] = useState<any>(null);
  const [q, setQ] = useState<any>(null);
  const [answer, setAnswer] = useState("");
  const [evalr, setEvalr] = useState<any>(null);
  const [next, setNext] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [n, setN] = useState(6);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function start() {
    setBusy(true); setErr(null); setSummary(null); setEvalr(null);
    try {
      const r = await api("/interview/start", { body: { n_questions: n } });
      setSession(r); setQ(r.first_question); setAnswer("");
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  async function submit() {
    setBusy(true); setErr(null);
    try {
      const r = await api(`/interview/${session.session_id}/answer`, { body: { answer } });
      setEvalr(r.evaluation); setNext(r.next_question);
      if (r.done) setSummary(await api(`/interview/${session.session_id}/finish`, { method: "POST" }));
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  function goNext() { setQ(next); setNext(null); setEvalr(null); setAnswer(""); }
  async function finishEarly() {
    setBusy(true);
    try { setSummary(await api(`/interview/${session.session_id}/finish`, { method: "POST" })); setEvalr(null); }
    catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <>
      <PageHeader title="Mock interview" subtitle="Technical, resume-based and behavioural rounds, scored on every answer." />
      {err && <div className="mb-4"><Notice>{err}</Notice></div>}

      {!session || summary ? (
        <>
          {summary && (
            <Card title="Interview summary" className="mb-6">
              <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
                <ScoreRing value={summary.overall} size={128} label="Overall" />
                <div className="flex-1 space-y-4">
                  <Scores s={summary} />
                  <div className="text-sm text-slate-500">Answered {summary.answered} of {summary.total_questions} questions.</div>
                </div>
              </div>
              {summary.by_round && (
                <div className="mt-5 flex flex-wrap gap-2">{Object.entries(summary.by_round).map(([r, v]) => <Badge key={r} tone="indigo">{r}: {v as number}%</Badge>)}</div>
              )}
              {summary.focus_areas?.length > 0 && <div className="mt-5"><div className="mb-2 text-xs font-medium text-slate-500">Questions to revisit</div><ul className="space-y-1 text-sm text-slate-700">{summary.focus_areas.map((f: string) => <li key={f}>• {f}</li>)}</ul></div>}
            </Card>
          )}
          <Card title={summary ? "Practise again" : "Start a session"} subtitle="Questions are personalised from your resume, target role and skill gaps.">
            <div className="flex flex-wrap items-center gap-4">
              <label className="text-sm text-slate-700">Questions: <b>{n}</b>
                <input type="range" min={3} max={12} value={n} onChange={(e) => setN(+e.target.value)} className="ml-3 align-middle" /></label>
              <Button onClick={start} loading={busy}><Mic size={16} /> Start interview</Button>
            </div>
          </Card>
        </>
      ) : (
        <div className="space-y-6">
          <Card>
            <div className="mb-3 flex items-center justify-between">
              <Badge tone="indigo">{q.round}</Badge>
              <span className="text-xs text-slate-500">Question {q.index + 1} of {q.total}</span>
            </div>
            <Bar value={((q.index + (evalr ? 1 : 0)) / q.total) * 100} tone="indigo" className="mb-5" />
            <h2 className="text-lg font-semibold text-slate-900">{q.question}</h2>
            <textarea className="field mt-4 min-h-[150px]" placeholder="Type your answer as you would say it in the interview…" value={answer}
              disabled={!!evalr} onChange={(e) => setAnswer(e.target.value)} />
            {!evalr && (
              <div className="mt-3 flex gap-2">
                <Button onClick={submit} loading={busy} disabled={!answer.trim()}>Submit answer</Button>
                <Button variant="ghost" onClick={finishEarly}>End interview</Button>
              </div>
            )}
          </Card>

          {evalr && (
            <Card title="Feedback" action={<Badge tone={evalr.overall >= 70 ? "green" : evalr.overall >= 50 ? "amber" : "red"}>Overall {evalr.overall}%</Badge>}>
              <Scores s={evalr} />
              {evalr.feedback && <p className="mt-4 text-sm text-slate-700">{evalr.feedback}</p>}
              {evalr.follow_up && <p className="mt-3 rounded-xl bg-indigo-50 p-3 text-sm text-indigo-900"><b>Follow-up:</b> {evalr.follow_up}</p>}
              {next && <Button className="mt-5" onClick={goNext}>Next question</Button>}
            </Card>
          )}
        </div>
      )}
    </>
  );
}
