"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, clearToken, getToken } from "@/lib/api";
import { Spinner } from "@/components/ui";

type User = { id: number; email: string; full_name: string; telegram_linked: boolean };
type Ctx = { user: User; refresh: () => Promise<void>; logout: () => void };
const AuthCtx = createContext<Ctx | null>(null);

export const useAuth = () => {
  const c = useContext(AuthCtx);
  if (!c) throw new Error("useAuth outside AuthGate");
  return c;
};

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  const refresh = useCallback(async () => { setUser(await api<User>("/auth/me")); }, []);
  const logout = useCallback(() => { clearToken(); router.replace("/login"); }, [router]);

  useEffect(() => {
    if (!getToken()) { router.replace("/login"); return; }
    refresh().catch(() => router.replace("/login"));
  }, [refresh, router]);

  if (!user) return <div className="grid min-h-screen place-items-center"><Spinner /></div>;
  return <AuthCtx.Provider value={{ user, refresh, logout }}>{children}</AuthCtx.Provider>;
}
