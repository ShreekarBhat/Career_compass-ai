"use client";
import { useEffect, useRef, useState } from "react";
import { Bell, Send } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Badge, Button, Card, Empty, Notice, PageHeader, Spinner, fmtDate, useApi } from "@/components/ui";

export default function NotificationsPage() {
  const { user, refresh } = useAuth();
  const list = useApi<any[]>("/notifications");
  const [waiting, setWaiting] = useState(false);
  const [link, setLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  async function connect() {
    setBusy(true); setErr(null); setInfo(null);
    try {
      const r = await api("/notifications/telegram/link", { method: "POST" });
      setLink(r.link); window.open(r.link, "_blank", "noopener"); setWaiting(true);
      let tries = 0;
      timer.current = setInterval(async () => {
        tries++;
        try {
          const s = await api("/notifications/telegram/status");
          if (s.linked) { clearInterval(timer.current!); setWaiting(false); setInfo("Telegram connected!"); await refresh(); list.reload(); }
          else if (tries > 100) { clearInterval(timer.current!); setWaiting(false); }
        } catch { /* keep polling */ }
      }, 3000);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  async function unlink() { try { await api("/notifications/telegram", { method: "DELETE" }); await refresh(); } catch (e: any) { setErr(e.message); } }
  async function test() { setBusy(true); try { await api("/notifications/test", { method: "POST" }); setInfo("Test notification sent."); list.reload(); } catch (e: any) { setErr(e.message); } finally { setBusy(false); } }
  async function read(id: number) { try { await api(`/notifications/${id}/read`, { method: "POST" }); list.reload(); } catch { /* ignore */ } }

  return (
    <>
      <PageHeader title="Notifications" subtitle="Job matches, skill alerts, deadlines and interview reminders." />
      {err && <div className="mb-4"><Notice>{err}</Notice></div>}
      {info && <div className="mb-4"><Notice kind="success">{info}</Notice></div>}

      <Card title="Telegram alerts" subtitle="Get notifications on your phone. No chat id needed." className="mb-6">
        {user.telegram_linked ? (
          <div className="flex flex-wrap items-center gap-3">
            <Badge tone="green">Connected</Badge>
            <Button variant="secondary" onClick={test} loading={busy}><Send size={15} /> Send test</Button>
            <Button variant="ghost" onClick={unlink}>Disconnect</Button>
          </div>
        ) : waiting ? (
          <div className="space-y-2 text-sm text-slate-600">
            <div className="flex items-center gap-2"><Spinner className="h-4 w-4" /> Waiting for you to press <b>Start</b> in Telegram…</div>
            {link && <a href={link} target="_blank" rel="noreferrer" className="font-medium text-indigo-600 underline">Open the Telegram link again</a>}
          </div>
        ) : <Button onClick={connect} loading={busy}>Connect Telegram</Button>}
      </Card>

      {list.loading ? <div className="grid place-items-center py-12"><Spinner /></div>
        : !list.data?.length ? <Empty title="Nothing yet">Upload a resume and set a goal to start receiving alerts.</Empty>
        : (
          <div className="space-y-3">
            {list.data.map((n) => (
              <div key={n.id} className={`flex items-start gap-3 rounded-2xl border p-4 ${n.is_read ? "border-slate-200 bg-white" : "border-indigo-200 bg-indigo-50/50"}`}>
                <Bell size={18} className="mt-0.5 shrink-0 text-indigo-500" />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-semibold text-slate-900">{n.title}</span>{n.channel === "telegram" && <Badge tone="blue">Telegram</Badge>}</div>
                  <p className="mt-0.5 whitespace-pre-wrap text-sm text-slate-600">{n.body}</p>
                  <p className="mt-1 text-xs text-slate-400">{fmtDate(n.created_at)}</p>
                </div>
                {!n.is_read && <button onClick={() => read(n.id)} className="text-xs font-medium text-indigo-600 hover:underline">Mark read</button>}
              </div>
            ))}
          </div>
        )}
    </>
  );
}
