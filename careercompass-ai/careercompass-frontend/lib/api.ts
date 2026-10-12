export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const KEY = "cc_token";

export const getToken = (): string | null => (typeof window === "undefined" ? null : localStorage.getItem(KEY));
export const setToken = (t: string) => localStorage.setItem(KEY, t);
export const clearToken = () => localStorage.removeItem(KEY);

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

type Opts = { method?: string; body?: unknown; form?: FormData };

export async function api<T = any>(path: string, opts: Opts = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(opts.body); }

  let res: Response;
  try {
    res = await fetch(`${API}${path}`, { method: opts.method ?? (body ? "POST" : "GET"), headers, body });
  } catch {
    throw new ApiError(`Cannot reach the backend at ${API}. Is it running?`, 0);
  }
  if (res.status === 401 && !path.startsWith("/auth/login") && !path.startsWith("/auth/register")) {
    clearToken();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new ApiError("Session expired. Please sign in again.", 401);
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const d = data?.detail;
    const msg = typeof d === "string" ? d : Array.isArray(d) ? d.map((x: any) => x.msg).join("; ") : `Request failed (${res.status})`;
    throw new ApiError(msg, res.status);
  }
  return data as T;
}
