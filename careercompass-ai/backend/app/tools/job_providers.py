"""Job sources. Only official/public APIs are used. Every provider fails soft (returns [])."""
import html
import logging
import re
from datetime import datetime

import httpx

from app.core.config import settings
from app.data.jobs_seed import SEED_JOBS

logger = logging.getLogger(__name__)
_TAG = re.compile(r"<[^>]+>")


def _clean_html(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", raw or ""))).strip()


def _parse_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def fetch_seed(query: str = "", limit: int = 50) -> list[dict]:
    return SEED_JOBS[:limit]


def fetch_remotive(query: str, limit: int = 30) -> list[dict]:
    """Remotive public API (remote jobs, no key needed)."""
    try:
        r = httpx.get("https://remotive.com/api/remote-jobs", params={"search": query, "limit": limit}, timeout=8.0)
        r.raise_for_status()
        out = []
        for j in r.json().get("jobs", [])[:limit]:
            out.append({"source": "remotive", "external_id": str(j.get("id")), "title": j.get("title", ""),
                        "company": j.get("company_name", ""), "location": j.get("candidate_required_location") or "Remote",
                        "remote": True, "description": _clean_html(j.get("description", ""))[:4000],
                        "url": j.get("url"), "posted_at": _parse_dt(j.get("publication_date"))})
        return out
    except Exception as exc:
        logger.warning("Remotive fetch failed: %s", exc)
        return []


def fetch_adzuna(query: str, location: str = "", limit: int = 30) -> list[dict]:
    """Adzuna API (needs ADZUNA_APP_ID / ADZUNA_APP_KEY)."""
    if not (settings.adzuna_app_id and settings.adzuna_app_key):
        return []
    try:
        url = f"https://api.adzuna.com/v1/api/jobs/{settings.adzuna_country}/search/1"
        params = {"app_id": settings.adzuna_app_id, "app_key": settings.adzuna_app_key, "what": query,
                  "results_per_page": limit, "content-type": "application/json"}
        if location:
            params["where"] = location
        r = httpx.get(url, params=params, timeout=8.0)
        r.raise_for_status()
        out = []
        for j in r.json().get("results", []):
            loc = (j.get("location") or {}).get("display_name", "")
            out.append({"source": "adzuna", "external_id": str(j.get("id")), "title": _clean_html(j.get("title", "")),
                        "company": (j.get("company") or {}).get("display_name", ""), "location": loc,
                        "remote": "remote" in (j.get("title", "") + loc).lower(),
                        "description": _clean_html(j.get("description", ""))[:4000], "url": j.get("redirect_url"),
                        "posted_at": _parse_dt(j.get("created"))})
        return out
    except Exception as exc:
        logger.warning("Adzuna fetch failed: %s", exc)
        return []


def fetch_external(query: str, location: str = "") -> list[dict]:
    jobs: list[dict] = []
    providers = settings.providers_list
    if "remotive" in providers:
        jobs += fetch_remotive(query)
    if "adzuna" in providers:
        jobs += fetch_adzuna(query, location)
    return jobs
