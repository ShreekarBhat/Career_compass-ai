# Career Compass AI — backend

Agentic career-intelligence backend: a LangGraph **orchestrator** routes user requests/events to specialised
**agents** (resume, job discovery, skill gap, planner, interview, tracker, knowledge/RAG, notification), which call
deterministic **tools** (ATS engine, matcher, skill-gap, roadmap builder) and an LLM (Groq) with RAG over pgvector.
Everything works without an LLM key (rule-based fallbacks).

## Run (Windows / VS Code)
```
copy .env.example .env            # set GROQ_API_KEY, TELEGRAM_BOT_TOKEN, JWT_SECRET
docker compose up -d db redis     # pgvector Postgres + Redis (creds: careercompass / careercompass)
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-ml.txt   # optional: real sentence-transformer embeddings
uvicorn app.main:app --reload        # http://localhost:8000/docs
```
If you already have a Postgres container on port 5432, point `DATABASE_URL` in `.env` at it (needs the pgvector extension).
Tables, vector indexes and seed data (skills, jobs, knowledge base) are created automatically on startup.
Authentication uses 15-minute access tokens and rotating refresh tokens with a 30-day sliding expiry. Clients should
store the refresh token securely and call `POST /auth/refresh` before the access token expires; each successful refresh
invalidates the presented refresh token. Send `{"refresh_token":"<current refresh token>"}` to refresh; save both
tokens returned by the endpoint. `POST /auth/logout` with the same request body revokes the submitted refresh token.

## Layout
```
app/main.py            FastAPI app, middleware, lifespan (init DB + seed)
app/api/               thin routers: auth, profile, resumes, jobs, skills, roadmap, interview, tracker, notifications, agent
app/agents/            orchestrator.py (LangGraph) + one file per agent, shared state.py
app/tools/             pure functions: ats, matcher, skill_gap, roadmap_builder, interview_scoring, job providers, telegram
app/rag/               ingest + retriever (pgvector)          app/ai/   LLM + embeddings clients
app/ml/                role classifier (+ training script)     app/profile/  resume parsing -> career profile
app/core/              config, JWT/bcrypt, rate limiting, prompt-injection sanitising
app/db/                SQLAlchemy models + session            app/scheduler.py  background job scans (SCHEDULER_ENABLED=true)
evaluation/            offline evaluation scripts             tests/    pytest suite (SQLite, no external services)
```

## Key endpoint: `POST /agent/chat`
The orchestrator classifies intent, plans which agents run (and re-plans when results are weak), runs them and returns
the response plus `steps` (the agents that ran). Event pipelines (resume uploaded, skills updated, scheduled scan) use the
same graph. `GET /agent/runs` and `GET /agent/metrics` expose run history, completion rate and latency.

## Tests & evaluation
```
python -m pytest -q
python -m evaluation.eval_intent             # tool/agent-selection accuracy
python -m evaluation.eval_skill_extraction   # skill extraction precision / recall / F1
python -m evaluation.eval_matching           # job-matching P/R/F1 + Top-K
```
The datasets in `evaluation/data/` are small starter sets: extend them with your own labelled resumes/jobs before
quoting numbers in your report.

## Supervised model training
Train the intent, multi-label skill extraction, and job-relevance models from the labeled JSON fixtures:
```
python -m app.ml.train_labeled_models
```
The command writes model artifacts and per-task metrics to `models/`. Job-relevance validation keeps all examples
from a profile together; intent uses a stratified holdout. The six skill-extraction snippets are too few for a
meaningful holdout, so that task reports dataset size and labels without claiming evaluation quality. These fixture-
trained artifacts are experimental and are not automatically enabled in application inference.

Prepare the role classifier's `data/role_training.csv` from a Kaggle `UpdatedResumeDataSet.csv` containing `Category`
and `Resume` (or `Resume_str`) columns. The converter extracts known skills and maps supported categories to the
nearest role taxonomy labels; unrelated/unsupported categories and resumes with fewer than two extracted skills
are reported and skipped. The skills column contains extracted skills, not full resume text. Training deduplicates
identical extracted skill profiles before its stratified holdout to prevent duplicate-profile leakage:
```
python -m scripts.prepare_role_dataset path\to\UpdatedResumeDataSet.csv
python -m app.ml.train_role_classifier
```
To add examples manually, use the `skills,role` columns and quote comma-separated skills, for example
`"Python, SQL, Pandas",Data Analyst`. Without labeled rows, role training stops with an actionable error instead of
silently training on synthetic labels. Use `python -m app.ml.train_role_classifier --synthetic` only for an explicit
synthetic-data experiment.
