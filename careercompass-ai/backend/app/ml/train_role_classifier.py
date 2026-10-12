"""Train the role classifier and write evaluation metrics.

    python -m app.ml.train_role_classifier

Put a labeled CSV at data/role_training.csv with columns `skills` (comma separated) and `role`.
Synthetic training is available only when explicitly requested with `--synthetic`.
"""
import argparse
import csv
import json
import random
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.data.taxonomy import ROLES, SKILLS
from app.ml.role_classifier import MODEL_PATH, reload_model, skill_tokenizer

ROOT = Path(__file__).resolve().parents[2]


def synthetic_dataset(per_role: int = 300, seed: int = 7) -> tuple[list[str], list[str]]:
    rng = random.Random(seed)
    all_skills = list(SKILLS)
    X, y = [], []
    for role, info in ROLES.items():
        for _ in range(per_role):
            picked = [s for s, w in info["skills"].items() if rng.random() < 0.25 + 0.2 * w]
            picked += rng.sample(all_skills, rng.randint(0, 4))  # noise skills
            if len(picked) < 2:
                picked += rng.sample(list(info["skills"]), 2)
            rng.shuffle(picked)
            X.append(", ".join(dict.fromkeys(picked)))
            y.append(role)
    return X, y


def load_dataset(allow_synthetic: bool = False):
    csv_path = ROOT / "data" / "role_training.csv"
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows or any(not r.get("skills", "").strip() or not r.get("role", "").strip() for r in rows):
            raise ValueError(f"{csv_path} must contain non-empty 'skills' and 'role' values on every row")
        X, y = [r["skills"] for r in rows], [r["role"] for r in rows]
        counts = {label: y.count(label) for label in set(y)}
        if len(counts) < 2 or min(counts.values()) < 2:
            raise ValueError("Role training CSV must contain at least two examples for each of two or more roles")
        return X, y, "labeled_csv"
    if allow_synthetic:
        X, y = synthetic_dataset()
        return X, y, "synthetic"
    raise FileNotFoundError(
        f"No labeled role dataset found at {csv_path}. Add a CSV with 'skills' and 'role' columns "
        "or explicitly opt into synthetic data with --synthetic."
    )


def deduplicate_profiles(X: list[str], y: list[str]) -> tuple[list[str], list[str]]:
    """Remove repeated skill profiles so duplicates cannot leak across evaluation splits."""
    profiles: dict[tuple[str, ...], tuple[str, str]] = {}
    for skills, role in zip(X, y):
        key = tuple(sorted(set(skill_tokenizer(skills))))
        if not key:
            raise ValueError("Role training examples must contain at least one skill")
        previous = profiles.get(key)
        if previous and previous[1] != role:
            raise ValueError(
                f"Identical skill profile has conflicting role labels: {previous[1]!r} and {role!r}"
            )
        profiles.setdefault(key, (skills, role))
    unique = list(profiles.values())
    return [skills for skills, _ in unique], [role for _, role in unique]


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the role classifier from labeled resume skills.")
    parser.add_argument("--synthetic", action="store_true", help="Use generated taxonomy examples when no CSV exists.")
    args = parser.parse_args()
    X, y, source = load_dataset(allow_synthetic=args.synthetic)
    n_examples = len(X)
    X, y = deduplicate_profiles(X, y)
    class_counts = {label: y.count(label) for label in set(y)}
    if len(class_counts) < 2 or min(class_counts.values()) < 2:
        raise ValueError("Training needs at least two distinct skill profiles for every role")
    test_fraction = max(0.2, len(set(y)) / len(y))
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_fraction, stratify=y, random_state=42
    )
    model = Pipeline([
        ("vec", CountVectorizer(tokenizer=skill_tokenizer, lowercase=False, token_pattern=None, binary=True)),
        ("clf", LogisticRegression(max_iter=2000, C=2.0)),
    ])
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    top3 = float(np.mean([t in [model.classes_[i] for i in np.argsort(p)[::-1][:3]]
                          for t, p in zip(y_te, model.predict_proba(X_te))]))
    metrics = {"data_source": source, "dataset": "data/role_training.csv" if source == "labeled_csv" else None,
               "n_examples": n_examples, "n_unique_profiles": len(X),
               "evaluation": "stratified_holdout_unique_profiles",
               "n_train": len(X_tr), "n_test": len(X_te),
               "accuracy": round(accuracy_score(y_te, pred), 4),
               "macro_f1": round(f1_score(y_te, pred, average="macro"), 4),
               "top3_accuracy": round(top3, 4),
               "report": classification_report(y_te, pred, output_dict=True, zero_division=0)}
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    (MODEL_PATH.parent / "role_classifier_metrics.json").write_text(json.dumps(metrics, indent=2))
    reload_model()
    print(f"Saved {MODEL_PATH}")
    print(f"data={source} accuracy={metrics['accuracy']} macro_F1={metrics['macro_f1']} top3={metrics['top3_accuracy']}")
    if source == "synthetic":
        print("NOTE: metrics are on synthetic data. Add data/role_training.csv with real labelled resumes for the report.")


if __name__ == "__main__":
    main()
