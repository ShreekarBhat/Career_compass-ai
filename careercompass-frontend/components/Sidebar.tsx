"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, Briefcase, ClipboardList, FileText, LayoutDashboard, LogOut, MessageSquare, Mic, Route, Target } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { cx } from "@/components/ui";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Career Agent", icon: MessageSquare },
  { href: "/resume", label: "Resume", icon: FileText },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/skills", label: "Skill gap", icon: Target },
  { href: "/roadmap", label: "Roadmap", icon: Route },
  { href: "/interview", label: "Interview", icon: Mic },
  { href: "/tracker", label: "Tracker", icon: ClipboardList },
  { href: "/notifications", label: "Notifications", icon: Bell },
];

export default function Sidebar() {
  const path = usePathname();
  const { user, logout } = useAuth();
  return (
    <>
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col bg-slate-900 px-4 py-6 md:flex">
        <div className="mb-8 px-2">
          <div className="text-lg font-semibold text-white">Career Compass <span className="text-indigo-400">AI</span></div>
          <div className="text-xs text-slate-400">Your agentic career copilot</div>
        </div>
        <nav className="flex-1 space-y-1">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href}
              className={cx("flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
                path.startsWith(href) ? "bg-indigo-600 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white")}>
              <Icon size={18} /> {label}
            </Link>
          ))}
        </nav>
        <div className="rounded-xl bg-slate-800 p-3">
          <div className="truncate text-sm font-medium text-white">{user.full_name || user.email}</div>
          <div className="truncate text-xs text-slate-400">{user.email}</div>
          <button onClick={logout} className="mt-2 flex items-center gap-1.5 text-xs text-slate-300 hover:text-white"><LogOut size={14} /> Sign out</button>
        </div>
      </aside>
      <nav className="sticky top-0 z-20 flex gap-1 overflow-x-auto border-b border-slate-200 bg-white px-3 py-2 md:hidden">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href}
            className={cx("flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium", path.startsWith(href) ? "bg-indigo-600 text-white" : "text-slate-600")}>
            <Icon size={14} /> {label}
          </Link>
        ))}
        <button onClick={logout} className="ml-auto shrink-0 px-2 text-xs text-slate-500">Sign out</button>
      </nav>
    </>
  );
}
