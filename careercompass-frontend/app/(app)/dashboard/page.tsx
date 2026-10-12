"use client";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Circle } from "lucide-react";
import { useAuth } from "@/lib/auth";
import RolePicker from "@/components/RolePicker";
import { Bar, Badge, Card, Chips, PageHeader, ScoreRing, Spinner, Stat, scoreTone, useApi } from "@/components/ui";

export default function Dashboard() {
  const { user } = useAuth();
  const profile = useApi<any>("/profile");
  const resumes = useApi<any[]>("/resumes");
  const analytics = useApi<any>("/applications/analytics");
  const role: string | null | undefined = profile.data?.target_role;
  const gap = useApi<any>(role ? "/skills/gap" : null);

  if (profile.loading || resumes.loading) return <div className="grid place-items-center py-24"><Spinner /></div>;

  const latest = resumes.data?.[0];
  const hasResume = !!latest;
  const topMissing = (gap.data?.missing ?? []).slice(0, 6);

  const steps = [
    { done: hasResume, label: "Upload your resume", href: "/resume" },
    { done: !!role, label: "Pick a target role", href: "/skills" },
    { done: (analytics.data?.total_tracked ?? 0) > 0, label: "Find and save jobs", href: "/jobs" },
    { done: false, label: "Practise a mock interview", href: "/interview" },
  ];

  return (
    <>
      <PageHeader title={`Hi ${user.full_name?.split(" ")[0] || "there"} 👋`} subtitle="Here is where your career search stands today." />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Target role" value={<span className="text-lg">{role ?? "Not set"}</span>} hint={profile.data?.experience_level ? `Level: ${profile.data.experience_level}` : undefined} />
        <Stat label="Latest ATS score" value={hasResume ? `${latest.ats_score ?? "—"}/100` : "—"} hint={hasResume ? latest.filename : "No resume yet"} />
        <Stat label="Role match" value={gap.data ? `${gap.data.overall_match_pct}%` : "—"} hint={role ? "Based on skills + evidence" : "Set a goal first"} />
        <Stat label="Applications" value={analytics.data?.total_applied ?? 0} hint={`${analytics.data?.interview_conversion_pct ?? 0}% reach interview`} />
      </div>

      {!role && (
        <Card title="Choose your career goal" subtitle="Your skill gap, job matches and roadmap are built around it." className="mt-6">
          <RolePicker value={role} onChanged={() => { profile.reload(); }} />
        </Card>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card title="Priority skill gaps" subtitle={role ? `For ${role}` : undefined} className="lg:col-span-2"
          action={<Link href="/skills" className="flex items-center gap-1 text-xs font-medium text-indigo-600">Full analysis <ArrowRight size={14} /></Link>}>
          {gap.loading ? <Spinner /> : !role ? <p className="text-sm text-slate-500">Set a target role to see your gaps.</p> : topMissing.length === 0 ? (
            <p className="text-sm text-slate-500">No major gaps found. Nice work.</p>
          ) : (
            <div className="space-y-3.5">
              {topMissing.map((m: any) => (
                <div key={m.skill}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-800">{m.skill}</span>
                    <span className="text-xs text-slate-500">{m.market_frequency_pct}% of similar jobs</span>
                  </div>
                  <Bar value={m.proficiency} />
                </div>
              ))}
            </div>
          )}
          {gap.data?.insights?.length > 0 && (
            <ul className="mt-5 space-y-1.5 border-t border-slate-100 pt-4 text-sm text-slate-600">
              {gap.data.insights.slice(0, 3).map((i: string) => <li key={i}>• {i}</li>)}
            </ul>
          )}
        </Card>

        <div className="space-y-6">
          <Card title="Resume health">
            {hasResume ? (
              <div className="flex items-center gap-4">
                <ScoreRing value={latest.ats_score ?? 0} label="ATS" />
                <div className="text-sm text-slate-600">
                  <Badge tone={scoreTone(latest.ats_score ?? 0)}>{(latest.ats_score ?? 0) >= 75 ? "Strong" : (latest.ats_score ?? 0) >= 50 ? "Needs work" : "Weak"}</Badge>
                  <Link href="/resume" className="mt-2 block text-xs font-medium text-indigo-600">See fixes →</Link>
                </div>
              </div>
            ) : <Link href="/resume" className="text-sm font-medium text-indigo-600">Upload a resume →</Link>}
          </Card>
          <Card title="Getting started">
            <ul className="space-y-2.5">
              {steps.map((s) => (
                <li key={s.label}>
                  <Link href={s.href} className="flex items-center gap-2.5 text-sm text-slate-700 hover:text-indigo-600">
                    {s.done ? <CheckCircle2 size={18} className="text-emerald-500" /> : <Circle size={18} className="text-slate-300" />}
                    <span className={s.done ? "text-slate-400 line-through" : ""}>{s.label}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>

      {gap.data?.strong?.length > 0 && (
        <Card title="Your strengths for this role" className="mt-6"><Chips items={gap.data.strong.map((s: any) => s.skill)} tone="green" /></Card>
      )}
    </>
  );
}
