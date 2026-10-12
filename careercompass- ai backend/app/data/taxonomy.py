"""Skill and role taxonomy: the domain knowledge behind skill extraction, gap analysis and roadmaps.

Edit this file to add skills or roles. hours = rough hours to reach job-ready level.
"""
from __future__ import annotations

import difflib
import re
from functools import lru_cache


def _s(cat, hours, aliases=(), prereqs=(), related=()):
    return {"category": cat, "hours": hours, "aliases": list(aliases),
            "prereqs": list(prereqs), "related": list(related)}


SKILLS: dict[str, dict] = {
    # ---- languages ----
    "Python": _s("language", 40, ["python3"]),
    "Java": _s("language", 50),
    "JavaScript": _s("language", 40, ["js", "ecmascript", "es6"]),
    "TypeScript": _s("language", 25, ["ts"], ["JavaScript"], ["JavaScript"]),
    "C++": _s("language", 50, ["cpp"]),
    "C#": _s("language", 45, ["csharp", "c sharp"]),
    "Go": _s("language", 40, ["golang"]),
    "Rust": _s("language", 60),
    "Bash": _s("tool", 12, ["shell scripting", "shell script", "bash scripting"]),
    "SQL": _s("data", 25, ["structured query language"]),
    # ---- data ----
    "Pandas": _s("data", 20, [], ["Python"], ["NumPy"]),
    "NumPy": _s("data", 12, [], ["Python"], ["Pandas"]),
    "Data Visualization": _s("data", 15, ["matplotlib", "seaborn", "plotly", "data visualisation"], ["Python"]),
    "Excel": _s("data", 12, ["microsoft excel", "ms excel", "advanced excel"]),
    "Power BI": _s("data", 25, ["powerbi"], [], ["Tableau"]),
    "Tableau": _s("data", 25, [], [], ["Power BI"]),
    "Statistics": _s("data", 30, ["statistical analysis", "hypothesis testing", "probability and statistics"]),
    "Data Cleaning": _s("data", 10, ["data wrangling", "data preprocessing", "data preparation"], ["Pandas"]),
    "Feature Engineering": _s("ml", 15, ["feature selection"], ["Pandas"]),
    "ETL": _s("data", 20, ["data pipelines", "data pipeline", "elt"], ["SQL", "Python"]),
    "Apache Spark": _s("data", 35, ["pyspark", "spark"], ["Python", "SQL"]),
    "Apache Airflow": _s("data", 20, ["airflow"], ["Python"]),
    "Apache Kafka": _s("data", 25, ["kafka"]),
    "Hadoop": _s("data", 25, ["hdfs", "mapreduce"]),
    "Data Warehousing": _s("data", 25, ["data warehouse", "snowflake", "bigquery", "redshift"], ["SQL"]),
    # ---- machine learning ----
    "Machine Learning": _s("ml", 60, ["ml", "machine-learning"], ["Python", "Statistics"], ["Deep Learning"]),
    "Scikit-learn": _s("ml", 20, ["sklearn", "scikit learn"], ["Machine Learning"], ["XGBoost"]),
    "XGBoost": _s("ml", 10, ["lightgbm", "gradient boosting", "catboost"], ["Machine Learning"], ["Scikit-learn"]),
    "Model Evaluation": _s("ml", 10, ["cross-validation", "cross validation", "hyperparameter tuning", "model validation"], ["Machine Learning"]),
    "Deep Learning": _s("ml", 50, ["dl", "neural networks", "neural network", "cnn", "rnn", "lstm"], ["Machine Learning"]),
    "PyTorch": _s("ml", 30, ["torch"], ["Python", "Deep Learning"], ["TensorFlow"]),
    "TensorFlow": _s("ml", 30, ["keras", "tensorflow2"], ["Python", "Deep Learning"], ["PyTorch"]),
    "Computer Vision": _s("ml", 35, ["opencv", "image classification", "object detection", "image processing"], ["Deep Learning"]),
    "NLP": _s("ml", 35, ["natural language processing", "text mining", "text classification"], ["Machine Learning"]),
    "Transformers": _s("ml", 20, ["bert", "attention mechanism", "transformer models"], ["Deep Learning"]),
    "Hugging Face": _s("ml", 15, ["huggingface", "hugging face transformers"], ["Python"], ["Transformers"]),
    "Large Language Models": _s("genai", 25, ["llm", "llms", "gpt", "large language model", "openai api"], ["Python"]),
    "Generative AI": _s("genai", 20, ["genai", "gen ai", "generative ai", "gen-ai"], [], ["Large Language Models"]),
    "Prompt Engineering": _s("genai", 10, ["prompt design", "prompting"], [], ["Large Language Models"]),
    "RAG": _s("genai", 20, ["retrieval augmented generation", "retrieval-augmented generation"], ["Large Language Models", "Vector Databases"]),
    "LangChain": _s("genai", 15, [], ["Python", "Large Language Models"], ["LangGraph"]),
    "LangGraph": _s("genai", 12, [], ["LangChain"], ["LangChain"]),
    "Agentic AI": _s("genai", 15, ["ai agents", "agentic", "multi-agent", "multi agent", "llm agents"], ["Large Language Models"]),
    "Vector Databases": _s("genai", 12, ["pgvector", "pinecone", "faiss", "chromadb", "chroma", "weaviate", "vector database", "vector db", "qdrant"]),
    "Fine-tuning": _s("genai", 20, ["fine tuning", "finetuning", "lora", "peft", "qlora"], ["Deep Learning"]),
    "MLOps": _s("ml", 35, ["ml ops", "model deployment", "model serving", "mlflow", "kubeflow", "model monitoring"], ["Docker", "Machine Learning"]),
    "Reinforcement Learning": _s("ml", 35, ["rl", "q-learning"], ["Machine Learning"]),
    "Time Series": _s("ml", 20, ["time series forecasting", "arima", "forecasting"], ["Statistics"]),
    "Recommender Systems": _s("ml", 25, ["recommendation systems", "recommendation engine", "recommender system", "collaborative filtering"], ["Machine Learning"]),
    # ---- backend ----
    "REST APIs": _s("backend", 15, ["rest", "restful", "rest api", "restful apis", "api development", "api design"]),
    "FastAPI": _s("backend", 15, [], ["Python", "REST APIs"], ["Flask", "Django"]),
    "Flask": _s("backend", 15, [], ["Python"], ["FastAPI", "Django"]),
    "Django": _s("backend", 30, ["django rest framework", "drf"], ["Python"], ["Flask", "FastAPI"]),
    "Node.js": _s("backend", 30, ["nodejs", "node js"], ["JavaScript"], ["Express.js"]),
    "Express.js": _s("backend", 15, ["express", "expressjs"], ["Node.js"], ["Node.js"]),
    "Spring Boot": _s("backend", 40, ["spring", "spring framework"], ["Java"]),
    "GraphQL": _s("backend", 15, [], ["REST APIs"]),
    "Microservices": _s("backend", 25, ["microservice", "micro-services"], ["REST APIs", "Docker"]),
    "System Design": _s("backend", 40, ["distributed systems", "scalability", "high level design", "low level design"]),
    "Authentication": _s("backend", 10, ["jwt", "oauth", "oauth2", "authorization", "authn"], ["REST APIs"]),
    "WebSockets": _s("backend", 8, ["websocket", "socket.io"]),
    "Redis": _s("backend", 10, ["caching"], [], ["Message Queues"]),
    "Message Queues": _s("backend", 15, ["rabbitmq", "sqs", "celery", "message broker"], [], ["Apache Kafka"]),
    # ---- databases ----
    "PostgreSQL": _s("database", 20, ["postgres", "psql"], ["SQL"], ["MySQL"]),
    "MySQL": _s("database", 15, ["mariadb"], ["SQL"], ["PostgreSQL"]),
    "MongoDB": _s("database", 15, ["mongo", "nosql"], [], ["PostgreSQL"]),
    "Elasticsearch": _s("database", 20, ["elastic search", "opensearch"]),
    "Database Design": _s("database", 15, ["normalization", "schema design", "data modeling", "data modelling"], ["SQL"]),
    "SQLAlchemy": _s("database", 10, ["orm"], ["Python", "SQL"]),
    # ---- frontend ----
    "HTML/CSS": _s("frontend", 20, ["html", "css", "html5", "css3", "html & css"]),
    "React": _s("frontend", 35, ["reactjs", "react.js", "react js"], ["JavaScript", "HTML/CSS"], ["Vue.js", "Angular"]),
    "Next.js": _s("frontend", 20, ["nextjs", "next js"], ["React"]),
    "Tailwind CSS": _s("frontend", 8, ["tailwind", "tailwindcss"], ["HTML/CSS"]),
    "Vue.js": _s("frontend", 30, ["vue", "vuejs"], ["JavaScript"], ["React"]),
    "Angular": _s("frontend", 35, ["angularjs"], ["TypeScript"], ["React"]),
    "Redux": _s("frontend", 10, ["state management"], ["React"]),
    # ---- devops / cloud ----
    "Docker": _s("devops", 15, ["containers", "containerization", "containerisation", "dockerfile", "docker compose"]),
    "Kubernetes": _s("devops", 35, ["k8s"], ["Docker"]),
    "CI/CD": _s("devops", 15, ["github actions", "jenkins", "gitlab ci", "continuous integration", "continuous deployment", "ci cd"], ["Git"]),
    "Git": _s("tool", 8, ["github", "gitlab", "version control", "git/github"]),
    "Linux": _s("devops", 15, ["unix"]),
    "AWS": _s("cloud", 35, ["amazon web services", "ec2", "amazon s3"], [], ["Azure", "GCP"]),
    "Azure": _s("cloud", 30, ["microsoft azure"], [], ["AWS", "GCP"]),
    "GCP": _s("cloud", 30, ["google cloud", "google cloud platform"], [], ["AWS", "Azure"]),
    "Terraform": _s("devops", 20, ["infrastructure as code", "iac"], ["Linux"]),
    "Ansible": _s("devops", 15, [], ["Linux"]),
    "Monitoring": _s("devops", 15, ["prometheus", "grafana", "observability", "logging and monitoring"]),
    "Nginx": _s("devops", 8, [], ["Linux"]),
    # ---- CS fundamentals ----
    "Data Structures & Algorithms": _s("cs", 60, ["dsa", "data structures", "algorithms", "data structures and algorithms", "data structures & algorithms"]),
    "OOP": _s("cs", 12, ["object oriented programming", "object-oriented programming", "oops", "object oriented"]),
    "Operating Systems": _s("cs", 20, ["os concepts"]),
    "Computer Networks": _s("cs", 15, ["networking", "tcp/ip"]),
    "Testing": _s("cs", 12, ["unit testing", "pytest", "jest", "test-driven development", "tdd", "unit tests", "integration testing"]),
    "Agile": _s("cs", 5, ["scrum", "kanban"]),
}

