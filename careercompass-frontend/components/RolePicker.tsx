"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button, Notice, useApi } from "@/components/ui";

export default function RolePicker({ value, onChanged }: { value?: string | null; onChanged: () => void }) {
  const roles = useApi<any[]>("/roles");
  const [sel, setSel] = useState(value ?? "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    if (!sel) return;
    setBusy(true); setErr(null);
    try {
      await api("/profile", { method: "PUT", body: { target_role: sel } });
      // re-score the resume against the new role so the ATS score is consistent everywhere (ignored if no resume yet)
      await api("/resumes/analyze", { method: "POST" }).catch(() => null);
      onChanged();
    }
    catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-col gap-2 sm:flex-row">
        <select className="field sm:max-w-xs" value={sel} onChange={(e) => setSel(e.target.value)}>
          <option value="">Choose a target role…</option>
          {(roles.data ?? []).map((r) => <option key={r.role} value={r.role}>{r.role}</option>)}
        </select>
        <Button onClick={save} loading={busy} disabled={!sel || sel === value}>Set as my goal</Button>
      </div>
      <p className="text-xs text-slate-500">Setting a goal re-runs skill gap, job matching and your roadmap (a few seconds).</p>
      {err && <Notice>{err}</Notice>}
    </div>
  );
}
