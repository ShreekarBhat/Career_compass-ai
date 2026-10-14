export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const ACCESS_TOKEN_KEY = "cc_token";
const REFRESH_TOKEN_KEY = "cc_refresh_token";

export const getToken = (): string | null => (typeof window === "undefined" ? null : localStorage.getItem(ACCESS_TOKEN_KEY));
export const getRefreshToken = (): string | null => (typeof window === "undefined" ? null : localStorage.getItem(REFRESH_TOKEN_KEY));
export const setTokens = (accessToken: string, refreshToken: string) => {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
};
export const clearTokens = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

type Opts = { method?: string; body?: unknown; form?: FormData };

let refreshInFlight: Promise<boolean> | null = null;

function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const refreshToken = getRefreshToken();
      if (!refreshToken) return false;

      let res: Response;
      try {
        res = await fetch(`${API}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch {
        throw new ApiError(`Cannot reach the backend at ${API}. Is it running?`, 0);
      }
      if (res.status === 401) {
        clearTokens();
        return false;
      }

      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const detail = data?.detail;
        const message = typeof detail === "string" ? detail : `Token refresh failed (${res.status})`;
        throw new ApiError(message, res.status);
      }
      if (typeof data?.access_token !== "string" || typeof data?.refresh_token !== "string") {
        throw new ApiError("The backend returned an invalid token refresh response.", res.status);
      }

      setTokens(data.access_token, data.refresh_token);
      return true;
    })().finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

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
    const refreshed = await refreshSession();
    if (refreshed) {
      const retryHeaders = { ...headers, Authorization: `Bearer ${getToken()}` };
      try {
        res = await fetch(`${API}${path}`, {
          method: opts.method ?? (body ? "POST" : "GET"),
          headers: retryHeaders,
          body,
        });
      } catch {
        throw new ApiError(`Cannot reach the backend at ${API}. Is it running?`, 0);
      }
    }
    if (!refreshed || res.status === 401) {
      clearTokens();
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new ApiError("Session expired. Please sign in again.", 401);
    }
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
