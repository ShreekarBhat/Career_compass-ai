"""Convert Kaggle's UpdatedResumeDataSet.csv into labeled role/skills rows.

Run from the project root:
    python -m scripts.prepare_role_dataset path\\to\\UpdatedResumeDataSet.csv
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

from app.tools.skill_extractor import extract_skills

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "role_training.csv"

CATEGORY_TO_ROLE = {
    "Automation Testing": "Software Engineer",
    "Blockchain": "Software Engineer",
    "Business Analyst": "Data Analyst",
    "Data Science": "Data Scientist",
    "Database": "Data Engineer",
    "DevOps Engineer": "DevOps Engineer",
    "DotNet Developer": "Software Engineer",
    "ETL Developer": "Data Engineer",
    "Hadoop": "Data Engineer",
    "Java Developer": "Backend Developer",
    "Python Developer": "Backend Developer",
    "SAP Developer": "Software Engineer",
    "Testing": "Software Engineer",
    "Web Designing": "Frontend Developer",
}


def prepare_dataset(source: Path, output: Path = DEFAULT_OUTPUT) -> dict:
    """Extract skills and map supported source categories to project roles."""
    if not source.is_file():
        raise FileNotFoundError(f"Resume dataset not found: {source}")

    rows = []
    skipped_categories: Counter[str] = Counter()
    skipped_skills = 0
    with source.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "Category" not in reader.fieldnames:
            raise ValueError("Resume CSV must contain a 'Category' column")
        resume_column = next(
            (column for column in ("Resume", "Resume_str") if column in reader.fieldnames), None
        )
        if resume_column is None:
            raise ValueError("Resume CSV must contain a 'Resume' or 'Resume_str' column")

        for row in reader:
            category = (row.get("Category") or "").strip()
            role = CATEGORY_TO_ROLE.get(category)
            if role is None:
                skipped_categories[category or "(missing)"] += 1
                continue
            skills = extract_skills(row.get(resume_column) or "")
            if len(skills) < 2:
                skipped_skills += 1
                continue
            rows.append({"skills": ", ".join(skills), "role": role})

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["skills", "role"])
        writer.writeheader()
        writer.writerows(rows)

    return {
        "written": len(rows),
        "skipped_skills": skipped_skills,
        "skipped_categories": dict(sorted(skipped_categories.items())),
        "role_counts": dict(sorted(Counter(row["role"] for row in rows).items())),
        "output": output,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Path to Kaggle UpdatedResumeDataSet.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"Output CSV path (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()
    report = prepare_dataset(args.source, args.output)
    print(f"{report['written']} labeled rows written to {report['output']}")
    print(f"Skipped for fewer than two extracted skills: {report['skipped_skills']}")
    print(f"Skipped by unmapped category: {sum(report['skipped_categories'].values())}")
    for role, count in report["role_counts"].items():
        print(f"  {role}: {count}")
    if report["skipped_categories"]:
        print("Unmapped categories:")
        for category, count in report["skipped_categories"].items():
            print(f"  {category}: {count}")


if __name__ == "__main__":
    main()
