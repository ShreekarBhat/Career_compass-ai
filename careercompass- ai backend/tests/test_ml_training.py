import json
import csv

import joblib
import pytest

from app.ml import train_labeled_models, train_role_classifier
from scripts.prepare_role_dataset import prepare_dataset


def test_labeled_training_saves_models_and_task_metrics(tmp_path):
    data_dir = train_labeled_models.DEFAULT_DATA_DIR
    output_dir = tmp_path / "models"

    intent = train_labeled_models.train_intent_model(data_dir, output_dir)
    skills = train_labeled_models.train_skill_extractor(data_dir, output_dir)
    matching = train_labeled_models.train_job_relevance_model(data_dir, output_dir)

    for artifacts in (intent, skills, matching):
        assert artifacts["model"].is_file()
        assert artifacts["metrics"].is_file()
        assert json.loads(artifacts["metrics"].read_text(encoding="utf-8"))["n_examples"] > 0

    intent_model = joblib.load(intent["model"])
    assert intent_model.predict(["I want a job as a data scientist"])[0] in intent_model.classes_

    skill_model = joblib.load(skills["model"])
    skill_features = skill_model["vectorizer"].transform(["Python and PyTorch"])
    skill_prediction = skill_model["classifier"].predict(skill_features)
    assert skill_model["label_binarizer"].inverse_transform(skill_prediction)

    matching_model = joblib.load(matching["model"])
    assert matching_model.predict([train_labeled_models._matching_features(["Python"], ["Python"])])[0] in (
        True, False
    )
    matching_metrics = json.loads(matching["metrics"].read_text(encoding="utf-8"))
    assert matching_metrics["evaluation"] == "profile_grouped_holdout"
    assert matching_metrics["n_profiles"] == 24

    skill_metrics = json.loads(skills["metrics"].read_text(encoding="utf-8"))
    assert skill_metrics["evaluation"] == "not_performed"


def test_role_training_requires_labeled_data_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(train_role_classifier, "ROOT", tmp_path)

    with pytest.raises(FileNotFoundError, match="No labeled role dataset found"):
        train_role_classifier.load_dataset()

    _, _, source = train_role_classifier.load_dataset(allow_synthetic=True)
    assert source == "synthetic"


def test_role_training_deduplicates_profiles_and_rejects_conflicting_labels():
    unique_x, unique_y = train_role_classifier.deduplicate_profiles(
        ["Python, SQL", "SQL, Python", "React"],
        ["Backend Developer", "Backend Developer", "Frontend Developer"],
    )
    assert unique_x == ["Python, SQL", "React"]
    assert unique_y == ["Backend Developer", "Frontend Developer"]

    with pytest.raises(ValueError, match="conflicting role labels"):
        train_role_classifier.deduplicate_profiles(
            ["Python, SQL", "SQL, Python"],
            ["Backend Developer", "Data Analyst"],
        )


def test_prepare_role_dataset_maps_categories_and_skips_unsupported_rows(tmp_path):
    source = tmp_path / "resumes.csv"
    output = tmp_path / "role_training.csv"
    with source.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Category", "Resume"])
        writer.writeheader()
        writer.writerow({"Category": "Data Science", "Resume": "Python SQL Pandas machine learning"})
        writer.writerow({"Category": "HR", "Resume": "Human resources recruiting"})
        writer.writerow({"Category": "DevOps Engineer", "Resume": "Kubernetes"})

    report = prepare_dataset(source, output)

    assert report["written"] == 1
    assert report["skipped_skills"] == 1
    assert report["skipped_categories"] == {"HR": 1}
    with output.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows == [{"skills": "Python, SQL, Pandas, Machine Learning", "role": "Data Scientist"}]
