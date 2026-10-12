"""Generate a SYNTHETIC starter dataset of labelled profile/job pairs -> evaluation/data/matching_pairs.json.
Labels come from hand-declared role families (not from the matcher), but the data is still synthetic:
use it to test the evaluation pipeline, then replace it with ~100+ manually labelled real pairs for your report.
Run: python -m evaluation.build_matching_dataset"""
import json
import random
from pathlib import Path

FAMILIES = {
    "ml":      ["Python", "Machine Learning", "Scikit-learn", "Pandas", "NumPy", "Deep Learning", "PyTorch", "Statistics"],
    "genai":   ["Python", "LLMs", "RAG", "LangChain", "Vector Databases", "FastAPI", "Prompt Engineering", "Hugging Face"],
    "analyst": ["SQL", "Excel", "Tableau", "Power BI", "Statistics", "Python", "Pandas", "Data Visualization"],
    "backend": ["Python", "REST APIs", "PostgreSQL", "Docker", "FastAPI", "Git", "Redis", "System Design"],
    "web":     ["JavaScript", "React", "HTML/CSS", "TypeScript", "Node.js", "Git", "Next.js", "Tailwind CSS"],
    "devops":  ["Docker", "Kubernetes", "Linux", "CI/CD", "AWS", "Terraform", "Git", "Python"],
}
ADJACENT = {("ml", "genai"), ("ml", "analyst"), ("genai", "backend"), ("backend", "devops"), ("backend", "web")}
related = lambda a, b: a == b or (a, b) in ADJACENT or (b, a) in ADJACENT  # noqa: E731

rng = random.Random(11)
others = sorted({s for v in FAMILIES.values() for s in v})
data = []
for fam, skills in FAMILIES.items():
    for i in range(4):  # 4 profiles per family
        ps = rng.sample(skills, rng.randint(4, 6)) + rng.sample(others, rng.randint(0, 2))
        jobs = []
        for jf, jskills in FAMILIES.items():
            for k in range(3):  # 3 jobs per family
                js = rng.sample(jskills, rng.randint(4, 6))
                jobs.append({"id": f"{jf}_{k}", "skills": js, "relevant": related(fam, jf)})
        data.append({"profile": f"{fam}_{i}", "profile_skills": list(dict.fromkeys(ps)), "jobs": jobs})
out = Path(__file__).parent / "data" / "matching_pairs.json"
out.write_text(json.dumps(data, indent=1), encoding="utf-8")
print(f"{len(data)} profiles x {len(data[0]['jobs'])} jobs = {len(data) * len(data[0]['jobs'])} pairs -> {out}")