_CATEGORY_DEFAULT_HOURS = {"language": 35, "data": 20, "ml": 30, "genai": 18, "backend": 18,
                           "database": 15, "frontend": 20, "devops": 18, "cloud": 30, "cs": 20, "tool": 8}


def skill_hours(skill: str) -> int:
    info = SKILLS.get(skill)
    if not info:
        return 15
    return info.get("hours") or _CATEGORY_DEFAULT_HOURS.get(info["category"], 15)


def _r(aliases, description, skills):
    return {"aliases": aliases, "description": description, "skills": skills}


# skill -> importance weight (3 = core, 2 = important, 1 = nice to have)
ROLES: dict[str, dict] = {
    "Machine Learning Engineer": _r(
        ["ml engineer", "machine learning engineer", "mle", "ml developer", "machine learning developer",
         "machine learning engineering", "ml engineering"],
        "Builds, trains, deploys and monitors machine learning models in production systems.",
        {"Python": 3, "SQL": 2, "Machine Learning": 3, "Scikit-learn": 3, "Pandas": 2, "NumPy": 2,
         "Deep Learning": 3, "PyTorch": 3, "TensorFlow": 1, "Docker": 2, "MLOps": 3, "FastAPI": 2,
         "REST APIs": 2, "Git": 2, "Model Evaluation": 2, "Feature Engineering": 2, "Statistics": 2,
         "AWS": 1, "Data Structures & Algorithms": 1}),
    "Data Scientist": _r(
        ["data scientist", "data science", "ds role"],
        "Extracts insight and builds predictive models from data using statistics and machine learning.",
        {"Python": 3, "SQL": 3, "Statistics": 3, "Machine Learning": 3, "Pandas": 3, "NumPy": 2,
         "Scikit-learn": 3, "Data Visualization": 2, "Feature Engineering": 2, "Model Evaluation": 2,
         "Data Cleaning": 2, "Excel": 1, "Tableau": 1, "Git": 1, "Deep Learning": 1}),
    "Data Analyst": _r(
        ["data analyst", "business analyst", "analytics role"],
        "Turns raw data into reports, dashboards and decisions.",
        {"SQL": 3, "Excel": 3, "Python": 2, "Pandas": 2, "Data Visualization": 3, "Power BI": 2,
         "Tableau": 2, "Statistics": 2, "Data Cleaning": 2}),
    "AI Engineer": _r(
        ["ai engineer", "genai engineer", "gen ai engineer", "generative ai engineer", "llm engineer",
         "ai developer", "ai application developer"],
        "Builds applications on top of LLMs: RAG systems, agents and AI-powered products.",
        {"Python": 3, "Large Language Models": 3, "Generative AI": 3, "Prompt Engineering": 2, "RAG": 3,
         "LangChain": 2, "LangGraph": 2, "Vector Databases": 2, "FastAPI": 2, "REST APIs": 2, "Docker": 2,
         "Git": 2, "Agentic AI": 2, "Fine-tuning": 1, "Hugging Face": 2}),
    "NLP Engineer": _r(
        ["nlp engineer", "natural language processing engineer", "nlp scientist"],
        "Builds language-understanding systems with transformers and classic NLP.",
        {"Python": 3, "NLP": 3, "Transformers": 3, "Hugging Face": 3, "PyTorch": 3, "Deep Learning": 3,
         "Large Language Models": 2, "Machine Learning": 2, "Docker": 1, "FastAPI": 1, "Git": 1}),
    "Backend Developer": _r(
        ["backend developer", "backend engineer", "back-end developer", "back end developer",
         "backend", "server side developer", "api developer"],
        "Designs and builds APIs, services and databases that power applications.",
        {"Python": 2, "SQL": 3, "REST APIs": 3, "FastAPI": 2, "PostgreSQL": 2, "Docker": 2, "Git": 2,
         "Authentication": 2, "System Design": 2, "Testing": 2, "Data Structures & Algorithms": 2,
         "Redis": 1, "Microservices": 1}),
    "Full Stack Developer": _r(
        ["full stack developer", "fullstack developer", "full-stack developer", "full stack engineer",
         "fullstack engineer", "mern developer"],
        "Builds both the user interface and the server side of web applications.",
        {"JavaScript": 3, "React": 3, "Node.js": 2, "HTML/CSS": 3, "SQL": 2, "REST APIs": 3, "Git": 3,
         "TypeScript": 2, "Next.js": 1, "MongoDB": 1, "PostgreSQL": 1, "Docker": 1, "Testing": 1}),
    "Frontend Developer": _r(
        ["frontend developer", "front-end developer", "front end developer", "frontend engineer",
         "ui developer", "react developer"],
        "Builds responsive, accessible user interfaces for the web.",
        {"HTML/CSS": 3, "JavaScript": 3, "React": 3, "TypeScript": 2, "Tailwind CSS": 1, "Git": 2,
         "Next.js": 1, "Testing": 1, "REST APIs": 1}),
    "DevOps Engineer": _r(
        ["devops engineer", "devops", "site reliability engineer", "sre", "platform engineer", "cloud engineer"],
        "Automates build, deployment and infrastructure so software ships reliably.",
        {"Linux": 3, "Docker": 3, "Kubernetes": 3, "CI/CD": 3, "Git": 2, "AWS": 2, "Terraform": 2,
         "Bash": 2, "Monitoring": 2, "Ansible": 1, "Python": 1}),
    "Data Engineer": _r(
        ["data engineer", "big data engineer", "etl developer", "analytics engineer"],
        "Builds the pipelines and warehouses that deliver reliable data to analysts and models.",
        {"Python": 3, "SQL": 3, "ETL": 3, "Apache Spark": 3, "Apache Airflow": 2, "Data Warehousing": 2,
         "Apache Kafka": 2, "Docker": 1, "AWS": 2, "Git": 1, "PostgreSQL": 1}),
    "Software Engineer": _r(
        ["software engineer", "sde", "software developer", "software development engineer", "swe",
         "software development"],
        "Designs, writes and tests software systems.",
        {"Data Structures & Algorithms": 3, "OOP": 3, "Git": 2, "SQL": 2, "REST APIs": 2, "System Design": 2,
         "Testing": 2, "Operating Systems": 1, "Python": 1}),
}

