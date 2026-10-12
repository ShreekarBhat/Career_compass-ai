"use client";
import { ButtonHTMLAttributes, ReactNode, useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

export const cx = (...a: (string | false | null | undefined)[]) => a.filter(Boolean).join(" ");

export function Card({ title, subtitle, action, children, className }: {
  title?: string; subtitle?: string; action?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={cx("rounded-2xl border border-slate-200 bg-white p-5 shadow-card", className)}>
      {(title || action) && (
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-[15px] font-semibold text-slate-900">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Button({ variant = "primary", loading, className, children, disabled, ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger"; loading?: boolean }) {
  const styles = {
    primary: "bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm",
    secondary: "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50",
    ghost: "text-slate-600 hover:bg-slate-100",
    danger: "bg-white text-rose-600 border border-rose-200 hover:bg-rose-50",
  }[variant];
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={cx("inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60", styles, className)}
    >
      {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />}
      {children}
    </button>
  );
}

const tones = {
  slate: "bg-slate-100 text-slate-700", green: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100",
  amber: "bg-amber-50 text-amber-700 ring-1 ring-amber-100", red: "bg-rose-50 text-rose-700 ring-1 ring-rose-100",
  indigo: "bg-indigo-50 text-indigo-700 ring-1 ring-indigo-100", blue: "bg-sky-50 text-sky-700 ring-1 ring-sky-100",
};
export type Tone = keyof typeof tones;
export function Badge({ tone = "slate", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return <span className={cx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", tones[tone], className)}>{children}</span>;
}

export const scoreTone = (v: number): Tone => (v >= 75 ? "green" : v >= 50 ? "amber" : "red");
const barColor = { green: "bg-emerald-500", amber: "bg-amber-500", red: "bg-rose-500", indigo: "bg-indigo-500", slate: "bg-slate-400", blue: "bg-sky-500" };

export function Bar({ value, tone, className }: { value: number; tone?: Tone; className?: string }) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className={cx("h-2 w-full overflow-hidden rounded-full bg-slate-100", className)}>
      <div className={cx("h-full rounded-full transition-all", barColor[tone ?? scoreTone(v)])} style={{ width: `${v}%` }} />
    </div>
  );
}

export function ScoreRing({ value, size = 104, label }: { value: number; size?: number; label?: string }) {
  const r = 42, c = 2 * Math.PI * r, v = Math.max(0, Math.min(100, value));
  const color = v >= 75 ? "#10b981" : v >= 50 ? "#f59e0b" : "#f43f5e";
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" className="-rotate-90" width={size} height={size}>
        <circle cx="50" cy="50" r={r} fill="none" stroke="#e2e8f0" strokeWidth="9" />
        <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (c * v) / 100} />
      </svg>
      <div className="absolute text-center">
        <div className="text-2xl font-semibold leading-none text-slate-900">{Math.round(v)}</div>
        {label && <div className="mt-1 text-[10px] uppercase tracking-wide text-slate-500">{label}</div>}
      </div>
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
      <div className="text-xs font-medium text-slate-500">{label}</div>
      <div className="mt-1.5 text-2xl font-semibold text-slate-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <span className={cx("inline-block h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent", className)} />;
}

export function Notice({ kind = "error", children }: { kind?: "error" | "info" | "success"; children: ReactNode }) {
  const s = { error: "border-rose-200 bg-rose-50 text-rose-700", info: "border-sky-200 bg-sky-50 text-sky-800", success: "border-emerald-200 bg-emerald-50 text-emerald-800" }[kind];
  return <div className={cx("rounded-xl border px-3.5 py-2.5 text-sm", s)}>{children}</div>;
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-10 text-center">
      <div className="text-sm font-medium text-slate-700">{title}</div>
      {children && <div className="mt-1.5 text-sm text-slate-500">{children}</div>}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Chips({ items, tone = "slate", max }: { items?: string[]; tone?: Tone; max?: number }) {
  const list = (items ?? []).slice(0, max ?? 999);
  if (!list.length) return <span className="text-xs text-slate-400">None</span>;
  return <div className="flex flex-wrap gap-1.5">{list.map((s) => <Badge key={s} tone={tone}>{s}</Badge>)}</div>;
}

export function useApi<T = any>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!!path);
  const load = useCallback(async () => {
    if (!path) { setLoading(false); return; }
    setLoading(true); setError(null);
    try { setData(await api<T>(path)); } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  }, [path]);
  useEffect(() => { load(); }, [load]);
  return { data, error, loading, reload: load, setData };
}

export const fmtDate = (d?: string | null) => (d ? new Date(d).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "—");
