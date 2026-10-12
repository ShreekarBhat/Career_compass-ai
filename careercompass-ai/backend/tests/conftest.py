import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db",
    "SCHEDULER_ENABLED": "false",
    "USE_SENTENCE_TRANSFORMERS": "false",
    "JOB_PROVIDERS": "seed",
    "RATE_LIMIT_PER_MINUTE": "0",
    "GROQ_API_KEY": "",
    "TELEGRAM_BOT_TOKEN": "",
    "AUTO_SEED": "true",
    "ENV": "test",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

RESUME = """Shreekar Kumar
shreekar@example.com | +91 98765 43210 | github.com/shreekar | linkedin.com/in/shreekar

Summary
BTech AIML student at UVCE passionate about machine learning and backend development.

Education
B.Tech in Artificial Intelligence and Machine Learning, UVCE Bengaluru, 2022 - 2026

Skills
Python, SQL, Pandas, NumPy, Scikit-learn, Machine Learning, Flask, Git, GitHub, PostgreSQL

Projects
Food Ordering System
- Built a Flask web application with SQL backend serving 200 users
- Worked on payment integration

Churn Prediction
- Trained a random forest model using scikit-learn reaching 87% accuracy on 10k records
- Designed feature engineering pipeline with Pandas, reducing preprocessing time by 40%
"""


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    import uuid
    email = f"user{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "supersecret1", "full_name": "Test User"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def resume_bytes():
    return RESUME.encode()