# ------------------------------------------------------------------ lookups


@lru_cache(maxsize=1)
def alias_map() -> dict[str, str]:
    m: dict[str, str] = {}
    for name, info in SKILLS.items():
        m[name.lower()] = name
        for a in info["aliases"]:
            m[a.lower()] = name
    return m


@lru_cache(maxsize=1)
def role_alias_map() -> dict[str, str]:
    m: dict[str, str] = {}
    for name, info in ROLES.items():
        m[name.lower()] = name
        for a in info["aliases"]:
            m[a.lower()] = name
    return m


def canonical_skill(name: str) -> str | None:
    return alias_map().get(name.strip().lower())


def role_skill_weights(role: str) -> dict[str, int]:
    return dict(ROLES[role]["skills"]) if role in ROLES else {}


def find_role_in_text(text: str) -> str | None:
    """Find a known role mentioned inside free text (longest alias wins)."""
    t = text.lower()
    for alias in sorted(role_alias_map(), key=len, reverse=True):
        if len(alias) < 4:  # avoid matching tiny aliases inside words
            if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", t):
                return role_alias_map()[alias]
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", t):
            return role_alias_map()[alias]
    return None


def resolve_role(text: str | None) -> str | None:
    """Map free text such as 'ML engineer' to a canonical role name (fuzzy)."""
    if not text:
        return None
    t = text.strip().lower()
    if t in role_alias_map():
        return role_alias_map()[t]
    hit = find_role_in_text(t)
    if hit:
        return hit
    close = difflib.get_close_matches(t, list(role_alias_map()), n=1, cutoff=0.78)
    return role_alias_map()[close[0]] if close else None


_FAMILY_RULES = [
    ("ML/AI", ["machine learning", "ml ", " ml", "deep learning", "ai ", " ai", "nlp", "llm", "genai",
               "computer vision", "data scien"]),
    ("Data", ["data analyst", "data engineer", "analytics", "business intelligence", "bi developer", "etl"]),
    ("Full Stack/Frontend", ["full stack", "fullstack", "frontend", "front-end", "front end", "react", "ui "]),
    ("Backend", ["backend", "back-end", "back end", "api", "python developer", "java developer"]),
    ("DevOps/Cloud", ["devops", "sre", "cloud", "platform engineer", "infrastructure"]),
    ("Software Engineering", ["software", "sde", "developer", "engineer"]),
]


def role_family(title: str) -> str:
    t = f" {title.lower()} "
    for family, kws in _FAMILY_RULES:
        if any(k in t for k in kws):
            return family
    return "Other"
