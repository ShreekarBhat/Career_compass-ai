"""Train experimental supervised models from the labeled evaluation datasets.

Run from the project root:
    python -m app.ml.train_labeled_models

The small skill-extraction fixture is suitable for proving the training path, not
for measuring generalization or deploying the resulting model.
"""
import argparse
import json
from pathlib import Path

import joblib
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MultiLabelBinarizer

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT / "evaluation" / "data"
DEFAULT_OUTPUT_DIR = ROOT / "models"


def _load_json(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Expected a non-empty JSON array in {path}")
    return rows


def _save_artifacts(name: str, model, metrics: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / f"{name}.joblib"
    metrics_path = output_dir / f"{name}_metrics.json"
    joblib.dump(model, model_path)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return {"model": model_path, "metrics": metrics_path}


def _classification_metrics(y_true, y_pred, labels: list) -> dict:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "report": classification_report(
            y_true, y_pred, labels=labels, output_dict=True, zero_division=0
        ),
    }


def train_intent_model(data_dir: Path = DEFAULT_DATA_DIR, output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict:
    """Fit an intent classifier and report a stratified holdout evaluation."""
    rows = _load_json(data_dir / "intent_tests.json")
    if any(not isinstance(r.get("message"), str) or not r["message"].strip()
           or not isinstance(r.get("intent"), str) or not r["intent"].strip() for r in rows):
        raise ValueError("Intent rows must contain non-empty 'message' and 'intent' strings")
    texts = [r["message"] for r in rows]
    labels = [r["intent"] for r in rows]
    classes = sorted(set(labels))
    if len(classes) < 2 or min(labels.count(label) for label in classes) < 2:
        raise ValueError("Intent training requires at least two labeled examples per intent")

    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.25, stratify=labels, random_state=42
    )
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", sublinear_tf=True)),
        ("classifier", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
    ])
    model.fit(x_train, y_train)
    metrics = {
        "task": "intent_classification",
        "dataset": "intent_tests.json",
        "n_examples": len(texts),
        "n_train": len(x_train),
        "n_test": len(x_test),
        "evaluation": "stratified_holdout",
        **_classification_metrics(y_test, model.predict(x_test), classes),
    }
    model.fit(texts, labels)
    return _save_artifacts("intent_classifier", model, metrics, output_dir)


def train_skill_extractor(data_dir: Path = DEFAULT_DATA_DIR, output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict:
    """Fit a multi-label text-to-skill model; the tiny fixture has no holdout."""
    rows = _load_json(data_dir / "skill_extraction.json")
    if any(not isinstance(r.get("text"), str) or not r["text"].strip()
           or not isinstance(r.get("skills"), list) or not r["skills"]
           or any(not isinstance(skill, str) or not skill.strip() for skill in r["skills"])
           for r in rows):
        raise ValueError("Skill rows must contain non-empty 'text' and a list of skill labels")
    texts = [r["text"] for r in rows]
    labels = [list(dict.fromkeys(skill.strip() for skill in r["skills"])) for r in rows]
    binarizer = MultiLabelBinarizer()
    encoded = binarizer.fit_transform(labels)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", sublinear_tf=True)
    features = vectorizer.fit_transform(texts)
    classifier = OneVsRestClassifier(
        LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)
    )
    classifier.fit(features, encoded)
    model = {"vectorizer": vectorizer, "label_binarizer": binarizer, "classifier": classifier}
    metrics = {
        "task": "multi_label_skill_extraction",
        "dataset": "skill_extraction.json",
        "n_examples": len(texts),
        "n_labels": len(binarizer.classes_),
        "evaluation": "not_performed",
        "note": "Six labeled snippets are insufficient for a reliable holdout evaluation.",
    }
    return _save_artifacts("skill_extractor", model, metrics, output_dir)


def _matching_features(profile_skills: list[str], job_skills: list[str]) -> dict:
    profile = {skill.strip().casefold() for skill in profile_skills if skill.strip()}
    job = {skill.strip().casefold() for skill in job_skills if skill.strip()}
    shared = profile & job
    job_only = job - profile
    union = profile | job
    features = {
        f"profile:{skill}": 1 for skill in profile
    }
    features.update({f"job:{skill}": 1 for skill in job})
    features.update({f"shared:{skill}": 1 for skill in shared})
    features.update({f"missing:{skill}": 1 for skill in job_only})
    features["profile_skill_count"] = len(profile)
    features["job_skill_count"] = len(job)
    features["shared_skill_count"] = len(shared)
    features["job_coverage"] = len(shared) / len(job) if job else 0.0
    features["jaccard"] = len(shared) / len(union) if union else 0.0
    return features


def train_job_relevance_model(
    data_dir: Path = DEFAULT_DATA_DIR, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> dict:
    """Fit a job/profile relevance classifier with profile-grouped holdout."""
    profiles = _load_json(data_dir / "matching_pairs.json")
    features, labels, groups = [], [], []
    for profile in profiles:
        if (not isinstance(profile.get("profile"), str) or not profile["profile"].strip()
                or not isinstance(profile.get("profile_skills"), list)
                or any(not isinstance(skill, str) for skill in profile["profile_skills"])
                or not isinstance(profile.get("jobs"), list)):
            raise ValueError("Matching profiles require 'profile' and 'profile_skills' fields")
        for job in profile.get("jobs", []):
            if (not isinstance(job.get("skills"), list)
                    or any(not isinstance(skill, str) for skill in job["skills"])
                    or not isinstance(job.get("relevant"), bool)):
                raise ValueError("Matching jobs require a 'skills' list and boolean 'relevant' label")
            features.append(_matching_features(profile["profile_skills"], job["skills"]))
            labels.append(job["relevant"])
            groups.append(profile["profile"])
    if len(set(labels)) != 2:
        raise ValueError("Matching training requires both relevant and irrelevant examples")

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_indices, test_indices = next(splitter.split(features, labels, groups))
    y_train = [labels[i] for i in train_indices]
    y_test = [labels[i] for i in test_indices]
    if len(set(y_train)) != 2 or len(set(y_test)) != 2:
        raise ValueError("Profile-grouped validation split must contain both relevance labels")

    model = Pipeline([
        ("features", DictVectorizer()),
        ("classifier", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
    ])
    x_train = [features[i] for i in train_indices]
    x_test = [features[i] for i in test_indices]
    model.fit(x_train, y_train)
    metrics = {
        "task": "job_relevance",
        "dataset": "matching_pairs.json",
        "n_examples": len(features),
        "n_profiles": len(set(groups)),
        "n_train": len(train_indices),
        "n_test": len(test_indices),
        "evaluation": "profile_grouped_holdout",
        **_classification_metrics(y_test, model.predict(x_test), [False, True]),
    }
    model.fit(features, labels)
    return _save_artifacts("job_relevance", model, metrics, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train supervised models from labeled evaluation JSON files.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    for task, train in (
        ("intent", train_intent_model),
        ("skill extraction", train_skill_extractor),
        ("job relevance", train_job_relevance_model),
    ):
        artifacts = train(data_dir=args.data_dir, output_dir=args.output_dir)
        print(f"{task}: saved {artifacts['model']} and {artifacts['metrics']}")


if __name__ == "__main__":
    main()
