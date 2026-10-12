"""Resume text -> structured profile (sections, skills, education, projects, experience)."""
import re

from app.tools.skill_extractor import extract_skills

_HEADINGS = {
    "education": r"education|academics?|academic (background|qualifications?)|qualifications?",
    "experience": r"(work |professional |relevant )?experience|employment( history)?|internships?|work history",
    "projects": r"(academic |personal |key |major )?projects?",
    "skills": r"(technical |key |core )?skills|technologies|tech stack|competencies",
    "summary": r"summary|objective|profile|about me|career objective|professional summary",
    "certifications": r"certifications?|courses?|licenses?",
    "achievements": r"achievements?|awards?|honou?rs|accomplishments",
}
_HEAD_RE = {k: re.compile(rf"^\s*(?:{v})\s*[:\-]?\s*$", re.IGNORECASE) for k, v in _HEADINGS.items()}
_BULLET = re.compile(r"^\s*[-•*▪●◦·➢►]\s*")
_DEGREE = re.compile(r"\b(b\.?\s?tech|b\.?\s?e\.?|m\.?\s?tech|bachelor|master|b\.?sc|m\.?sc|bca|mca|ph\.?d|diploma|"
                     r"b\.?\s?com|mba|12th|hsc|ssc)\b", re.IGNORECASE)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s-]?)\d{3,5}[\s-]?\d{3,5}")
_YEARS = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b", re.IGNORECASE)


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.splitlines():
        stripped = line.strip()
        matched = None
        if stripped and len(stripped) <= 45:
            for name, rx in _HEAD_RE.items():
                if rx.match(stripped.rstrip(":")):
                    matched = name
                    break
        if matched:
            current = matched
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def _blocks(section_text: str, limit: int = 8) -> list[dict]:
    items: list[dict] = []
    for block in re.split(r"\n\s*\n", section_text):
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        title = _BULLET.sub("", lines[0])[:120]
        desc = " ".join(_BULLET.sub("", l) for l in lines[1:])[:600]
        items.append({"title": title, "description": desc})
    # a section made only of bullets without blank lines -> treat each bullet as an item
    if len(items) == 1 and len(section_text.splitlines()) > 2:
        lines = [l for l in section_text.splitlines() if l.strip()]
        if all(_BULLET.match(l) for l in lines):
            items = [{"title": _BULLET.sub("", l)[:120], "description": ""} for l in lines]
    return items[:limit]


def infer_level(years: float | None, text: str) -> str:
    low = text.lower()
    if years is None or years == 0:
        return "fresher" if ("intern" in low or "student" in low or "b.tech" in low or years is None) else "fresher"
    if years < 2:
        return "junior"
    if years < 5:
        return "mid"
    return "senior"


def parse_resume(text: str) -> dict:
    sections = split_sections(text)
    skills = extract_skills(text)
    education: list[str] = []
    if "education" in sections:
        for l in sections["education"].splitlines():
            l = _BULLET.sub("", l.strip())
            if l and (_DEGREE.search(l) or len(education) < 3):
                education.append(l[:160])
        education = education[:4]
    else:
        education = [l.strip()[:160] for l in text.splitlines() if _DEGREE.search(l)][:3]

    projects = _blocks(sections["projects"]) if "projects" in sections else []
    experience = _blocks(sections["experience"]) if "experience" in sections else []

    years = None
    ys = [float(m.group(1)) for m in _YEARS.finditer(text) if float(m.group(1)) < 40]
    if ys:
        years = max(ys)
    summary = sections.get("summary", "")[:400]
    return {
        "sections": list(sections),
        "skills": skills,
        "education": education,
        "projects": projects,
        "experience": experience,
        "summary": summary,
        "years_experience": years,
        "experience_level": infer_level(years, text),
        "contact": {
            "email": bool(_EMAIL.search(text)),
            "phone": bool(_PHONE.search(text)),
            "linkedin": "linkedin.com" in text.lower(),
            "github": "github.com" in text.lower(),
        },
    }
