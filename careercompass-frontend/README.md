# Career Compass AI — frontend

Next.js 14 (App Router) + TypeScript + Tailwind CSS client for the Career Compass backend.

## Run
```
copy .env.local.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                             # http://localhost:3000
```
Start the backend first (`uvicorn app.main:app --reload`). The backend's `CORS_ORIGINS` must include the
frontend origin (default `http://localhost:3000`).

## Pages
| Route | Backend endpoints used |
|---|---|
| `/login` | `POST /auth/login-json`, `POST /auth/register` |
| `/dashboard` | `/profile`, `/resumes`, `/skills/gap`, `/applications/analytics` |
| `/chat` | `POST /agent/chat` (shows which agents ran) |
| `/resume` | `POST /resumes` (upload), `POST /resumes/analyze`, `POST /resumes/tailor` |
| `/jobs` | `POST /jobs/discover`, `POST /jobs/{id}/save` |
| `/skills` | `GET /skills/gap`, `GET /roles`, `PUT /profile`, `POST/DELETE /profile/skills` |
| `/roadmap` | `GET /roadmap`, `POST /roadmap/generate`, `POST /roadmap/adjust` |
| `/interview` | `POST /interview/start`, `/{id}/answer`, `/{id}/finish` |
| `/tracker` | `/applications` (CRUD), `/applications/analytics` |
| `/notifications` | `/notifications`, one-click Telegram: `POST /notifications/telegram/link` + `GET /notifications/telegram/status` |

## Structure
```
app/login            sign in / register
app/(app)/*          authenticated pages (layout = auth gate + sidebar)
components/ui.tsx    Card, Button, Badge, Bar, ScoreRing, useApi ...
lib/api.ts           fetch wrapper (JWT header, error handling, 401 -> /login)
lib/auth.tsx         AuthGate + useAuth()
```
Access and rotating refresh tokens are kept in `localStorage` so sessions survive page reloads and access-token
expiry. This is suitable for a student project; use httpOnly cookies for production.
